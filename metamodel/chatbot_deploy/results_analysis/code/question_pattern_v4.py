"""
Question by question: what makes the agent reach the variable holding the answer? (EXPLORATORY, 2026-11-16)

Twelve retrieval questions: October's S50, S3, S35, HD1 (Map, Map+) and run v4's R1–R8 (Map, Map+, Map+lever).
Every count is computed from the scored data; the only judgement is SHARE_OF_ASKED (below), stated per question.

Run from metamodel/chatbot_deploy:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/question_pattern_v4.py [OUT.xlsx]
    → results_analysis/question_pattern_v4.xlsx by default; never overwrites an existing file
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # chatbot_deploy/, for backend.*
from backend.rdm.eval.questions import SETS  # noqa: E402

RES = Path("results_analysis")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RES / "question_pattern_v4.xlsx"
OCT = {"S50": "Biogas Recovered from Landfills", "S3": "Area of Improved Land",
       "S35": "Vehicle Distance Traveled from Electricity", "HD1": "Total Electrical Energy Consumption from Transportation"}
# Judgement (Claude, 2026-11-16; to be checked by Alexa): is the lever's own input a share or factor OF the quantity
# the question asks an amount of? Rule: the lever input and the asked quantity name the same thing.
SHARE_OF_ASKED = {
    "S50": (True, "Fraction of landfill gas recovered ↔ how much landfill gas captured"),
    "S3": (True, "No-till crop fraction ↔ hectares using the methods"),
    "R1": (True, "Biogas recovery factor at plants ↔ how much biogas recovered"),
    "R3": (True, "Transmission loss fraction ↔ how much electricity lost"),
    "R6": (True, "Fraction of food lost ↔ how much food lost"),
    "R8": (True, "Fraction of incinerated MSW recovered for energy ↔ how much MSW recovered for energy"),
    "R2": (False, "Share of manure to digesters ↔ biogas (the question itself names the setting)"),
    "S35": (False, "Fuel fractions ↔ kilometres driven"),
    "HD1": (False, "Fuel fractions ↔ electricity used"),
    "R4": (False, "Industrial fuel fractions ↔ electricity used"),
    "R5": (False, "Appliance demand multiplier ↔ electricity used"),
    "R7": (False, "Transport demand multiplier ↔ energy used"),
}
STOP = set("the of to and a in at from for by would how much many if as is it its be on with that what more still than "
           "uganda 2050 possible realistically ambitiously far model allows moved pushed total fraction".split())


def stems(s):
    return {w[:5] for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) >= 3}


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; give another name")
    ref = json.loads(Path("backend/rdm/eval/retrieval_v4_reference.json").read_text())
    qs = {q: (SETS["bank"][q]["question"], node) for q, node in OCT.items()}
    qs.update({q: (r["question"], r["node"]) for q, r in ref.items()})
    octo = pd.read_excel(RES / "reanalysis_v2.xlsx", sheet_name="Retrieval vs answer")
    v4 = pd.read_excel(RES / "run_v4_analysis.xlsx", sheet_name="Held-out (B)")
    rows = []
    for q, (text, node) in qs.items():
        d = octo if q in OCT else v4
        x = d[d.question == q].groupby("arm")[["PROCESS: reached the node", "ANSWER: value inside the key"]].sum()
        share, why = SHARE_OF_ASKED[q]
        row = {"question": q, "text": text, "answer variable": node,
               "answer-variable words in the question": f"{len(stems(text) & stems(node))} of {len(stems(node))}",
               "unit named": bool(re.search(r"hectares|kilomet|tonnes|\bPJ\b", text, re.I)),
               "lever input is a share of the asked quantity": share, "why (judgement)": why}
        for a in ("Map", "Map+", "Map+lever"):
            row[f"{a} reached"] = int(x.loc[a].iloc[0]) if a in x.index else None
            row[f"{a} valid"] = int(x.loc[a].iloc[1]) if a in x.index else None
        rows.append(row)
    t = pd.DataFrame(rows)
    groups = {"share of the asked quantity": t["lever input is a share of the asked quantity"],
              "something else": ~t["lever input is a share of the asked quantity"],
              "something else, without R2": ~t["lever input is a share of the asked quantity"] & (t.question != "R2")}
    pat = []
    for g, m in groups.items():
        r = {"lever input is": g, "questions": " ".join(t[m].question)}
        for a in ("Map", "Map+", "Map+lever"):
            s = t[m][f"{a} reached"].dropna()
            r[f"{a} reached"] = f"{int(s.sum())} of {5 * len(s)}"
        pat.append(r)
    with pd.ExcelWriter(OUT) as xw:
        pd.DataFrame({"note": [__doc__.strip()]}).to_excel(xw, sheet_name="Read me", index=False)
        t.to_excel(xw, sheet_name="By question", index=False)
        pd.DataFrame(pat).to_excel(xw, sheet_name="Pattern", index=False)
    print(pd.DataFrame(pat).to_string(index=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
