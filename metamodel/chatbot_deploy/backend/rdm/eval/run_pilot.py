"""
Pilot runner: every question of a set × arms × repetitions.

    python -m backend.rdm.eval.run_pilot --set pilot --reps 3                         (v0, v1)
    python -m backend.rdm.eval.run_pilot --set pairs --reps 3 --arms v0 v1_inputs v1_outputs v1
        → backend/rdm/eval/pilot_runs/<model>/<set>/<qid>_<arm>_r<rep>.json
Runs that already exist are skipped, so an interrupted pilot resumes.
"""

import argparse
import itertools

from backend.rdm.eval.questions import SETS
from backend.rdm.harness.agent import MODEL, RUNS_DIR, run_one

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--set", default="pilot", choices=list(SETS))
    a.add_argument("--reps", type=int, default=3)
    a.add_argument("--arms", nargs="+", default=["v0", "v1"])
    args = a.parse_args()
    for rep, qid, arm in itertools.product(range(args.reps), SETS[args.set], args.arms):
        if (RUNS_DIR / MODEL / args.set / f"{qid}_{arm}_r{rep}.json").exists():
            continue
        try:
            print(run_one(qid, arm, rep, args.set), flush=True)
        except Exception as e:  # noqa: BLE001 — record and keep going
            print(f"FAILED {qid} {arm} r{rep}: {type(e).__name__}: {e}", flush=True)
