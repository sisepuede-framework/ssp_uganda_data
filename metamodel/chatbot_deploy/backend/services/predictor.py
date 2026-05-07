"""
Surrogate Model Predictor Service
===================================
Loads the trained XGBoost pipeline and provides a clean interface for
running simulations. All knowledge about the model's expected input format
is encapsulated here — the rest of the application does not need to know
about column ordering, feature names, or units.

Key design decisions:
  - Column order is read from the training parquet at startup (not hardcoded).
    If the model is retrained with a different column order, only this file
    changes — no other service needs updating.
  - Defaults (L=0.1 for BAU, X=-1.0 for BAU) are applied for any group not
    explicitly overridden by the caller.
  - Percentile-in-training is computed from the stored training targets so that
    the UI can show "this prediction is in the top 20% of all simulations."

To update the model:
  1. Retrain the XGBoost pipeline.
  2. Update MODEL_PATH and TRAINING_DATA_PATH in config.py.
  3. Restart the server — this module will pick up the new files automatically.
"""

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Output metric metadata (units, display names) ────────────────────────────
# Kept here (not only in the registry) because the predictor needs units to
# build PredictionResult objects without importing the full registry.

TARGET_METADATA: dict[str, dict] = {
    "emission_total_sum": {
        "display_name": "Total Cumulative Emissions (2025–2070)",
        "unit": "Mt CO₂e",
    },
    "2033_2037_mean_emission": {
        "display_name": "Near-Term Annual Emissions (2033–2037 avg)",
        "unit": "Mt CO₂e/yr",
    },
    "2066_2070_mean_emission": {
        "display_name": "Long-Term Annual Emissions (2066–2070 avg)",
        "unit": "Mt CO₂e/yr",
    },
    "2025_2035_mean_benefits": {
        "display_name": "Near-Term Annual Co-Benefits (2025–2035 avg)",
        "unit": "Billion USD/yr",
    },
    "2025_2070_mean_benefits": {
        "display_name": "Long-Term Annual Co-Benefits (2025–2070 avg)",
        "unit": "Billion USD/yr",
    },
    "2025_2035_mean_costs": {
        "display_name": "Near-Term Annual Implementation Costs (2025–2035 avg)",
        "unit": "Billion USD/yr",
    },
    "2025_2070_mean_costs": {
        "display_name": "Long-Term Annual Implementation Costs (2025–2070 avg)",
        "unit": "Billion USD/yr",
    },
    "2025_2035_max_costs_rel_to_gdp": {
        "display_name": "Peak Near-Term Cost as % of GDP (2025–2035)",
        # Raw model output is a decimal fraction (e.g. 0.003 = 0.3% of GDP).
        # Multiply by 100 when presenting to users as a percentage.
        "unit": "fraction of GDP (multiply by 100 for %)",
    },
    "2025_2070_max_costs_rel_to_gdp": {
        "display_name": "Peak Long-Term Cost as % of GDP (2025–2070)",
        "unit": "fraction of GDP (multiply by 100 for %)",
    },
    "2025_2035_cumulative_cost_rel_to_gdp": {
        "display_name": "Cumulative Near-Term Cost as % of GDP (2025–2035)",
        "unit": "fraction of GDP (multiply by 100 for %)",
    },
    "2025_2070_cumulative_cost_rel_to_gdp": {
        "display_name": "Cumulative Long-Term Cost as % of GDP (2025–2070)",
        "unit": "fraction of GDP (multiply by 100 for %)",
    },
}

# Defaults applied when a group is not overridden by the caller.
# L features: 0.1 = minimal policy (BAU baseline)
# X features: -1.0 = fixed baseline trajectory (no uncertainty variation)
BAU_L_DEFAULT: float = 0.1
BAU_X_DEFAULT: float = -1.0

MODERATE_L_DEFAULT: float = 0.5
MODERATE_X_DEFAULT: float = 0.5

# Groups not in the NZ strategy stay at BAU (0.1).
NETZERO_L_DEFAULT: float = 0.1
NETZERO_X_DEFAULT: float = 0.5

