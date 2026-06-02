"""
precompute_bau.py
-----------------
Runs the BAU scenario (all L groups = 0.1, all X groups = -1.0) through the
sector surrogate and writes the 11 aggregate metrics to backend/bau_trajectory.json.

Run from repo root:
    conda run -n uganda_metamodel_env python -m backend.scripts.precompute_bau

The output file is read at request time by GET /api/bau — it is NOT regenerated
on every request. Re-run this script whenever the model is retrained or the BAU
defaults change.

This delegates to SectorPredictor so it uses the exact same (name-aligned)
prediction path as the live server — no hand-built feature vectors, no risk of
the positional feature-ordering bug.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings
from backend.services.predictor import BAU_L_DEFAULT, BAU_X_DEFAULT, get_sector_predictor

OUTPUT_PATH = Path(__file__).parent.parent / "bau_trajectory.json"


def main() -> None:
    print("Loading sector model ...", flush=True)
    predictor = get_sector_predictor()

    print("Running BAU prediction ...", flush=True)
    scenario = predictor.predict(preset_scenario="bau", scenario_name="Business as Usual (Baseline)")

    outputs = {
        target: round(pred["value"], 6) for target, pred in scenario["predictions"].items()
    }

    result = {
        "outputs": outputs,
        "cost_benefit": scenario["cost_benefit"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.model_sector_path.name,
        "bau_defaults": {"L_groups_1_to_59": BAU_L_DEFAULT, "X_groups_60_to_68": BAU_X_DEFAULT},
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
