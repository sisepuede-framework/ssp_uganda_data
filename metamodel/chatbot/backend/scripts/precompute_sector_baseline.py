"""
precompute_sector_baseline.py
-----------------------------
Fetches per-sector MtCO2e emissions for year 2019 from the BAU-nearest
SISEPUEDE run on S3, then writes the result to backend/sector_baseline_2019.json.

Run from repo root:
    conda run -n uganda_metamodel_env python metamodel/chatbot/backend/scripts/precompute_sector_baseline.py

Re-run only if the underlying SISEPUEDE run data changes (it won't — 2019 is
a historical baseline). The output file is committed to the repo so the server
never needs AWS credentials just to anchor the sector chart at 2019.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
_BACKEND_DIR = _SCRIPTS_DIR.parent
_CHATBOT_DIR = _BACKEND_DIR.parent  # metamodel/chatbot/ — makes `backend` importable

sys.path.insert(0, str(_CHATBOT_DIR))

OUTPUT_PATH = _BACKEND_DIR / "sector_baseline_2019.json"

BAU_L_DEFAULT = 0.1

SECTOR_CODES = [
    "agrc", "frst", "inen", "ippu", "lndu", "lsmm",
    "lvst", "scoe", "soil", "trns", "trww", "waso",
]


def main() -> None:
    from backend.services.s3_lookup import find_nearest_lhs_trial, get_model_outputs_row

    print("Finding BAU-nearest LHS trial (design_id=3) ...", flush=True)
    bau_l_values = {gid: BAU_L_DEFAULT for gid in range(1, 60)}
    primary_id = find_nearest_lhs_trial(bau_l_values, design_id=3)
    print(f"  primary_id: {primary_id}", flush=True)

    print("Fetching model outputs row from S3 ...", flush=True)
    outputs = get_model_outputs_row(primary_id)  # {col: [val_tp0, ..., val_tp55]}

    # time_period=4 corresponds to year 2015+4 = 2019
    sector_values: dict[str, float] = {}
    for s in SECTOR_CODES:
        col = f"emission_co2e_subsector_total_{s}"
        values = outputs.get(col, [])
        sector_values[s] = round(float(values[4]), 3) if len(values) > 4 else 0.0

    result = {
        "emissions_2019": sector_values,
        "primary_id": primary_id,
        "time_period": 4,
        "year": 2019,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Static historical baseline. Re-run only if S3 run data changes.",
    }

    with open(OUTPUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"\nWrote {OUTPUT_PATH}")
    print(f"  Sectors ({len(sector_values)}):")
    for sector, val in sector_values.items():
        print(f"    {sector}: {val} MtCO2e")


if __name__ == "__main__":
    main()
