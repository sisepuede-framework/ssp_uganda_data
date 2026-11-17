"""Why E3 conversations did not reach the answer, by set and arm, including the explicit wording (SX), which
analyze_e3.py's 'Why not reached' sheet leaves out. Reads results_analysis/e3_analysis.xlsx; no API calls.
Run from metamodel/chatbot_deploy: /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/e3_stop_table.py
→ results_analysis/e3_stop_codes.csv (never overwritten). Added 2026-11-17, after the results (descriptive)."""
from pathlib import Path

import pandas as pd

OUT = Path("results_analysis/e3_stop_codes.csv")
if OUT.exists():
    raise SystemExit(f"{OUT} exists")
x = pd.read_excel("results_analysis/e3_analysis.xlsx", sheet_name="Conversations (hand check)")
nr = x[~x.reached]
t = nr.assign(cond=nr.set + " " + nr.arm).pivot_table(index="stop", columns="cond", values="question",
                                                       aggfunc="count", fill_value=0)
t.to_csv(OUT)
print(t.to_string())