# Per-group L values derived from the NZ strategy YAML files.
# Formula: T = NZ_magnitude / transformer_default; L = (T - 0.1) / 0.9, clamped [0,1].
# Groups absent from the NZ strategy (22, 29, 5) remain at BAU = 0.1.
NETZERO_L_OVERRIDES: dict[int, float] = {
    1:  1.0,     # Rice Paddy Methane Reduction
    2:  1.0,     # Agricultural Food Loss Reduction
    3:  1.0,     # Conservation Agriculture
    4:  1.0,     # Crop Yield Improvement
    5:  0.1,     # CCS — NZ uses only 1% of default capacity
    6:  1.0,     # Electricity Grid Efficiency
    7:  1.0,     # Clean Hydrogen
    8:  1.0,     # Renewable Electricity Target
    9:  1.0,     # Fugitive Gas Leak Reduction
    10: 1.0,     # Methane Flaring
    11: 1.0,     # Forest Carbon Sequestration
    12: 1.0,     # Industrial Fuel Efficiency
    13: 1.0,     # Industrial Production Efficiency
    14: 1.0,     # Industrial Fuel Mix Shift
    15: 1.0,     # Low-Clinker Cement
    16: 1.0,     # Industrial Production Demand Reduction
    17: 1.0,     # Industrial N₂O Process Emissions
    18: 1.0,     # Industrial PFC Emissions
    19: 1.0,     # Deforestation Reduction
    20: 1.0,     # Wetland Protection
    21: 1.0,     # Reforestation
    22: 0.1,     # Silvopasture — not in NZ strategy
    23: 1.0,     # Livestock Manure Biogas Capture
    24: 0.9942,  # Cattle & Pig Manure Management
    25: 0.9942,  # Other Livestock Manure Management
    26: 0.9942,  # Poultry Manure Management
    27: 1.0,     # Livestock Enteric Fermentation
    28: 1.0,     # Livestock Productivity
    29: 0.1,     # Diet Shift — not in NZ strategy
    30: 1.0,     # Industrial CO₂ Capture
    31: 0.7778,  # Building Heat Demand Reduction
    32: 0.5556,  # Building Appliance Efficiency
    33: 1.0,     # Biomass Cooking Stove Efficiency
    34: 0.9415,  # Building Fuel Mix Shift
    35: 1.0,     # Agricultural Liming Reduction
    36: 1.0,     # Nitrogen Fertilizer Reduction
    37: 1.0,     # Transport Demand Reduction
    38: 1.0,     # Electric Vehicle Efficiency
    39: 1.0,     # Non-Electric Vehicle Efficiency
    40: 1.0,     # Passenger Vehicle Occupancy
    41: 1.0,     # Light Duty Vehicle Electrification
    42: 0.6825,  # Maritime Fuel Shift
    43: 1.0,     # Medium Duty Vehicle Electrification
    44: 1.0,     # Rail Electrification
    45: 1.0,     # Freight Mode Shift
    46: 1.0,     # Passenger Mode Shift
    47: 1.0,     # Regional Transport Mode Shift
    48: 1.0,     # Wastewater Biogas Capture
    49: 1.0,     # Septic System Compliance
    50: 1.0,     # Industrial Wastewater Treatment
    51: 1.0,     # Rural Wastewater Treatment
    52: 1.0,     # Urban Wastewater Treatment
    53: 1.0,     # Consumer Food Waste Reduction
    54: 1.0,     # Organic Waste Composting
    55: 1.0,     # Landfill Gas Capture
    56: 1.0,     # Landfill Gas Energy Recovery
    57: 1.0,     # Waste Incineration Energy Recovery
    58: 1.0,     # Controlled Landfilling
    59: 1.0,     # Solid Waste Recycling
}

PRESET_DEFAULTS = {
    "bau":      (BAU_L_DEFAULT, BAU_X_DEFAULT),
    "moderate": (MODERATE_L_DEFAULT, MODERATE_X_DEFAULT),
    "netzero":  (NETZERO_L_DEFAULT, NETZERO_X_DEFAULT),
}


