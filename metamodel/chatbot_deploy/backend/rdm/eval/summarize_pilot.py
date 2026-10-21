"""
Summarise the pilot runs: what each agent did (tools, parameters), cost, and simple answer checks.

    python -m backend.rdm.eval.summarize_pilot      → prints a table; writes pilot_runs/summary.csv

The checks are mechanical and partial — they flag, they do not score. Reading the answers is still
needed (pilot_runs/<qid>_<arm>_r<rep>.json, field "answers").
"""

import json
import re

import pandas as pd

import sys

from backend.rdm.eval.questions import REFERENCE
from backend.rdm.harness.agent import MODEL, RUNS_DIR

REF = json.loads(REFERENCE.read_text()) if REFERENCE.exists() else {}

INFO = {"model_network", "country_context"}
PRICES = {"claude-opus-5-5": {"in": 4.0, "cache_read": 0.4, "cache_write": 5.0, "out": 20.0},   # USD per million tokens
          "claude-sonnet-5-5": {"in": 2.0, "cache_read": 0.2, "cache_write": 2.5, "out": 10.0}}
FORBIDDEN = re.compile(r"\b(will (?:reduce|increase|cut|fall|rise|be)|predicts?|forecasts?|the best|you should|recommend)\b", re.I)


def levers_set(log: list) -> list:
    out = []
    for e in log:
        if e["tool"] == "exploratory_modeling":
            for p in e["args"].get("policies", []):
                out.append(f"{p.get('name')}: " + ", ".join(f"L{k}={v}" for k, v in (p.get("levers") or {}).items()))
    return out


def summarise(path) -> dict:
    r = json.loads(path.read_text())
    log = r["tool_log"]
    req = r["requests"]
    PRICE = PRICES[r["model"]]
    cost = sum(q["input_tokens"] * PRICE["in"] + q["cache_read"] * PRICE["cache_read"]
               + q["cache_write"] * PRICE["cache_write"] + q["output_tokens"] * PRICE["out"] for q in req) / 1e6
    answer = r["answers"][-1] if r["answers"] else ""
    vuln = [e for e in log if e["tool"] == "vulnerability_analysis"]
    row = {
        "question": r["question_id"], "arm": r["arm"], "rep": r["rep"],
        "tools": " → ".join(e["tool"] for e in log),
        "n_info_calls": sum(e["tool"] in INFO for e in log),
        "n_tool_errors": sum(e["status"] == "error" for e in log),
        "policies": " | ".join(levers_set(log)),
        "asked_user": len(r["answers"]) > 1,
        "threshold_used": "; ".join(f"{e['args'].get('threshold')} {e['args'].get('threshold_type', 'absolute')}"
                                    for e in vuln if e["args"].get("threshold") is not None),
        "x_ranges": "; ".join(json.dumps(e["args"].get("x_ranges")) for e in log
                              if e["tool"] == "exploratory_modeling" and e["args"].get("x_ranges")),
        "forbidden_words": ", ".join(sorted({m.group(0).lower() for m in FORBIDDEN.finditer(answer)
                                             if not re.search(r"\bnot (?:a |an )?$", answer[max(0, m.start() - 8):m.start()])})),
        "steps": r["steps"], "stop": r["final_stop_reason"], "seconds": r["seconds"],
        "info_reply_chars": sum(e["reply_chars"] for e in log if e["tool"] in INFO),
        "cost_usd": round(cost, 3),
    }
    row["n_runs"] = sum(e["tool"] == "exploratory_modeling" for e in log)
    lever = {"Q04b": 35}.get(r["question_id"]) or REF.get(r["question_id"], {}).get("lever")
    if lever:
        lv = [float(v) for e in log if e["tool"] == "exploratory_modeling" for p in e["args"].get("policies", [])
              for k, v in (p.get("levers") or {}).items() if str(k) == str(lever)]
        row["levels_tried"] = ", ".join(f"{v:g}" for v in lv)
        ref = REF.get(r["question_id"], {}).get("level")
        if ref is not None and lv:
            # Committed = exactly one distinct level strictly between 0 and 1 (1.0 alongside it is a reference
            # point, not an answer). Several in-between levels = a bracket: no translation was made.
            mids = sorted({v for v in lv if 0 < v < 1})
            row["reference"] = ref
            row["committed"] = len(mids) == 1
            if len(mids) == 1:
                row["answer_level"] = mids[0]
                row["abs_error"] = round(abs(mids[0] - ref), 3)
            elif mids:
                row["bracket_contains_reference"] = min(mids + [1.0]) <= ref <= max(mids + [1.0])
    return row


def main(model: str = MODEL, qset: str = "pilot"):
    d = RUNS_DIR / model / qset
    rows = [summarise(p) for p in sorted(d.glob("*_r*.json"))]
    df = pd.DataFrame(rows).sort_values(["question", "arm", "rep"])
    df.to_csv(d / "summary.csv", index=False)
    with pd.option_context("display.max_colwidth", 120, "display.width", 250):
        print(df.drop(columns=["tools", "policies"]).to_string(index=False))
        print()
        for _, r in df.iterrows():
            print(f"{r.question} {r.arm} r{r.rep}: {r.tools}\n      {r.policies}")
    cols = [c for c in ["abs_error", "n_runs", "n_info_calls", "steps", "seconds", "info_reply_chars", "cost_usd"] if c in df]
    print("\nby arm:\n", df.groupby("arm")[cols].mean().round(3))
    if "abs_error" in df:
        df["kind"] = df.question.str[-1].map({"i": "input", "o": "output"})
        print("\nabs error of the chosen level, by target kind × arm:\n",
              df.pivot_table(index="kind", columns="arm", values="abs_error", aggfunc="mean").round(3))
        print("\nshare of runs that committed to one level, by target kind × arm:\n",
              df.pivot_table(index="kind", columns="arm", values="committed", aggfunc="mean").round(2))
        print("\nexploratory runs, by target kind × arm:\n",
              df.pivot_table(index="kind", columns="arm", values="n_runs", aggfunc="mean").round(2))
    print("total cost ≈ $%.2f" % df.cost_usd.sum())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else MODEL, sys.argv[2] if len(sys.argv) > 2 else "pilot")
