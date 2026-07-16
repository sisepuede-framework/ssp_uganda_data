"""
build_feature_registry.py
-------------------------
Generate backend/feature_registry.json from the NEW training parquet columns +
the VARIABLE_TRAJECTORY_GROUPS_{L,X} CSVs.

Why this exists: the registry maps each LHS trajectory group → its model feature
column, plus human metadata (display name, sector, semantics, aliases) used by the
predictor (group→column) and by the agent's system prompt. Group numbering and
column names change every run, so we rebuild it from the run's own files.

New run layout (vs old):
  - Levers L: groups 1–54 (was 1–59). Every L group is an NZ-strategy transformation
    (transformation_code TX:SECTOR:ACTION_STRATEGY_NZ) → sector + name derived from it.
  - Exogenous X: groups 55–67 (was 60–68), sampled in [0,1] (was [-1,1]).

Re-run after retraining on a new run:
    python -m backend.scripts.build_feature_registry
"""

import json
import re
from pathlib import Path

import pandas as pd

_BACKEND_DIR = Path(__file__).parent.parent
_METAMODEL_DIR = _BACKEND_DIR.parent.parent
RUN_ID = "2026-05-30t21;35;56.244639"
_PARQUET = _METAMODEL_DIR / "data" / "training" / f"training_data_sector_{RUN_ID}.parquet"
_SSP_DIR = _METAMODEL_DIR / "data" / "ssp" / f"sisepuede_run_{RUN_ID}"
_OUT = _BACKEND_DIR / "feature_registry.json"

# SISEPUEDE subsector/sector codes (from TX:<CODE>:...) → display sector.
SECTOR_NAMES = {
    "AGRC": "Agriculture", "ENTC": "Electricity", "FGTV": "Fugitive Emissions",
    "FRST": "Forestry", "INEN": "Industrial Energy", "IPPU": "Industrial Processes",
    "LNDU": "Land Use", "LSMM": "Livestock Manure Management", "LVST": "Livestock",
    "PFLO": "Cross-Sector", "SCOE": "Buildings & Other Combustion",
    "TRDE": "Transport Demand", "TRNS": "Transportation", "TRWW": "Wastewater",
    "WALI": "Water & Wastewater Treatment", "WASO": "Solid Waste",
}
VERBS = {"DEC": "Reduce", "INC": "Increase", "TARGET": "Target", "SHIFT": "Shift",
         "SET": "Set", "TARGET_RENEWABLE": "Target Renewable"}

# Curated metadata for the 13 exogenous (X) groups — small set, worth hand-naming.
X_META = {
    "exports":               ("Agricultural Export Volumes", "Macroeconomic / Trade"),
    "cost_enfu_fuel":        ("Fossil Fuel Prices", "Energy Markets"),
    "gdp_mmm_usd":           ("GDP Growth Trajectory", "Macroeconomic"),
    "elasticity_ippu":       ("Industrial Output Elasticity (to GDP)", "Industry"),
    "elasticity_ippu_product_use": ("Industrial Product-Use Elasticity (to GDP/cap)", "Industry"),
    "population_gnrl":       ("Population Growth", "Demographics"),
    "elasticity_scoe":       ("Building Energy-Demand Elasticity (to GDP/cap)", "Buildings"),
    "nemomod_enst":          ("Battery Storage Capital Cost", "Energy Technology"),
    "nemomod_entc_capital_cost_pp_coal": ("Coal Power Plant Capital Cost", "Energy Technology"),
    "nemomod_entc_capital_cost_pp_nuclear": ("Nuclear Power Plant Capital Cost", "Energy Technology"),
    "nemomod_entc_capital_cost_pp_geothermal": ("Geothermal Power Plant Capital Cost", "Energy Technology"),
    "nemomod_entc":          ("Power Plant Capital Cost", "Energy Technology"),
    "elasticity_trde_mtkm_to_gdp_freight": ("Freight Transport Demand Elasticity", "Transport Demand"),
    "elasticity_trde_pkm_to_gdppc": ("Passenger Transport Demand Elasticity", "Transport Demand"),
}


def _humanize_l(tcode: str) -> tuple[str, str]:
    """(display_name, sector) from a transformation code TX:SECTOR:ACTION_STRATEGY_NZ."""
    parts = tcode.split(":")
    sector_code = parts[1] if len(parts) > 1 else ""
    action = parts[2] if len(parts) > 2 else tcode
    action = re.sub(r"_STRATEGY_NZ$|_NZ$", "", action)
    tokens = action.split("_")
    verb = VERBS.get(tokens[0], tokens[0].title())
    rest = " ".join(t.title() if not t.isupper() else t for t in tokens[1:])
    name = f"{verb} {rest}".strip()
    return name, SECTOR_NAMES.get(sector_code, sector_code or "Other")


