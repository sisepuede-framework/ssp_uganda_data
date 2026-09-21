"""
check_outputs.py
----------------
Runs a BAU prediction (all L=0.1, all X=-1.0) using the trained XGBoost
pipeline and prints every output field alongside its value, unit, and
description from feature_registry.json.

Usage (from repo root):
    conda run -n uganda_metamodel_env python metamodel/chatbot/backend/scripts/check_outputs.py
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# ── Resolve paths the same way config.py does ───────────────────────────────
_SCRIPTS_DIR  = Path(__file__).parent
_BACKEND_DIR  = _SCRIPTS_DIR.parent
_METAMODEL_DIR = _BACKEND_DIR.parent.parent

MODEL_PATH    = _METAMODEL_DIR / "surrogate_model" / "trained_models" / "xgb_pipeline_2025-11-12t22;19;28.194097.pkl"
PARQUET_PATH  = _METAMODEL_DIR / "data" / "training" / "training_data_w_suffix_2025-11-12t22;19;28.194097.parquet"
REGISTRY_PATH = _BACKEND_DIR / "feature_registry.json"

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
    # ── Load artifacts ───────────────────────────────────────────────────────
    print("Loading model ...", flush=True)
    model = joblib.load(MODEL_PATH)

    print("Loading training parquet (column order) ...", flush=True)
    df = pd.read_parquet(PARQUET_PATH)
    feature_cols = [c for c in df.columns if c not in TARGET_COLS and c not in ID_COLS]

    print("Loading feature registry ...", flush=True)
    with open(REGISTRY_PATH) as fh:
        registry = json.load(fh)

    # group_id (int) → training column name
    group_to_col: dict[int, str] = {}
    for gid, meta in {
        **registry["lever_features"],
        **registry["exogenous_features"],
    }.items():
        group_to_col[int(gid)] = meta["training_column"]

    # ── Build BAU feature vector ─────────────────────────────────────────────
    col_to_value: dict[str, float] = {}
    for col in feature_cols:
        matched_gid = next((g for g, c in group_to_col.items() if c == col), None)
        if matched_gid is None:
            # Should never happen after verify-columns passed; use safe fallback
            col_to_value[col] = 0.5
            print(f"  WARNING: {col} has no registry mapping — defaulting to 0.5", file=sys.stderr)
        elif 1 <= matched_gid <= 59:
            col_to_value[col] = BAU_L   # L feature
        else:
            col_to_value[col] = BAU_X   # X feature

    X = np.array(list(col_to_value.values())).reshape(1, -1)

    # ── Run prediction ───────────────────────────────────────────────────────
    print("Running BAU prediction ...\n", flush=True)
    raw = model.predict(X)[0]  # shape (n_targets,)

    outputs_meta = registry["outputs"]

    # ── Print results ────────────────────────────────────────────────────────
    print("=" * 72)
    print("  BAU PREDICTION  (all L = 0.1, all X = -1.0)")
    print("=" * 72)

    for i, target in enumerate(TARGET_COLS):
        value = float(raw[i])
        meta  = outputs_meta.get(target, {})

        display_name = meta.get("display_name", target)
        unit         = meta.get("unit", "—")
        description  = meta.get("description", "")
        tr           = meta.get("training_range", {})
        tr_min       = tr.get("min")
        tr_max       = tr.get("max")
        policy_ctx   = meta.get("policy_context", "")

        # GDP-relative outputs are decimal fractions; show both raw and as %
        is_gdp_rel = "rel_to_gdp" in target
        display_value = f"{value:.6f}" if is_gdp_rel else f"{value:.4f}"
        pct_note      = f"  ({value * 100:.4f}%)" if is_gdp_rel else ""

        print(f"\n{'─' * 72}")
        print(f"  {display_name}")
        print(f"  Key:   {target}")
        print(f"  Value: {display_value} {unit}{pct_note}")
        if tr_min is not None and tr_max is not None:
            # Where does this value sit in the training range?
            frac = (value - tr_min) / (tr_max - tr_min) if tr_max != tr_min else 0.0
            print(f"  Training range: {tr_min} – {tr_max}  (BAU sits at {frac * 100:.1f}% of range)")
        if description:
            # Wrap description at 68 chars
            words, line = description.split(), ""
            lines = []
            for w in words:
                if len(line) + len(w) + 1 > 68:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            print(f"  Desc:  {lines[0]}")
            for l in lines[1:]:
                print(f"         {l}")
        if policy_ctx:
            words, line = policy_ctx.split(), ""
            lines = []
            for w in words:
                if len(line) + len(w) + 1 > 68:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            print(f"  Context: {lines[0]}")
            for l in lines[1:]:
                print(f"           {l}")

    print(f"\n{'=' * 72}")
    print(f"  {len(TARGET_COLS)} outputs printed.  Model: {MODEL_PATH.name}")
    print("=" * 72)


if __name__ == "__main__":
    main()
