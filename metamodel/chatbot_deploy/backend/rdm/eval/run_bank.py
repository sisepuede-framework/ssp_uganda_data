"""
Full bank run (docs/question_bank_v3.md, "Run design"): every bank conversation × arms × repetitions.

    AWS_PROFILE=alexa python -m backend.rdm.eval.run_bank                 (v0 v1, 5 repetitions)
        → backend/rdm/eval/pilot_runs/bank_v3_full/<qid>_<arm>_r<rep>.json

Before it starts: the RDM code and backend/services are committed, the AWS login works and country_context returns
the labelled GDP reply, and the API key answers. Conversations run 5 at a time, repetition by repetition, so a
stopped run is balanced across arms. Runs that already exist are skipped, so a stopped run resumes.

A conversation hit by an infrastructure fault (country_context could not reach AWS, or the API call failed) is
saved under _infra/ — not with the results — and run again at the end, up to two more times. A run out of API
credit stops at once.
"""

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from backend.config import settings
from backend.rdm.eval.questions import SETS
from backend.rdm.eval.run_source_labels import pinned_reply
from backend.rdm.harness.agent import MODEL, RUNS_DIR, converse
from backend.rdm.tools.context import country_context

OUT = RUNS_DIR / "bank_v3_full"
INFRA_CODES = {"CONTEXT_UNAVAILABLE"}
ROOT = Path(__file__).parents[3]


class OutOfCredit(Exception):
    pass


def preflight():
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "backend/rdm", "backend/services",
                            ":(exclude)backend/rdm/eval/pilot_runs"], capture_output=True, text=True, cwd=ROOT).stdout
    if dirty.strip():
        raise SystemExit(f"Uncommitted changes in the code the run uses; commit first:\n{dirty}")
    reply = country_context("gdp")
    if reply != pinned_reply("after"):
        raise SystemExit("country_context gdp reply is not the labelled one (AWS login expired?)")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    client.messages.create(model=MODEL, max_tokens=16, messages=[{"role": "user", "content": "ok"}])
    print("preflight ok: code committed, AWS + labelled country_context, API key", flush=True)


def one(qid: str, arm: str, rep: int) -> str:
    path = OUT / f"{qid}_{arm}_r{rep}.json"
    if path.exists():
        return f"skip {path.name}"
    q = SETS["bank"][qid]
    try:
        run = converse(q["question"], arm, q["replies"])
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e):
            raise OutOfCredit(str(e)) from e
        return _infra(path, {"question_id": qid, "arm": arm, "rep": rep, "error": f"{type(e).__name__}: {e}"})
    except anthropic.APIConnectionError as e:
        return _infra(path, {"question_id": qid, "arm": arm, "rep": rep, "error": f"{type(e).__name__}: {e}"})
    run.update(question_id=qid, rep=rep, question_set="bank", condition="full")
    faults = sorted({c.get("error_code") for c in run["tool_log"]} & INFRA_CODES)
    if faults:
        return _infra(path, {**run, "error": f"infrastructure fault in a tool: {faults}"})
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1, default=str))
    return f"ok {path.name} steps={run['steps']} {run['seconds']}s"


def _infra(path: Path, record: dict) -> str:
    d = OUT / "_infra"
    d.mkdir(exist_ok=True)
    n = len(list(d.glob(f"{path.stem}.try*.json"))) + 1
    (d / f"{path.stem}.try{n}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str))
    return f"INFRA {path.name} (try {n}): {record['error'][:120]}"


def run_all(jobs: list) -> list:
    """Runs the jobs 5 at a time; returns those that hit an infrastructure fault."""
    failed = []
    with ThreadPoolExecutor(5) as ex:
        for (qid, arm, rep), msg in zip(jobs, ex.map(lambda j: one(*j), jobs)):
            print(msg, flush=True)
            if msg.startswith("INFRA"):
                failed.append((qid, arm, rep))
    return failed


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--reps", type=int, default=5)
    a.add_argument("--arms", nargs="+", default=["v0", "v1"])
    args = a.parse_args()
    preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(qid, arm, rep) for rep in range(args.reps) for qid in SETS["bank"] for arm in args.arms]
    try:
        failed = run_all(jobs)
        for attempt in (1, 2):
            if not failed:
                break
            print(f"re-running {len(failed)} conversation(s) hit by infrastructure faults (round {attempt})", flush=True)
            failed = run_all(failed)
    except OutOfCredit as e:
        raise SystemExit(f"STOPPED: API credit ran out ({e}). Top up and run again; finished conversations are kept.")
    done = len([p for p in OUT.glob("*_r*.json")])
    print(f"done: {done} of {len(jobs)} conversations saved; {len(failed)} still failing (see _infra/)")
