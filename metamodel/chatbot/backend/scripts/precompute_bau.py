"""
precompute_bau.py
-----------------
Builds the BAU feature vector (all L groups = 0.1, all X groups = -1.0),
runs a prediction, and writes the result to backend/bau_trajectory.json.

Run from repo root:
    conda run -n uganda_metamodel_env python metamodel/chatbot/backend/scripts/precompute_bau.py

The output file is read at request time by GET /api/bau — it is NOT
regenerated on every request.  Re-run this script whenever the model is
retrained or the BAU defaults change.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# ── Resolve paths (same logic as config.py) ──────────────────────────────────
_SCRIPTS_DIR   = Path(__file__).parent
_BACKEND_DIR   = _SCRIPTS_DIR.parent
_METAMODEL_DIR = _BACKEND_DIR.parent.parent

MODEL_PATH    = _METAMODEL_DIR / "surrogate_model" / "trained_models" / "xgb_pipeline_2025-11-12t22;19;28.194097.pkl"
PARQUET_PATH  = _METAMODEL_DIR / "data" / "training" / "training_data_w_suffix_2025-11-12t22;19;28.194097.parquet"
REGISTRY_PATH = _BACKEND_DIR / "feature_registry.json"
OUTPUT_PATH   = _BACKEND_DIR / "bau_trajectory.json"

TARGET_COLS = [
    "emission_total_sum",
    "2033_2037_mean_emission",
    "2066_2070_mean_emission",
    "2025_2035_mean_benefits",
    "2025_2070_mean_benefits",
    "2025_2035_mean_costs",
    "2025_2070_mean_costs",
    "2025_2035_max_costs_rel_to_gdp",
    "2025_2070_max_costs_rel_to_gdp",
    "2025_2035_cumulative_cost_rel_to_gdp",
    "2025_2070_cumulative_cost_rel_to_gdp",
]
ID_COLS = ["future_id", "primary_id", "strategy_id", "design_id"]

BAU_L = 0.1
BAU_X = -1.0


def main() -> None:
    # ── Load artifacts ────────────────────────────────────────────────────────
    print("Loading model ...", flush=True)
    model = joblib.load(MODEL_PATH)

    print("Loading training parquet (column order) ...", flush=True)
    df = pd.read_parquet(PARQUET_PATH)
    feature_cols = [c for c in df.columns if c not in TARGET_COLS and c not in ID_COLS]

    print("Loading feature registry ...", flush=True)
    with open(REGISTRY_PATH) as fh:
        registry = json.load(fh)

    group_to_col: dict[int, str] = {}
    for gid, meta in {
        **registry["lever_features"],
        **registry["exogenous_features"],
    }.items():
        group_to_col[int(gid)] = meta["training_column"]

    # ── Build BAU feature vector ──────────────────────────────────────────────
    col_to_value: dict[str, float] = {}
    for col in feature_cols:
        matched_gid = next((g for g, c in group_to_col.items() if c == col), None)
        if matched_gid is None:
            col_to_value[col] = 0.5
            print(f"  WARNING: {col} has no registry mapping — defaulting to 0.5", file=sys.stderr)
        elif 1 <= matched_gid <= 59:
            col_to_value[col] = BAU_L
        else:
            col_to_value[col] = BAU_X

    X = np.array(list(col_to_value.values())).reshape(1, -1)

    # ── Run prediction ────────────────────────────────────────────────────────
    print("Running BAU prediction ...", flush=True)
    raw = model.predict(X)[0]

    outputs = {target: round(float(raw[i]), 6) for i, target in enumerate(TARGET_COLS)}

    # ── Write output ──────────────────────────────────────────────────────────
    result = {
        "outputs": outputs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_PATH.name,
        "bau_defaults": {"L_groups_1_to_59": BAU_L, "X_groups_60_to_68": BAU_X},
    }

    with open(OUTPUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"\nWrote {OUTPUT_PATH}")
    print(f"  generated_at: {result['generated_at']}")
    print(f"  outputs ({len(outputs)}):")
    for k, v in outputs.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
