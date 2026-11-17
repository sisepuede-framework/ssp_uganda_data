"""
Why did the agent not reach the variable holding the answer? (run v4, part B, R1–R8). EXPLORATORY: defined on
2026-11-16 after reading the results. No API calls.

Run from metamodel/chatbot_deploy:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/stop_coding_v4.py
    → results_analysis/run_v4_stop_coding.xlsx (never overwritten)

Codes, applied to the opening of the final answer (first 400 characters), for each conversation that did not reach
the answer node (check 25):
  nearby quantity   the opening gives the lever's own input at the range maximum as the answer (e.g. "about 5.5% of
                    electricity would still be lost"); the value is the model's (it is the lever's top-of-range input)
  said unavailable  the opening says the tools or the model cannot give the quantity
  other             neither (read by hand)
If both appear, "nearby quantity" wins when the input value comes first. Every code has a column for the hand check.

Scoring of R3, R6, R8 (decision 2026-11-16): the pre-registered strict score (value inside the key, in the asked
unit) stays primary. "Nearby quantity" is reported beside it as exploratory, and named a wording problem of those
questions: "how much ... would still be lost / be recovered" can be read as a share.
"""
import json
import re
from pathlib import Path

import pandas as pd

RUNS = Path("backend/rdm/eval/pilot_runs/retrieval_v4")
OUT = Path("results_analysis/run_v4_stop_coding.xlsx")
ARM = {"v0": "Map", "v1": "Map+", "v2": "Map+lever"}
# the lever's input at the range maximum, 2050 (model_network input_values), for levers with one value
TOP = {"R1": 0.4909, "R3": 0.05546, "R5": 0.5448, "R6": 0.02119, "R7": 0.7905, "R8": 0.5643}
SHARE_READING = {"R3", "R6", "R8"}           # questions a share can fairly answer (wording problem)
UNAVAILABLE = re.compile(r"can['’]?t give|cannot give|can['’]?t tell|doesn['’]?t report|does not report|"
                         r"not (?:something|a number|a figure) I can|still (?:can['’]?t|not|doesn['’]?t)|"
                         r"no (?:figure|output|value)|isn['’]?t (?:available|reported)|not available", re.I)


def mentions_top(text: str, top: float) -> int:
    """Position of the top-of-range value written as a percent or a fraction, or -1."""
    pats = {f"{100 * top:.1f}%", f"{100 * top:.0f}%", f"{top:.2f}", f"{top:.3f}", f"{100 * top:.1f} %"}
    hits = [text.find(p) for p in pats if p in text]
    return min(hits) if hits else -1


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold hand checks); move it before re-running")
    fm = pd.read_csv(RUNS / "failure_modes.csv").set_index("file")
    rows = []
    for f, r in fm.iterrows():
        if f.startswith("_infra") or str(r["25_required_node_not_visited"]) != "True":
            continue
        run = json.loads((RUNS / f).read_text())
        q = run["question_id"]
        head = (run["final_answer"] or "")[:400]
        pos = mentions_top(head, TOP[q]) if q in TOP else -1
        m = UNAVAILABLE.search(head)
        code = ("nearby quantity" if pos >= 0 and (not m or pos < m.start()) else
                "said unavailable" if m else "other")
        walk = [str(c["args"].get("node")) for c in run["tool_log"] if c["tool"] == "model_network"]
        rows.append({"question": q, "arm": ARM[run["arm"]], "rep": run["rep"], "log_file": f,
                     "share is a fair reading": q in SHARE_READING, "proposed code": code,
                     "network walk": " → ".join(walk), "answer opening": head,
                     "hand check (agree? y/n)": "", "your code if different": ""})
    t = pd.DataFrame(rows).sort_values(["question", "arm", "rep"])
    summ = t.pivot_table(index="proposed code", columns="arm", values="log_file", aggfunc="count", fill_value=0)
    by_q = t.pivot_table(index=["question", "proposed code"], columns="arm", values="log_file", aggfunc="count",
                         fill_value=0)
    with pd.ExcelWriter(OUT) as xw:
        t.to_excel(xw, sheet_name="Not reached (coded)", index=False)
        summ.reset_index().to_excel(xw, sheet_name="Summary", index=False)
        by_q.reset_index().to_excel(xw, sheet_name="By question", index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 150)
    print(summ, "\n")
    print(by_q, "\n")
    for _, x in t.iterrows():
        print(f"{x.question} {x.arm:9s} r{x.rep} {x['proposed code']:16s} | {x['answer opening'][:150]!r}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