def _x_meta(variable: str) -> tuple[str, str]:
    # Match the most specific (longest) key first so e.g. elasticity_ippu_product_use
    # wins over elasticity_ippu, and ..._pp_coal wins over the generic nemomod_entc.
    for key in sorted(X_META, key=len, reverse=True):
        if variable.startswith(key):
            return X_META[key]
    return variable.replace("_", " ").title(), "Exogenous"


def _aliases(name: str, extra: list[str]) -> list[str]:
    words = re.findall(r"[a-z0-9]+", name.lower())
    seen, out = set(), []
    for w in words + [e.lower() for e in extra]:
        if len(w) > 2 and w not in seen:
            seen.add(w); out.append(w)
    return out


def main() -> None:
    df = pd.read_parquet(_PARQUET, columns=None)
    feat_cols = [c for c in df.columns if c.startswith("group_")]

    vt_l = pd.read_csv(_SSP_DIR / "VARIABLE_TRAJECTORY_GROUPS_L.csv")
    l_tcode = vt_l.groupby("variable_trajectory_group")["transformation_code"].first().to_dict()
    vt_x = pd.read_csv(_SSP_DIR / "VARIABLE_TRAJECTORY_GROUPS_X.csv")
    x_var = vt_x.groupby("variable_trajectory_group")["variable"].first().to_dict()

    lever_features: dict[str, dict] = {}
    exogenous_features: dict[str, dict] = {}

    for col in feat_cols:
        m = re.match(r"group_(\d+)_([XL])_(.*)$", col, re.DOTALL)
        if not m:
            continue
        gid, kind, suffix = int(m.group(1)), m.group(2), m.group(3).strip()
        if kind == "L":
            tcode = l_tcode.get(gid, "")
            name, sector = _humanize_l(tcode)
            lever_features[str(gid)] = {
                "group_id": gid,
                "training_column": col,
                "display_name": name or suffix or f"Lever {gid}",
                "sector": sector,
                "transformation_code": tcode,
                "scale_min": 0.0,
                "scale_max": 1.0,
                "semantic_min": f'No policy action (baseline): the "{name}" measure is not '
                                f"pursued; the {sector} sector stays on its business-as-usual path.",
                "semantic_max": f'Maximum ambition: "{name}" is deployed to its full technically '
                                f"feasible extent by 2070.",
                "policy_description": f"Policy lever ({sector}). 0 = no action, 1 = maximum "
                                     f"technically feasible deployment by 2070 ({tcode}).",
                "aliases": _aliases(name, [sector]),
            }
        else:  # X
            name, sector = _x_meta(x_var.get(gid, suffix))
            exogenous_features[str(gid)] = {
                "group_id": gid,
                "training_column": col,
                "display_name": name,
                "sector": f"Exogenous / {sector}",
                "scale_min": 0.0,
                "scale_max": 1.0,
                "semantic_0": f"Low end of the {name.lower()} uncertainty range.",
                "semantic_05": f"Median (central) {name.lower()} future.",
                "semantic_1": f"High end of the {name.lower()} uncertainty range.",
                "policy_description": f"Exogenous uncertainty ({sector}) — external condition "
                                     f"beyond policy control. Sampled in [0,1].",
                "aliases": _aliases(name, [sector]),
            }

    payload = {
        "_metadata": {
            "version": "2.0.0",
            "model_run_id": RUN_ID,
            "n_lever_features": len(lever_features),
            "n_exogenous_features": len(exogenous_features),
            "note": "Rebuilt for the 2026-05-30 run. L groups 1-54 (NZ transformations), "
                    "X groups 55-67 sampled in [0,1].",
        },
        "lever_features": lever_features,
        "exogenous_features": exogenous_features,
        "preset_scenarios": {
            "bau": {"name": "Business as Usual (BAU)", "l_default": 0.1, "x_default": 0.5,
                    "description": "Minimal policy action; median (central) uncertainty future."},
            "moderate": {"name": "Moderate Ambition", "l_default": 0.5, "x_default": 0.5,
                         "description": "Moderate policy across all sectors; median future."},
            "netzero": {"name": "Net Zero", "l_default": 1.0, "x_default": 0.5,
                        "description": "Full deployment of all NZ-strategy levers; median future."},
        },
    }

    with open(_OUT, "w") as f:
        json.dump(payload, f, indent=1)

    print(f"Wrote {_OUT}")
    print(f"  lever_features: {len(lever_features)} (groups "
          f"{min(int(k) for k in lever_features)}-{max(int(k) for k in lever_features)})")
    print(f"  exogenous_features: {len(exogenous_features)} (groups "
          f"{min(int(k) for k in exogenous_features)}-{max(int(k) for k in exogenous_features)})")
    print("\n  Sample levers:")
    for gid in list(lever_features)[:4]:
        print(f"    {gid}: {lever_features[gid]['display_name']}  [{lever_features[gid]['sector']}]")
    print("  Exogenous:")
    for gid in exogenous_features:
        print(f"    {gid}: {exogenous_features[gid]['display_name']}  [{exogenous_features[gid]['sector']}]")


if __name__ == "__main__":
    main()
