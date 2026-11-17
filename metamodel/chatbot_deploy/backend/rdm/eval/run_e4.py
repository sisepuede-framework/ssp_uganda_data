"""
E4 run (docs/run_design_E4_2026-11-17.md): the calibration-on-request arm C and a concurrent Map+ control P, on the
E3 questions. Same machinery as run_e3.py (preflight, interleaving, resume, _infra retries, credit stop).

    AWS_PROFILE=alexa python -m backend.rdm.eval.run_e4          (all 258 conversations)
    AWS_PROFILE=alexa python -m backend.rdm.eval.run_e4 --dry    (prints the plan, runs nothing)
        → backend/rdm/eval/pilot_runs/e4_{S,O,G}/<qid>_<arm>_r<rep>.json

Arms: v1 P (Map+, control, run again alongside C), v6 C (calibration on request + looking_for; tools/network.py).

| Set | Questions | Arms | Repetitions |
|---|---|---|---|
| e4_S (share-type, general; = E3 set S) | 12 | P, C | 5 |
| e4_O (other-type, general; = E3 set O) | 8  | P, C | 3 |
| e4_G (T1 translation guard; = E3 set G) | 15 | P, C | 3 |
"""
import argparse

from backend.rdm.eval import run_e3
from backend.rdm.eval.questions import E3_G, SETS
from backend.rdm.eval.run_bank import OutOfCredit, preflight
from backend.rdm.harness.agent import RUNS_DIR

PLAN = [  # (folder, question set, question ids, arms, repetitions)
    ("e4_S", "e3_S", list(SETS["e3_S"]), ["v1", "v6"], 5),
    ("e4_O", "e3_O", list(SETS["e3_O"]), ["v1", "v6"], 3),
    ("e4_G", "bank", E3_G, ["v1", "v6"], 3),
]


def jobs() -> list:
    out = []
    for rep in range(max(p[4] for p in PLAN)):
        for folder, qset, qids, arms, reps in PLAN:
            if rep < reps:
                out += [(folder, qset, q, arm, rep) for q in qids for arm in arms]
    return out


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--dry", action="store_true")
    args = a.parse_args()
    js = jobs()
    by = {}
    for folder, _, _, arm, _ in js:
        by[(folder, arm)] = by.get((folder, arm), 0) + 1
    print(f"{len(js)} conversations: " + ", ".join(f"{f} {a} {n}" for (f, a), n in sorted(by.items())), flush=True)
    if args.dry:
        raise SystemExit(0)
    preflight()
    for folder, *_ in PLAN:
        (RUNS_DIR / folder).mkdir(parents=True, exist_ok=True)
    try:
        failed = run_e3.run_all(js)
        for attempt in (1, 2):
            if not failed:
                break
            print(f"re-running {len(failed)} conversation(s) hit by infrastructure faults (round {attempt})", flush=True)
            failed = run_e3.run_all(failed)
    except OutOfCredit as e:
        raise SystemExit(f"STOPPED: API credit ran out ({e}). Top up and run again; finished conversations are kept.")
    done = sum(len(list((RUNS_DIR / f).glob("*_r*.json"))) for f, *_ in PLAN)
    print(f"done: {done} of {len(js)} conversations saved; {len(failed)} still failing (see _infra/)")
