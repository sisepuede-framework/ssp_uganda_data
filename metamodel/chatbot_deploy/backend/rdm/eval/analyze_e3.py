"""
Analysis of E3 (docs/run_design_E3_2026-11-17.md), fixed before the run.

    # 1. score each folder (reader = Haiku, as before)
    for d in e3_S e3_SX e3_O e3_G; do
      AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/$d --reader; done
    # 2. python -m backend.rdm.eval.run_manifest && python -m backend.rdm.eval.run_manifest --check
    # 3. python -m backend.rdm.eval.analyze_e3        → results_analysis/e3_analysis.xlsx (never overwritten)

Arms: P = v1 (Map+), H = v3 (calibration hidden), L = v4 (role sentence in the lever's reply), T = v5 (the same
sentence in the tool description).

Outcomes, per conversation (sets S, SX, O)
  reached   the agent opened the variable holding the answer (check 25 not failed)
  valid     a value with the asked unit inside the key (p10–p90 of the lever's top third, 2050; HD1: an increase of
            3–5 PJ or a level of 59–60.5 PJ), found by a text rule; every match is listed for the hand check
  stop      for conversations that did not reach the answer (A4 rules on the opening of the final answer):
            "gave the lever's share" (the lever's top-of-range input value), "said unavailable", or "other"

Primary contrasts (arm labels permuted within question, two-sided, 10,000 permutations; analyze_bank.permutation_p)
  E3a  set S:  H vs P              on reached and valid
  E3b  set S:  L vs P, T vs P      on reached and valid;  L vs T (estimate; powered only for large differences)
  E3c  set S (P, general) vs set SX (P, explicit)   on valid and on "gave the lever's share"
  Guard set G: lever level off the key (T1) for L and T vs P (descriptive, with p)
Secondary: set O (P vs H, descriptive); old vs new targets; results without the second target of a shared lever
(N1 for L52, N6 for L49); network calls; stop codes by arm.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.eval.analyze_v4 import long_table, pair_test
from backend.rdm.eval.questions import E3_SPECS
from backend.rdm.harness.agent import RUNS_DIR

OUT = Path(__file__).parents[3] / "results_analysis" / "e3_analysis.xlsx"
ARM = {"v1": "P", "v3": "H", "v4": "L", "v5": "T"}
SEED = 20261117
REF = json.loads((Path(__file__).parent / "e3_reference.json").read_text())
# the lever's input at the range maximum (what the agent sees at the lever), for the "gave the lever's share" code
TOP = {"S50": 0.55, "S3": 0.5869, "R1": 0.4909, "R3": 0.05546, "R6": 0.02119, "R8": 0.5643, "N1": 0.5643,
       "N2": 0.7427, "N3": 0.02727, "N4": 0.5455, "N5": 0.2832, "N6": 0.3133}
SECOND_OF_LEVER = {"N1", "N6"}
UNIT_RX = {
    "tonne": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
    "PJ": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b",
    "ha": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand)?\s*(?:hectares|ha)\b",
    "vehicle-km": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>billion|million)\s*(?:vehicle[- ]?)?(?:km|kilomet)",
}
SCALE = {"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "billion": 1e9, "": 1}
UNAVAILABLE = re.compile(r"can['’]?t give|cannot give|can['’]?t tell|doesn['’]?t report|does not report|"
                         r"not (?:something|a number|a figure) I can|still (?:can['’]?t|not|doesn['’]?t)|"
                         r"no (?:figure|output|value)|isn['’]?t (?:available|reported)|not available", re.I)


def values(text: str, unit: str) -> list:
    return [float(m.group("n").replace(",", "")) * SCALE[m.group("s") or ""]
            for m in re.finditer(UNIT_RX[unit], text, re.I)]


def is_valid(q: str, vals: list) -> bool:
    if q == "HD1":
        return any(3 <= v <= 5 or 59 <= v <= 60.5 for v in vals)
    k = E3_SPECS[q]["key"]
    return any(k["p10"] <= v <= k["p90"] for v in vals)


def mentions_top(text: str, top: float) -> int:
    pats = {f"{100 * top:.1f}%", f"{100 * top:.0f}%", f"{top:.2f}", f"{top:.3f}", f"{100 * top:.1f} %"}
    hits = [text.find(p) for p in pats if p in text]
    return min(hits) if hits else -1


def conversations(folder: str, wording: str) -> pd.DataFrame:
    d = RUNS_DIR / folder
    fm = pd.read_csv(d / "failure_modes.csv").set_index("file")
    rows = []
    for f, r in fm.iterrows():
        if f.startswith("_infra"):
            continue
        run = json.loads((d / f).read_text())
        q = run["question_id"]
        ans = "\n".join(run.get("answers") or [run.get("final_answer") or ""])
        vals = values(ans, REF[q]["unit"])
        reached = str(r.get("25_required_node_not_visited")) == "False"
        head = (run.get("final_answer") or "")[:400]
        stop = ""
        if not reached:
            pos = mentions_top(head, TOP[q]) if q in TOP else -1
            m = UNAVAILABLE.search(head)
            stop = ("gave the lever's share" if pos >= 0 and (not m or pos < m.start()) else
                    "said unavailable" if m else "other")
        rows.append({"set": folder, "wording": wording, "question": q, "share_type": REF[q]["share_type"],
                     "new": REF[q]["new"], "arm": ARM[run["arm"]], "rep": run["rep"], "log_file": f"{folder}/{f}",
                     "reached": reached, "valid": is_valid(q, vals), "stop": stop,
                     "network calls": r.get("network_calls"),
                     "values found": ", ".join(f"{v:,.4g}" for v in vals[:6]),
                     "answer opening": head, "hand check: valid? y/n": "", "hand check: stop code ok? y/n": ""})
    return pd.DataFrame(rows)


def test(d: pd.DataFrame, col: str, a: str, b: str, rng) -> dict:
    x = pd.DataFrame({"question": d.question, "arm": d.cond, "value": d[col].astype(float)})
    diff, p = pair_test(x, a, b, rng)
    na, nb = (x.arm == a).sum(), (x.arm == b).sum()
    return {f"{a}": f"{int(x[x.arm == a].value.sum())} of {na}", f"{b}": f"{int(x[x.arm == b].value.sum())} of {nb}",
            "difference": diff, "p (permutation within question)": p}


def primary(s: pd.DataFrame, sx: pd.DataFrame, rng) -> pd.DataFrame:
    rows = []
    s = s.assign(cond=s.arm)
    for name, col, a, b in [("E3a cause", "reached", "H", "P"), ("E3a cause", "valid", "H", "P"),
                            ("E3b fix", "reached", "L", "P"), ("E3b fix", "valid", "L", "P"),
                            ("E3b fix", "reached", "T", "P"), ("E3b fix", "valid", "T", "P"),
                            ("E3b placement (estimate)", "reached", "L", "T"),
                            ("E3b placement (estimate)", "valid", "L", "T")]:
        r = test(s, col, a, b, rng)
        rows.append({"experiment": name, "outcome": col, "comparison": f"{a} vs {b}",
                     "first": r[a], "second": r[b], "difference": r["difference"],
                     "p": r["p (permutation within question)"]})
    c = pd.concat([s[s.arm == "P"].assign(cond="general"), sx.assign(cond="explicit")])
    c["gave_share"] = c.stop == "gave the lever's share"
    for col in ("valid", "reached", "gave_share"):
        r = test(c, col, "explicit", "general", rng)
        rows.append({"experiment": "E3c wording", "outcome": col, "comparison": "explicit vs general (P)",
                     "first": r["explicit"], "second": r["general"], "difference": r["difference"],
                     "p": r["p (permutation within question)"]})
    return pd.DataFrame(rows)


def by_question(t: pd.DataFrame) -> pd.DataFrame:
    g = t.groupby(["set", "question", "share_type", "new", "arm"]).agg(
        n=("reached", "size"), reached=("reached", "sum"), valid=("valid", "sum"),
        gave_share=("stop", lambda s: int((s == "gave the lever's share").sum())),
        said_unavailable=("stop", lambda s: int((s == "said unavailable").sum())))
    return g.reset_index()


def secondary(s: pd.DataFrame, o: pd.DataFrame, rng) -> pd.DataFrame:
    rows = []
    for label, d in [("S, old targets", s[~s.new]), ("S, new targets", s[s.new]),
                     ("S, without the second target of a shared lever", s[~s.question.isin(SECOND_OF_LEVER)]),
                     ("O (other-type, descriptive)", o)]:
        d = d.assign(cond=d.arm)
        for a in (["H", "L", "T"] if label.startswith("S") else ["H"]):
            for col in ("reached", "valid"):
                r = test(d, col, a, "P", rng)
                rows.append({"subset": label, "outcome": col, "comparison": f"{a} vs P", "first": r[a],
                             "second": r["P"], "difference": r["difference"],
                             "p": r["p (permutation within question)"]})
    stops = pd.concat([s, o]).query("not reached").pivot_table(index=["set", "stop"], columns="arm",
                                                               values="log_file", aggfunc="count", fill_value=0)
    return pd.DataFrame(rows), stops.reset_index()


def guard(rng) -> pd.DataFrame:
    lt = long_table(RUNS_DIR / "e3_G")
    d = lt[(lt.check == "03_level_off_key") & (lt.kind == "T1")].assign(arm=lambda x: x.arm.map(ARM))
    rows = []
    for a in ("L", "T"):
        x = d.assign(cond=d.arm).rename(columns={})
        r = test(x.assign(value=x.value), "value", a, "P", rng)
        rows.append({"outcome": "lever level off the key (T1)", "comparison": f"{a} vs P", "first": r[a],
                     "second": r["P"], "p": r["p (permutation within question)"]})
    return pd.DataFrame(rows)


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold hand checks); move it before re-running")
    rng = np.random.default_rng(SEED)
    s, sx, o = conversations("e3_S", "general"), conversations("e3_SX", "explicit"), conversations("e3_O", "general")
    prim = primary(s, sx, rng)
    sec, stops = secondary(s, o, rng)
    g = guard(rng)
    allc = pd.concat([s, sx, o])
    with pd.ExcelWriter(OUT) as xw:
        pd.DataFrame({"note": [__doc__.strip()]}).to_excel(xw, sheet_name="Read me", index=False)
        prim.round(4).to_excel(xw, sheet_name="Primary", index=False)
        g.round(4).to_excel(xw, sheet_name="Guard (G)", index=False)
        sec.round(4).to_excel(xw, sheet_name="Secondary", index=False)
        stops.to_excel(xw, sheet_name="Why not reached", index=False)
        by_question(allc).to_excel(xw, sheet_name="By question", index=False)
        allc.to_excel(xw, sheet_name="Conversations (hand check)", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    print(prim.round(4).to_string(index=False), "\n")
    print(g.round(4).to_string(index=False), "\n")
    print(sec.round(4).to_string(index=False), "\n")
    print(stops.to_string(index=False))
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
