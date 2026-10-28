"""Dump question specs, the reader prompt, the text-rule word lists and per-check counts to JSON for evaluation_rules_doc.py."""
import json, inspect, re
from pathlib import Path
import pandas as pd
from backend.rdm.eval.questions import BANK_SPECS, SETS
from backend.rdm.eval import failure_modes as fm
out = {"specs": {}, "questions": {q: v["question"] for q, v in SETS["bank"].items()}}
for q, s in BANK_SPECS.items():
    out["specs"][q] = json.loads(json.dumps(s, default=str))
src = inspect.getsource(fm._read)
out["prompt_code"] = re.search(r"prompt = \((.*?)\)\n", src, re.S).group(1)
out["regex"] = {"FORECAST": fm.FORECAST.pattern, "NEGATION": fm.NEGATION.pattern, "WINNER": fm.WINNER.pattern,
                "RANGE": fm.RANGE.pattern, "ONE_DIMENSION": fm.ONE_DIMENSION.pattern}
out["harness_numbers"] = sorted(fm._harness_numbers())
def counts(d):
    cnt = {}
    for c in d.columns:
        m = re.match(r"^(?:(\w+):)?(\d\d)_", c)
        if not m: continue
        for arm in ("v0", "v1"):
            x = d[d.arm == arm][c].astype(str)
            a = cnt.setdefault(m.group(2), {}).setdefault(arm, [0, 0])
            a[0] += int(x.isin(["True", "False"]).sum()); a[1] += int((x == "True").sum())
    return cnt


before = Path("backend/rdm/eval/pilot_runs/bank_v3_full/failure_modes_before_review_fixes.csv")
out["counts_before"] = counts(pd.read_csv(before)) if before.exists() else {}
d = pd.read_csv("backend/rdm/eval/pilot_runs/bank_v3_full/failure_modes.csv")
cnt = {}
for c in d.columns:
    m = re.match(r"^(?:(\w+):)?(\d\d)_", c)
    if not m: continue
    num = m.group(2)
    for arm in ("v0", "v1"):
        x = d[d.arm == arm][c].astype(str)
        a = cnt.setdefault(num, {}).setdefault(arm, [0, 0])
        a[0] += int(x.isin(["True", "False"]).sum()); a[1] += int((x == "True").sum())
out["counts"] = cnt
run = json.load(open("backend/rdm/eval/pilot_runs/bank_v3_full/F2_v0_r0.json"))
out["example_prompt"] = fm.transcript(run)
json.dump(out, open(__import__("sys").argv[1], "w"), ensure_ascii=False, indent=1)
print(sorted(cnt), out["harness_numbers"])