class SurrogatePredictor:
    """
    Thin wrapper around the trained XGBoost multi-output pipeline.

    Usage
    -----
    predictor = SurrogatePredictor()   # loads model + training data
    result = predictor.predict(
        lever_overrides={8: 0.9, 41: 0.8},    # group_id → value
        exogenous_overrides={62: 0.7},
        preset_scenario="bau",
        scenario_name="High Renewables",
    )
    """

    def __init__(self) -> None:
        self._model = self._load_model()
        self._feature_columns, self._group_to_column, self._training_targets = (
            self._load_training_metadata()
        )
        self._registry = self._load_registry()
        logger.info(
            "SurrogatePredictor ready. Features: %d, Targets: %d",
            len(self._feature_columns),
            len(TARGET_METADATA),
        )

    # ── Public interface ────────────────────────────────────────────────────

    def predict(
        self,
        lever_overrides: dict[int, float] | None = None,
        exogenous_overrides: dict[int, float] | None = None,
        preset_scenario: str = "bau",
        scenario_name: str = "Scenario",
    ) -> dict:
        """
        Run the surrogate model for one scenario.

        Parameters
        ----------
        lever_overrides : group_id (1–59) → value in [0.0, 1.0]
        exogenous_overrides : group_id (60–68) → value in [-1.0, 1.0]
        preset_scenario : "bau" | "moderate" | "netzero" — fill for unspecified groups
        scenario_name : human-readable name for this run

        Returns
        -------
        dict matching the SimulationResult schema
        """
        lever_overrides = lever_overrides or {}
        exogenous_overrides = exogenous_overrides or {}

        l_default, x_default = PRESET_DEFAULTS.get(preset_scenario, (BAU_L_DEFAULT, BAU_X_DEFAULT))

        # For netzero, seed lever values from per-group NZ overrides, then let
        # caller's explicit lever_overrides take priority on top.
        if preset_scenario == "netzero":
            lever_overrides = {**NETZERO_L_OVERRIDES, **lever_overrides}

        # Build group_id → value mapping for ALL 68 groups
        group_values = self._build_group_values(lever_overrides, exogenous_overrides, l_default, x_default)

        # Build feature vector in exact training column order
        feature_vector = self._build_feature_vector(group_values)

        # Run prediction
        X = np.array(list(feature_vector.values())).reshape(1, -1)
        raw_predictions = self._model.predict(X)[0]  # shape: (n_targets,)

        # Assemble structured predictions
        predictions = {}
        for i, target_name in enumerate(TARGET_METADATA):
            value = float(raw_predictions[i])
            training_col = self._training_targets.get(target_name, {})
            predictions[target_name] = {
                "value": round(value, 4),
                "unit": TARGET_METADATA[target_name]["unit"],
                "display_name": TARGET_METADATA[target_name]["display_name"],
                "training_range": training_col.get("range", {"min": 0, "max": 0}),
                "percentile_in_training": round(
                    float(stats.percentileofscore(training_col.get("values", [value]), value)),
                    1,
                ),
            }

        return {
            "scenario_name": scenario_name,
            "feature_vector": feature_vector,
            "group_values": group_values,
            "predictions": predictions,
        }

    def predict_comparison(
        self,
        lever_overrides: dict[int, float] | None = None,
        exogenous_overrides: dict[int, float] | None = None,
        preset_scenario: str = "bau",
        scenario_name: str = "Scenario",
    ) -> dict:
        """
        Run the scenario AND a BAU baseline. Returns both plus % change deltas.
        """
        scenario = self.predict(lever_overrides, exogenous_overrides, preset_scenario, scenario_name)
        baseline = self.predict({}, {}, "bau", "Business as Usual (Baseline)")

        comparison = {}
        for metric in TARGET_METADATA:
            scenario_val = scenario["predictions"][metric]["value"]
            baseline_val = baseline["predictions"][metric]["value"]
            if baseline_val != 0:
                pct_change = round(100 * (scenario_val - baseline_val) / abs(baseline_val), 2)
            else:
                pct_change = 0.0
            comparison[metric] = pct_change

        return {"scenario": scenario, "baseline": baseline, "comparison": comparison}

    def get_feature_info(self) -> dict:
        """Return the full feature registry (for /api/features endpoint)."""
        return self._registry

    def get_group_to_column(self) -> dict[int, str]:
        """Map group_id → training column name."""
        return self._group_to_column

    # ── Private helpers ─────────────────────────────────────────────────────

    def _load_model(self):
        path = settings.model_path
        if not path.exists():
            raise FileNotFoundError(
                f"Trained model not found at {path}. "
                "Update MODEL_PATH in config.py or .env."
            )
        model = joblib.load(path)
        logger.info("Loaded model from %s", path)
        return model

    def _load_training_metadata(self) -> tuple[list[str], dict[int, str], dict]:
        """
        Extract:
          - ordered list of feature column names (defines model input order)
          - mapping from group_id (int) to column name
          - target distribution statistics (for percentile computation)
        """
        path = settings.training_data_path
        if not path.exists():
            raise FileNotFoundError(
                f"Training data not found at {path}. "
                "Update TRAINING_DATA_PATH in config.py or .env."
            )

        df = pd.read_parquet(path)
        target_cols = list(TARGET_METADATA.keys())
        id_cols = ["future_id", "primary_id", "strategy_id", "design_id"]
        feature_cols = [c for c in df.columns if c not in target_cols and c not in id_cols]

        # Build group_id → column name map from registry
        registry_path = settings.feature_registry_path
        with open(registry_path) as f:
            registry = json.load(f)

        group_to_column: dict[int, str] = {}
        for gid, meta in {**registry["lever_features"], **registry["exogenous_features"]}.items():
            group_to_column[int(gid)] = meta["training_column"]

        # Store training target distributions for percentile calculations
        training_targets: dict[str, dict] = {}
        for col in target_cols:
            if col in df.columns:
                vals = df[col].dropna().tolist()
                training_targets[col] = {
                    "values": vals,
                    "range": {"min": round(min(vals), 4), "max": round(max(vals), 4)},
                }

        logger.info("Feature columns loaded: %d", len(feature_cols))
        return feature_cols, group_to_column, training_targets

    def _load_registry(self) -> dict:
        with open(settings.feature_registry_path) as f:
            return json.load(f)

    def _build_group_values(
        self,
        lever_overrides: dict[int, float],
        exogenous_overrides: dict[int, float],
        l_default: float,
        x_default: float,
    ) -> dict[int, float]:
        """
        Build a complete {group_id: value} dict for all 68 groups.
        Overrides take priority; everything else gets the default.
        Values are clamped to their valid ranges.
        """
        group_values: dict[int, float] = {}

        # L features: groups 1–59
        for gid in range(1, 60):
            raw = lever_overrides.get(gid, l_default)
            group_values[gid] = float(np.clip(raw, 0.0, 1.0))

        # X features: groups 60–68
        for gid in range(60, 69):
            raw = exogenous_overrides.get(gid, x_default)
            group_values[gid] = float(np.clip(raw, -1.0, 1.0))

        return group_values

    def _build_feature_vector(self, group_values: dict[int, float]) -> dict[str, float]:
        """
        Convert {group_id: value} to {column_name: value} in the exact
        column order the model was trained on.

        Any column not mapped by the registry falls back to its training median.
        This should not happen in normal operation but prevents silent failures
        if the registry ever gets out of sync with the training data.
        """
        vector: dict[str, float] = {}
        for col in self._feature_columns:
            # Find which group_id this column belongs to
            matched_gid = None
            for gid, col_name in self._group_to_column.items():
                if col_name == col:
                    matched_gid = gid
                    break

            if matched_gid is not None and matched_gid in group_values:
                vector[col] = group_values[matched_gid]
            else:
                # Fallback: use 0.5 for L, 0.0 for X (median of training)
                logger.warning("Column %s has no registry mapping — using fallback value", col)
                vector[col] = 0.5 if "_L_" in col else 0.0

        return vector


