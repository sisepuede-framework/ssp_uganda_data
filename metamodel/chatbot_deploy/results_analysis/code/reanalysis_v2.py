"""
Re-analysis of the 290-conversation run for working paper v2 (2026-11-16). No new conversations, no API calls.

Run from metamodel/chatbot_deploy with the project env:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/reanalysis_v2.py
    → results_analysis/reanalysis_v2.xlsx

Sheets
  Read me               what each sheet is, and what is pre-registered vs exploratory
  Pre-registered        the analysis fixed before the run (docs/question_bank_v3.md, "Run design", commit 7bedda2):
                        per tag, never pooled; arm labels permuted within question (analyze_bank.permutation_p)
  By question           every main check, per question and arm (repetitions are not independent: questions are the
                        sample of tasks)
  Retrieval vs answer   the four questions whose answer is an in-between quantity (S50, S3, S35, HD1): the process
                        (reached the node holding the answer) and the answer (value inside the key, range, year,
                        source, provenance) scored apart. EXPLORATORY: the walk measure was defined on 2026-10-28,
                        after the results were seen (results_analysis/code/walk_depth.py).
  Provenance (28)       every answer flagged by check 15 (a number no tool returned), with a proposed code
                        (Claude, 2026-11-16) and an empty column for Alexa's hand check
  Summaries             counts by arm for the two sheets above, with within-question permutation p-values
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # chatbot_deploy/, for backend.*


from backend.rdm.eval.analyze_bank import permutation_p

RUNS = Path("backend/rdm/eval/pilot_runs/bank_v3_full")
OUT = Path("results_analysis/reanalysis_v2.xlsx")
ARM = {"v0": "Map", "v1": "Map+"}
SEED = 20261116

# ---------------------------------------------------------------- retrieval questions: node and answer key
# node regexes as in walk_depth.py; keys as in questions.py BANK_SPECS (S keys: lever top third, 2050, p10–p90)
RETRIEVAL = {
    "S50": {"node": r"biogas recovered from landfills|gasrecovered_waso_biogas_landfills",
            "unit": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
            "lo": 120_000, "hi": 1_400_000, "key": "120,000–1.4 million t of landfill gas (2050)"},
    "S3": {"node": r"area of improved land|area_lndu_improved_croplands",
           "unit": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand)?\s*(?:hectares|ha)\b",
           "lo": 2_200_000, "hi": 3_100_000, "key": "2.2–3.1 million ha (2050)"},
    "S35": {"node": r"vehicle distance traveled from electric|vehicle_distance_traveled_trns_road_light_electricity",
            "unit": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>billion)\s*(?:vehicle[- ]?)?(?:km|kilomet)",
            "lo": 18, "hi": 28, "key": "18–28 billion vehicle-km (2050)"},
    "HD1": {"node": r"total electrical energy consumption from transportation|energy_consumption_electricity_trns",
            "unit": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b",
            "lo": None, "hi": None, "key": "56.0 → 59.9 PJ, an increase of about 3–5 PJ (2050)"},
}
SCALE = {"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "billion": 1, "": 1, None: 1}
RANGE = re.compile(r"p10|\d\s*(?:–|-|to)\s*\d", re.I)
SOURCE = re.compile(r"model runs|runs of the model|from the runs|not (?:from )?the surrogate|model.network", re.I)


def answer_text(run: dict) -> str:
    return "\n".join(run.get("answers") or [run.get("final_answer") or ""])


def values(text: str, unit_rx: str) -> list:
    out = []
    for m in re.finditer(unit_rx, text, re.I):
        out.append(float(m.group("n").replace(",", "")) * SCALE[m.group("s") or ""])
    return out


# hand corrections of the text rule, each read in the answer (2026-11-16)
NOT_THE_ANSWER = {
    "S3_v0_r4.json": "2.4 million ha is the baseline cereal area, given as an example; the agent says it cannot "
                     "give the no-till hectares",
}


def in_key(q: str, vals: list, text: str, f: str = "") -> bool:
    if f in NOT_THE_ANSWER:
        return False
    k = RETRIEVAL[q]
    if q == "HD1":   # the key is a change: 3–5 PJ, or the level near 60 PJ (same rule as check 19 for HD1)
        return any(3 <= v <= 5 or 59 <= v <= 60.5 for v in vals)
    return any(k["lo"] <= v <= k["hi"] for v in vals)


def retrieval_table(fmt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q, k in RETRIEVAL.items():
        for arm in ("v0", "v1"):
            for rep in range(5):
                f = f"{q}_{arm}_r{rep}.json"
                run = json.loads((RUNS / f).read_text())
                nodes = [str(c["args"].get("node")) for c in run["tool_log"]
                         if c["tool"] == "model_network" and c["status"] == "ok"]
                ans = answer_text(run)
                vals = values(ans, k["unit"])
                rows.append({
                    "question": q, "arm": ARM[arm], "rep": rep, "log_file": f, "answer key": k["key"],
                    "PROCESS: reached the node": any(re.search(k["node"], n, re.I) for n in nodes),
                    "ANSWER: gives a value for the quantity": bool(vals),
                    "ANSWER: value inside the key": in_key(q, vals, ans, f),
                    "ANSWER: gives a range": bool(vals) and bool(RANGE.search(ans)),
                    "ANSWER: says 2050": "2050" in ans,
                    "ANSWER: names the source (runs / network)": bool(SOURCE.search(ans)),
                    "ANSWER: every number traced (check 15)": str(fmt.loc[f, "15_untraced_numbers"]) != "True",
                    "values found": ", ".join(f"{v:,.3g}" for v in vals[:6]),
                    "answer (first 600 characters)": ans[:600],
                    "hand check (Alexa): answer valid? y/n": "",
                })
    t = pd.DataFrame(rows)
    p, a = t["PROCESS: reached the node"], t["ANSWER: value inside the key"]
    t["process × answer"] = np.select([p & a, p & ~a, ~p & a], ["reached, valid", "reached, not valid",
                                                                  "not reached, valid"], "not reached, not valid")
    return t


# ---------------------------------------------------------------- provenance: proposed code per flagged answer
CODES = {
    "A": "Not an agent number: from a tool earlier in the conversation, the user's own words, a count or a proposed "
         "setting (scoring artefact of check 15)",
    "B": "Derived by the agent, inputs shown in the answer, arithmetic correct",
    "C": "Derived by the agent, inputs not shown (unlogged), arithmetic correct",
    "D": "Wrong or unsupported",
}
# (code, reason). Each was checked by recomputing the number from the inputs the answer shows.
PROPOSED = {
    "AG2_v0_r0.json": ("B", "93% = 69 / 74 Mt (livestock / farm total, both stated)"),
    "AG2_v0_r3.json": ("B", "93% = 69 / 74 Mt (both stated)"),
    "AG2_v1_r0.json": ("B", "93% = 69 / 74 Mt (both stated)"),
    "AG2_v1_r3.json": ("B", "93% = 69 / 74 Mt (both stated)"),
    "C4b_v0_r0.json": ("B", "40 ≈ 19.4 + 20.7 Mt; 36% ≈ (9.1 + 5.7) / 40; 34 ≈ 20% × 168 Mt (all stated)"),
    "C4b_v0_r2.json": ("B", "40 ≈ 19.4 + 20.7; 24% ≈ 40 / 168; 83% ≈ 33.6 / 40 (stated)"),
    "C4b_v0_r3.json": ("B", "40 ≈ 19.4 + 20.7; 24% ≈ 40 / 168 (stated)"),
    "C4b_v0_r4.json": ("B", "33 ≈ 20% × 168 Mt; 40 ≈ 19.4 + 20.7 (stated); 40 also = lever number L40"),
    "C4b_v1_r1.json": ("B", "40 ≈ 19.4 + 20.7 of 168 Mt (stated); 40 also = lever number L40"),
    "C4b_v1_r2.json": ("B", "40 ≈ 19.4 + 20.7 of 168 Mt (stated); 40 also = lever number L40"),
    "C4b_v1_r4.json": ("B", "33 ≈ 20% × 168 Mt (stated); 12 = number of waste levers (43–54) and 20 − 8.6 ≈ 12 pp"),
    "H2_v0_r2.json": ("A", "50% restates the user's 'half'; the agent says it cannot confirm the lever meaning"),
    "HA1_v1_r2.json": ("D", "33 = 20.1 / 0.61 is right, but 29–38 bn km does not follow from the stated 15–26 bn km "
                            "at a 0.61 share (that gives about 25–43); the 0.56–0.72 share range rests on it"),
    "HA1_v1_r4.json": ("B", "25–43 bn km = 15–26 / 0.61; 84% ≈ 21 / 25 (stated)"),
    "HD1_v1_r1.json": ("B", "44% = 0.719 / 0.500 − 1 (stated), labelled an approximation; it is not the quantity "
                            "asked (the runs give +3.8 PJ, about +7%, for all transport)"),
    "HD1_v1_r2.json": ("B", "44% = (0.72 − 0.50) / 0.50 (stated) as 'more electric light-duty travel'; not the "
                            "quantity asked (transport electricity in PJ)"),
    "HE1_v1_r3.json": ("B", "17% = (0.72 − 0.60) / 0.72 (stated)"),
    "LV1_v0_r4.json": ("A", "0.33 is a lever level the agent proposes to run, not a result"),
    "Q10b_v0_r3.json": ("A", "6.6 Mt was returned by exploratory_modeling earlier in the conversation (part Q10b)"),
    "Q10b_v0_r4.json": ("A", "3.7% was returned by vulnerability_analysis earlier in the conversation"),
    "Q10b_v1_r0.json": ("A", "3.7% was returned by vulnerability_analysis earlier in the conversation"),
    "Q10b_v1_r2.json": ("A", "3.9% and 6.6 Mt were returned earlier in the conversation"),
    "Q10b_v1_r4.json": ("A", "6.6 Mt was returned earlier in the conversation"),
    "S35_v1_r3.json": ("B", "28% = 1 − 0.72 electric share (stated)"),
    "S3_v0_r3.json": ("B", "7.66 million ha = sum of the five crop areas listed (country_context, base future)"),
    "S3_v1_r2.json": ("B", "crop area × no-till share, each row shown; total 3.69 Mha is outside the key "
                           "(2.2–3.1 Mha) because the areas are the base future's, not the runs'"),
    "S3_v1_r3.json": ("B", "same table; 48% = 3.69 / 7.66; outside the key for the same reason"),
    "S3_v1_r4.json": ("B", "same table; 7,661,598 = the sum of the five areas; outside the key for the same reason"),
}


def provenance_table(fmt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f, r in fmt.iterrows():
        for col in [c for c in fmt.columns if c.endswith("15_untraced_numbers")]:
            if str(r[col]) != "True":
                continue
            part = col.split(":")[0] if ":" in col else r["question_id"]
            run = json.loads((RUNS / f).read_text())
            code, why = PROPOSED[f]
            rows.append({"log_file": f, "question": part, "arm": ARM[r["arm"]], "rep": r["rep"],
                         "untraced numbers": r[col.replace("15_untraced_numbers", "untraced")],
                         "question text": run["question"][:200],
                         "proposed code": code, "code meaning": CODES[code], "reason (recomputed)": why,
                         "hand check (Alexa): agree? y/n": "", "her code if different": ""})
    t = pd.DataFrame(rows)
    assert len(t) == 28 and set(t.log_file) == set(PROPOSED), "the flagged answers changed: re-read them"
    return t


# ---------------------------------------------------------------- tests and summaries
def perm(t: pd.DataFrame, col: str, rng) -> tuple:
    d = pd.DataFrame({"question": t.question, "arm": t.arm.map({"Map": "v0", "Map+": "v1"}),
                      "value": t[col].astype(float)})
    return permutation_p(d, rng)


def summaries(ret: pd.DataFrame, prov: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for col in [c for c in ret.columns if c.startswith(("PROCESS", "ANSWER"))]:
        diff, p = perm(ret, col, rng)
        rows.append({"table": "Retrieval vs answer (4 questions × 5 reps, exploratory)", "measure": col,
                     "Map": f"{int(ret[ret.arm == 'Map'][col].sum())} of 20",
                     "Map+": f"{int(ret[ret.arm == 'Map+'][col].sum())} of 20",
                     "p (permutation within question)": round(p, 3)})
    for k in ("reached, valid", "reached, not valid", "not reached, valid", "not reached, not valid"):
        rows.append({"table": "Retrieval vs answer", "measure": f"process × answer: {k}",
                     "Map": int((ret[ret.arm == "Map"]["process × answer"] == k).sum()),
                     "Map+": int((ret[ret.arm == "Map+"]["process × answer"] == k).sum())})
    for code in CODES:
        rows.append({"table": "Provenance (28 flagged answers, proposed codes)", "measure": f"{code}: {CODES[code]}",
                     "Map": int(((prov.arm == "Map") & (prov["proposed code"] == code)).sum()),
                     "Map+": int(((prov.arm == "Map+") & (prov["proposed code"] == code)).sum())})
    return pd.DataFrame(rows)


def by_question() -> pd.DataFrame:
    lt = pd.read_csv(RUNS / "analysis_long.csv")
    keep = ["03_level_off_key", "02_literal_translation", "network_calls", "08_required_step_skipped",
            "15_untraced_numbers", "22_statement_missing", "25_required_node_not_visited", "07_invented_threshold"]
    lt = lt[lt.check.isin(keep)].assign(arm=lambda d: d.arm.map(ARM))
    t = lt.pivot_table(index=["group", "question", "check"], columns="arm", values="value", aggfunc="mean")
    t["n per arm"] = lt.groupby(["group", "question", "check"]).size() // 2
    return t.reset_index().round(3)


def read_me() -> pd.DataFrame:
    lines = [
        ("Pre-registered", "The analysis fixed before the run (docs/question_bank_v3.md 'Run design', commit 7bedda2, "
                           "2026-10-26 17:37 PDT; first conversation 17:38 PDT). Per tag, never pooled; arm labels "
                           "permuted within question, 10,000 permutations. Primary: level off key (T1), "
                           "model_network calls, uncertainty range (check 5). Source: analysis_primary.csv and "
                           "analysis_checks.csv, unchanged."),
        ("By question", "Share failing (calls: mean) per question and arm. Questions are the sample of tasks; the "
                        "five repetitions show how the agent varies on the same task."),
        ("Retrieval vs answer", "EXPLORATORY. Process (reached the node) and answer (value inside the key, range, "
                                "2050, source, provenance) scored apart. Answer columns are automatic text rules; "
                                "please check the column 'hand check'."),
        ("Provenance (28)", "Every answer flagged by check 15. Proposed codes A–D by Claude after recomputing each "
                            "number; please mark agree / disagree."),
        ("Summaries", "Counts by arm. p-values: within-question permutation (same function as the pre-registered "
                      "analysis), seed 20261116; descriptive, not confirmatory."),
    ]
    return pd.DataFrame(lines, columns=["sheet", "what it is"])


def main():
    fmt = pd.read_csv(RUNS / "failure_modes.csv").set_index("file")
    ret, prov = retrieval_table(fmt), provenance_table(fmt)
    pre = pd.concat([pd.read_csv(RUNS / "analysis_primary.csv").assign(kind="primary"),
                     pd.read_csv(RUNS / "analysis_checks.csv").assign(kind="all checks")]).round(4)
    summ = summaries(ret, prov)
    if OUT.exists():   # the workbook carries Alexa's hand checks: never overwrite it (write a new name instead)
        raise SystemExit(f"{OUT} exists and may hold hand checks; move it or change OUT before re-running")
    with pd.ExcelWriter(OUT) as xw:
        read_me().to_excel(xw, sheet_name="Read me", index=False)
        pre.to_excel(xw, sheet_name="Pre-registered", index=False)
        by_question().to_excel(xw, sheet_name="By question", index=False)
        ret.to_excel(xw, sheet_name="Retrieval vs answer", index=False)
        prov.to_excel(xw, sheet_name="Provenance (28)", index=False)
        summ.to_excel(xw, sheet_name="Summaries", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 90)
    print(summ.to_string(index=False))
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
