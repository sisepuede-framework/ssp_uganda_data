"""
Source-label test (docs/preregistration_source_labels.md): HC1 × v0/v1 × 10 repetitions, one condition per call.

    python -m backend.rdm.eval.run_source_labels before
    python -m backend.rdm.eval.run_source_labels after
        → backend/rdm/eval/pilot_runs/source_labels_<condition>/HC1_<arm>_r<rep>.json

Every country_context 'gdp' reply is checked against the text pinned in the pre-registration (plus the label in
'after'); a conversation that saw a different reply is saved as *.mismatch.json and the run stops.
Runs that already exist are skipped, so an interrupted run resumes.
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.rdm.eval.questions import SETS
from backend.rdm.harness.agent import RUNS_DIR, converse

PREREG = Path(__file__).parents[3] / "docs" / "preregistration_source_labels.md"
QID, ARMS, REPS = "HC1", ("v0", "v1"), 10
LABEL = ("These values are SISEPUEDE's base future (future 0). It is not one of the experiment's runs, and its GDP is "
         "above the 90th percentile of the runs in 2040 and 2050. Do not read it as the middle of the futures explored.")


def pinned_reply(condition: str) -> dict:
    """The 'before' gdp reply, word for word from the pre-registration; 'after' adds the label to its text."""
    block = re.search(r'```\n(\{"topic": "gdp".*?\})\n```', PREREG.read_text(encoding="utf-8"), re.S).group(1)
    reply = json.loads(block)
    if condition == "after":
        reply["text"] += "\n\n" + LABEL
    return reply


def gdp_replies(run: dict) -> list:
    return [c["reply"] for c in run["tool_log"]
            if c["tool"] == "country_context" and (c.get("args") or {}).get("topic") == "gdp"]


def one(condition: str, arm: str, rep: int, out: Path, expected: dict) -> str:
    path = out / f"{QID}_{arm}_r{rep}.json"
    if path.exists():
        return f"skip {path.name}"
    q = SETS["bank"][QID]
    run = converse(q["question"], arm, q["replies"])
    run.update(question_id=QID, rep=rep, question_set="bank", condition=condition)
    bad = [r for r in gdp_replies(run) if r != expected]
    if bad:
        path = path.with_suffix(".mismatch.json")
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1, default=str))
    return f"{'MISMATCH' if bad else 'ok'} {path.name} steps={run['steps']} gdp_calls={len(gdp_replies(run))}"


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("condition", choices=["before", "after"])
    args = a.parse_args()
    expected = pinned_reply(args.condition)
    out = RUNS_DIR / f"source_labels_{args.condition}"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(arm, rep) for rep in range(REPS) for arm in ARMS]
    with ThreadPoolExecutor(5) as ex:
        for msg in ex.map(lambda j: one(args.condition, j[0], j[1], out, expected), jobs):
            print(msg, flush=True)
            if msg.startswith("MISMATCH"):
                raise SystemExit("country_context gdp reply differs from the pre-registered text; stopped")