# ── Module-level singleton ──────────────────────────────────────────────────
# Instantiated once at import time so the model is loaded once at startup.
# The FastAPI app imports this object directly.

_predictor: SurrogatePredictor | None = None


def get_predictor() -> SurrogatePredictor:
    """Return the module-level predictor singleton (lazy-initialised)."""
    global _predictor
    if _predictor is None:
        _predictor = SurrogatePredictor()
    return _predictor


# ── Sector predictor ─────────────────────────────────────────────────────────

SECTOR_DISPLAY_NAMES: dict[str, str] = {
    "agrc": "Agriculture",
    "frst": "Forestry (Carbon Sequestration)",
    "inen": "Industrial Energy",
    "ippu": "Industrial Processes",
    "lndu": "Land Use",
    "lsmm": "Livestock Manure Management",
    "lvst": "Livestock",
    "scoe": "Stationary Combustion (Cooking & Buildings)",
    "soil": "Soil Emissions",
    "trns": "Transportation",
    "trww": "Wastewater Treatment",
    "waso": "Solid Waste",
}

_SECTOR_CODES = list(SECTOR_DISPLAY_NAMES.keys())
_EMISSIONS_2019_CACHE: dict[str, float] | None = None


def _load_sector_emissions_2019() -> dict[str, float]:
    """Return per-sector MtCO2e for 2019 from the BAU-nearest S3 baseline run.

    Finds the LHS trial closest to BAU (all L=0.1, design_id=3) and reads
    time_period=4 (year 2019 = 2015 + 4) from the S3 model_outputs.
    Result is cached at module level.
    """
    global _EMISSIONS_2019_CACHE
    if _EMISSIONS_2019_CACHE is not None:
        return _EMISSIONS_2019_CACHE

    from backend.services.s3_lookup import find_nearest_lhs_trial, get_model_outputs_row

    bau_l_values = {gid: BAU_L_DEFAULT for gid in range(1, 60)}
    primary_id = find_nearest_lhs_trial(bau_l_values, design_id=3)
    outputs = get_model_outputs_row(primary_id)  # {col: [val_tp0, ..., val_tp55]}

    _EMISSIONS_2019_CACHE = {}
    for s in _SECTOR_CODES:
        col = f"emission_co2e_subsector_total_{s}"
        values = outputs.get(col, [])
        _EMISSIONS_2019_CACHE[s] = round(float(values[4]), 3) if len(values) > 4 else 0.0

    logger.info("Loaded 2019 sector baseline from S3 (primary_id=%d)", primary_id)
    return _EMISSIONS_2019_CACHE


