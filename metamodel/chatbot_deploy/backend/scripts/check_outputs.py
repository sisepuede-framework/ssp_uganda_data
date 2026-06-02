"""
check_outputs.py
----------------
Runs a BAU prediction (all L=0.1, all X=-1.0) through the sector surrogate and
prints every aggregate output field alongside its value, unit, and description
from feature_registry.json.

Usage (from repo root):
    conda run -n uganda_metamodel_env python -m backend.scripts.check_outputs

Delegates to SectorPredictor so it uses the exact same (name-aligned) prediction
path as the live server.
"""

import json
from pathlib import Path

from backend.config import settings
from backend.services.predictor import get_sector_predictor

REGISTRY_PATH = Path(__file__).parent.parent / "feature_registry.json"


def _wrap(text: str, width: int = 68) -> list[str]:
    words, line, lines = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    return lines


def main() -> None:
    print("Loading sector model ...", flush=True)
    predictor = get_sector_predictor()

    with open(REGISTRY_PATH) as fh:
        outputs_meta = json.load(fh)["outputs"]

    print("Running BAU prediction ...\n", flush=True)
    scenario = predictor.predict(preset_scenario="bau", scenario_name="Business as Usual (Baseline)")
    predictions = scenario["predictions"]

    print("=" * 72)
    print("  BAU PREDICTION  (all L = 0.1, all X = -1.0)")
    print("=" * 72)

    for target, pred in predictions.items():
        value = pred["value"]
        meta = outputs_meta.get(target, {})

        display_name = meta.get("display_name", pred["display_name"])
        unit = meta.get("unit", pred["unit"])
        description = meta.get("description", "")
        tr = meta.get("training_range", pred.get("training_range", {}))
        tr_min, tr_max = tr.get("min"), tr.get("max")
        policy_ctx = meta.get("policy_context", "")

        is_gdp_rel = "rel_to_gdp" in target
        display_value = f"{value:.6f}" if is_gdp_rel else f"{value:.4f}"
        pct_note = f"  ({value * 100:.4f}%)" if is_gdp_rel else ""

        print(f"\n{'─' * 72}")
        print(f"  {display_name}")
        print(f"  Key:   {target}")
        print(f"  Value: {display_value} {unit}{pct_note}")
        print(f"  Percentile in training: {pred['percentile_in_training']}")
        if tr_min is not None and tr_max is not None:
            frac = (value - tr_min) / (tr_max - tr_min) if tr_max != tr_min else 0.0
            print(f"  Training range: {tr_min} – {tr_max}  (BAU sits at {frac * 100:.1f}% of range)")
        if description:
            lines = _wrap(description)
            print(f"  Desc:  {lines[0]}")
            for l in lines[1:]:
                print(f"         {l}")
        if policy_ctx:
            lines = _wrap(policy_ctx)
            print(f"  Context: {lines[0]}")
            for l in lines[1:]:
                print(f"           {l}")

    print(f"\n{'=' * 72}")
    print(f"  {len(predictions)} outputs printed.  Model: {settings.model_sector_path.name}")
    print("=" * 72)


if __name__ == "__main__":
    main()
