"""
E3 run (docs/run_design_E3_2026-11-17.md): every set, arm and repetition in one interleaved job list.

    AWS_PROFILE=alexa python -m backend.rdm.eval.run_e3          (all 393 conversations)
    AWS_PROFILE=alexa python -m backend.rdm.eval.run_e3 --dry    (prints the plan, runs nothing)
        → backend/rdm/eval/pilot_runs/e3_{S,SX,O,G}/<qid>_<arm>_r<rep>.json

Arms: v1 P (Map+, control), v3 H (calibration hidden), v4 L (role sentence in the lever's reply), v5 T (the same
sentence in the tool description).

| Set | Questions | Arms | Repetitions |
|---|---|---|---|
| e3_S  (share-type, general)  | 12 | P, H, L, T | 5 |
| e3_SX (share-type, explicit) | 12 | P          | 5 |
| e3_O  (other-type, general)  | 8  | P, H       | 3 |
| e3_G  (T1 guard, bank set)   | 15 | P, L, T    | 1 |

Order: repetition by repetition; within a repetition, question by question with every set and arm of that
question together, 5 conversations at a time. As run_bank.py: preflight (committed code, AWS + labelled
country_context, API key); existing logs are skipped, so a stopped run resumes; infrastructure faults are set apart
under _infra/ and retried up to twice; a run out of API credit stops at once. No conversation is dropped for what the
agent did.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import anthropic

from backend.rdm.eval.questions import E3_G, SETS
from backend.rdm.eval.run_bank import INFRA_CODES, OutOfCredit, preflight
from backend.rdm.harness.agent import RUNS_DIR, converse

PLAN = [  # (folder, question set used for questions and scoring, question ids, arms, repetitions)
    ("e3_S", "e3_S", list(SETS["e3_S"]), ["v1", "v3", "v4", "v5"], 5),
    ("e3_SX", "e3_SX", list(SETS["e3_SX"]), ["v1"], 5),
    ("e3_O", "e3_O", list(SETS["e3_O"]), ["v1", "v3"], 3),
    ("e3_G", "bank", E3_G, ["v1", "v4", "v5"], 1),
]


def jobs() -> list:
    out = []
    for rep in range(max(p[4] for p in PLAN)):
        for folder, qset, qids, arms, reps in PLAN:
            if rep < reps:
                out += [(folder, qset, q, arm, rep) for q in qids for arm in arms]
    return out


def _infra(folder: str, name: str, record: dict) -> str:
    d = RUNS_DIR / folder / "_infra"
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob(f"{name}.try*.json"))) + 1
    (d / f"{name}.try{n}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str))
    return f"INFRA {folder}/{name} (try {n}): {record['error'][:120]}"


def one(folder: str, qset: str, qid: str, arm: str, rep: int) -> str:
    path = RUNS_DIR / folder / f"{qid}_{arm}_r{rep}.json"
    if path.exists():
        return f"skip {folder}/{path.name}"
    q = SETS[qset][qid]
    base = {"question_id": qid, "arm": arm, "rep": rep, "question_set": qset}
    try:
        run = converse(q["question"], arm, q["replies"])
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e):
            raise OutOfCredit(str(e)) from e
        return _infra(folder, path.stem, {**base, "error": f"{type(e).__name__}: {e}"})
    except anthropic.APIConnectionError as e:
        return _infra(folder, path.stem, {**base, "error": f"{type(e).__name__}: {e}"})
    run.update(question_id=qid, rep=rep, question_set=qset, condition="e3")
    faults = sorted({c.get("error_code") for c in run["tool_log"]} & INFRA_CODES)
    if faults:
        return _infra(folder, path.stem, {**run, "error": f"infrastructure fault in a tool: {faults}"})
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1, default=str))
    return f"ok {folder}/{path.name} steps={run['steps']} {run['seconds']}s"


def run_all(js: list) -> list:
    failed = []
    with ThreadPoolExecutor(5) as ex:
        for j, msg in zip(js, ex.map(lambda j: one(*j), js)):
            print(msg, flush=True)
            if msg.startswith("INFRA"):
                failed.append(j)
    return failed


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
        failed = run_all(js)
        for attempt in (1, 2):
            if not failed:
                break
            print(f"re-running {len(failed)} conversation(s) hit by infrastructure faults (round {attempt})", flush=True)
            failed = run_all(failed)
    except OutOfCredit as e:
        raise SystemExit(f"STOPPED: API credit ran out ({e}). Top up and run again; finished conversations are kept.")
    done = sum(len(list((RUNS_DIR / f).glob("*_r*.json"))) for f, *_ in PLAN)
    print(f"done: {done} of {len(js)} conversations saved; {len(failed)} still failing (see _infra/)")