class SectorPredictor:
    """
    Sector-level emission predictor backed by the multi-output XGBoost
    trained on 12 sectors × 4 time points (2030/2040/2050/2070).

    Uses the same 68 input features as SurrogatePredictor. Target column
    order is read from the training parquet at startup.

    Usage
    -----
    predictor = SectorPredictor()
    result = predictor.predict(lever_overrides={8: 0.9, 33: 0.8})
    # result["sector_trajectories"]["scoe"] → {2030: 45.2, 2040: 67.8, ...}
    """

    def __init__(self) -> None:
        self._model = self._load_model()
        self._feature_columns, self._group_to_column, self._target_columns = (
            self._load_training_metadata()
        )
        logger.info(
            "SectorPredictor ready. Features: %d, Sector targets: %d",
            len(self._feature_columns),
            len(self._target_columns),
        )

    def predict(
        self,
        lever_overrides: dict[int, float] | None = None,
        exogenous_overrides: dict[int, float] | None = None,
        preset_scenario: str = "bau",
        scenario_name: str = "Scenario",
    ) -> dict:
        """
        Run the sector surrogate for one scenario.

        Returns
        -------
        dict with keys:
            scenario_name  (str)
            group_values   (dict[int, float])
            sector_trajectories  (dict[str, dict[int, float]])
                Maps sector code → {year: Mt_CO2e}, e.g.
                {"scoe": {2030: 45.2, 2040: 67.8, 2050: 89.1, 2070: 106.5}, ...}
        """
        lever_overrides = lever_overrides or {}
        exogenous_overrides = exogenous_overrides or {}

        l_default, x_default = PRESET_DEFAULTS.get(preset_scenario, (BAU_L_DEFAULT, BAU_X_DEFAULT))

        if preset_scenario == "netzero":
            lever_overrides = {**NETZERO_L_OVERRIDES, **lever_overrides}

        group_values = self._build_group_values(lever_overrides, exogenous_overrides, l_default, x_default)
        feature_vector = self._build_feature_vector(group_values)

        X = np.array(list(feature_vector.values())).reshape(1, -1)
        raw_predictions = self._model.predict(X)[0]

        sector_trajectories: dict[str, dict[int, float]] = {}
        for i, col in enumerate(self._target_columns):
            if col.startswith("emission_") and "_yr" in col:
                sector, year_str = col.replace("emission_", "", 1).split("_yr")
                sector_trajectories.setdefault(sector, {})[int(year_str)] = round(float(raw_predictions[i]), 3)

        return {
            "scenario_name": scenario_name,
            "group_values": group_values,
            "sector_trajectories": sector_trajectories,
        }

    def predict_comparison(
        self,
        lever_overrides: dict[int, float] | None = None,
        exogenous_overrides: dict[int, float] | None = None,
        preset_scenario: str = "bau",
        scenario_name: str = "Scenario",
    ) -> dict:
        """
        Run scenario AND BAU baseline. Returns both plus absolute and % deltas per sector × year.
        """
        scenario = self.predict(lever_overrides, exogenous_overrides, preset_scenario, scenario_name)
        baseline = self.predict({}, {}, "bau", "Business as Usual (Baseline)")

        # Anchor both trajectories at the 2019 historical baseline (pre-policy divergence)
        emissions_2019 = _load_sector_emissions_2019()
        for sector, val in emissions_2019.items():
            scenario["sector_trajectories"].setdefault(sector, {})[2019] = val
            baseline["sector_trajectories"].setdefault(sector, {})[2019] = val

        sector_deltas: dict[str, dict[int, dict]] = {}
        for sector, traj in scenario["sector_trajectories"].items():
            sector_deltas[sector] = {}
            for year, val in traj.items():
                bau_val = baseline["sector_trajectories"].get(sector, {}).get(year, 0.0)
                abs_delta = round(val - bau_val, 3)
                pct_delta = round(100 * (val - bau_val) / abs(bau_val), 2) if bau_val != 0 else 0.0
                sector_deltas[sector][year] = {
                    "scenario": val,
                    "bau": round(bau_val, 3),
                    "delta": abs_delta,
                    "pct_change": pct_delta,
                }

        return {
            "scenario": scenario,
            "baseline": baseline,
            "sector_deltas": sector_deltas,
        }

    def get_sector_display_name(self, sector: str) -> str:
        return SECTOR_DISPLAY_NAMES.get(sector, sector.upper())

    # ── Private helpers ─────────────────────────────────────────────────────

    def _load_model(self):
        path = settings.model_sector_path
        if not path.exists():
            raise FileNotFoundError(
                f"Sector model not found at {path}. "
                "Update MODEL_SECTOR_PATH in config.py or .env."
            )
        model = joblib.load(path)
        logger.info("Loaded sector model from %s", path)
        return model

    def _load_training_metadata(self) -> tuple[list[str], dict[int, str], list[str]]:
        path = settings.training_data_sector_path
        if not path.exists():
            raise FileNotFoundError(
                f"Sector training data not found at {path}. "
                "Update TRAINING_DATA_SECTOR_PATH in config.py or .env."
            )

        df = pd.read_parquet(path)
        id_cols = {"future_id", "primary_id", "strategy_id", "design_id"}
        feature_cols = [c for c in df.columns if c.startswith("group_")]
        target_cols = [c for c in df.columns if c not in feature_cols and c not in id_cols]

        registry_path = settings.feature_registry_path
        with open(registry_path) as f:
            registry = json.load(f)

        group_to_column: dict[int, str] = {}
        for gid, meta in {**registry["lever_features"], **registry["exogenous_features"]}.items():
            group_to_column[int(gid)] = meta["training_column"]

        logger.info("Sector training metadata loaded. Features: %d, Targets: %d", len(feature_cols), len(target_cols))
        return feature_cols, group_to_column, target_cols

    def _build_group_values(
        self,
        lever_overrides: dict[int, float],
        exogenous_overrides: dict[int, float],
        l_default: float,
        x_default: float,
    ) -> dict[int, float]:
        group_values: dict[int, float] = {}
        for gid in range(1, 60):
            group_values[gid] = float(np.clip(lever_overrides.get(gid, l_default), 0.0, 1.0))
        for gid in range(60, 69):
            group_values[gid] = float(np.clip(exogenous_overrides.get(gid, x_default), -1.0, 1.0))
        return group_values

    def _build_feature_vector(self, group_values: dict[int, float]) -> dict[str, float]:
        vector: dict[str, float] = {}
        for col in self._feature_columns:
            matched_gid = next(
                (gid for gid, col_name in self._group_to_column.items() if col_name == col),
                None,
            )
            if matched_gid is not None and matched_gid in group_values:
                vector[col] = group_values[matched_gid]
            else:
                logger.warning("Column %s has no registry mapping — using fallback", col)
                vector[col] = 0.5 if "_L_" in col else 0.0
        return vector


_sector_predictor: SectorPredictor | None = None


def get_sector_predictor() -> SectorPredictor:
    """Return the module-level sector predictor singleton (lazy-initialised)."""
    global _sector_predictor
    if _sector_predictor is None:
        _sector_predictor = SectorPredictor()
    return _sector_predictor
