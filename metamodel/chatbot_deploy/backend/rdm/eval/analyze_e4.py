"""
Analysis of E4 (docs/run_design_E4_2026-11-17.md), fixed before the run. Same outcomes and test as E3
(analyze_e3.py); only the arms differ.

    # 1. score each folder (reader = Haiku, as before)
    for d in e4_S e4_O e4_G; do
      AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/$d --reader; done
    # 2. python -m backend.rdm.eval.run_manifest && python -m backend.rdm.eval.run_manifest --check
    # 3. python -m backend.rdm.eval.analyze_e4        → results_analysis/e4_analysis.xlsx (never overwritten)

Arms: P = v1 (Map+, control, run again alongside C), C = v6 (calibration on request: no input values in a lever's
reply, model_network(lever, meaning=true) returns them; every model_network call states looking_for).

Outcomes per conversation: reached, valid, stop (as E3); plus, for C, whether and when the agent asked for a lever's
meaning, and the looking_for it first wrote.

Primary (arm labels permuted within question, two-sided, 10,000 permutations)
  E4a  retrieval, set S (12 share-type × 5):  C vs P  on valid and reached
  E4b  translation, set G (15 T1 × 3):        C vs P  on lever level off the key (T1 check 03)
Secondary
  set O (8 other-type × 3): C vs P on reached and valid; S old vs new targets; S without N1, N6; stop codes by arm;
  meaning use (share of conversations that asked; asked before the first walk step); in G, off-key by whether the
  agent asked for the meaning.
Historical (descriptive, no p: run separately): C against E3's H, L, T and SX on set S; E4's P against E3's P (drift).
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.eval import analyze_e3 as a3
from backend.rdm.eval.analyze_v4 import long_table
from backend.rdm.harness.agent import RUNS_DIR

OUT = Path(__file__).parents[3] / "results_analysis" / "e4_analysis.xlsx"
SEED = 20261118
a3.ARM.update(v6="C")       # a3.conversations maps arm codes with this dict
UNIT_WORD = re.compile(r"tonne|\bt\b|\bMt\b|\bkt\b|\bPJ\b|hectare|\bha\b|km|kilomet|\bm3\b|m³|TWh|GWh|litre|head",
                       re.I)


def meaning_use(log_file: str) -> dict:
    run = json.loads((RUNS_DIR / log_file).read_text())
    calls = [c for c in run["tool_log"] if c["tool"] == "model_network"]
    asked = [i for i, c in enumerate(calls) if (c.get("args") or {}).get("meaning")]
    walk = [i for i, c in enumerate(calls) if not (c.get("args") or {}).get("meaning")
            and not str((c.get("args") or {}).get("node", "")).upper().startswith("L")]
    first_lf = next((c["args"].get("looking_for") for c in calls if (c.get("args") or {}).get("looking_for")), "")
    return {"asked meaning": len(asked),
            "asked before walking": bool(asked) and (not walk or asked[0] < walk[0]),
            "first looking_for": first_lf, "looking_for names a unit": bool(UNIT_WORD.search(first_lf or ""))}


def with_meaning(t: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([t.reset_index(drop=True), pd.DataFrame([meaning_use(f) for f in t.log_file])], axis=1)


def primary(s: pd.DataFrame, rng) -> pd.DataFrame:
    s = s.assign(cond=s.arm)
    rows = []
    for col in ("valid", "reached"):
        r = a3.test(s, col, "C", "P", rng)
        rows.append({"experiment": "E4a retrieval (S)", "outcome": col, "comparison": "C vs P", "first": r["C"],
                     "second": r["P"], "difference": r["difference"], "p": r["p (permutation within question)"]})
    return pd.DataFrame(rows)


def guard(rng) -> tuple:
    lt = long_table(RUNS_DIR / "e4_G")
    d = lt[(lt.check == "03_level_off_key") & (lt.kind == "T1")].assign(arm=lambda x: x.arm.map(a3.ARM))
    r = a3.test(d.assign(cond=d.arm), "value", "C", "P", rng)
    g = pd.DataFrame([{"experiment": "E4b translation (G)", "outcome": "lever level off the key (T1)",
                       "comparison": "C vs P", "first": r["C"], "second": r["P"], "difference": r["difference"],
                       "p": r["p (permutation within question)"]}])
    fm = pd.read_csv(RUNS_DIR / "e4_G" / "failure_modes.csv")
    fm = fm[~fm.file.str.startswith("_infra") & (fm.arm == "v6")]
    m = pd.DataFrame([{"file": f, **meaning_use(f"e4_G/{f}")} for f in fm.file])
    off = d[d.arm == "C"].assign(file=lambda x: x.question + "_v6_r" + x.rep.astype(str) + ".json")
    m = m.merge(off[["file", "value"]].rename(columns={"value": "off key"}), on="file", how="left")
    return g, m


def secondary(s: pd.DataFrame, o: pd.DataFrame, rng) -> tuple:
    rows = []
    for label, d in [("S, old targets", s[~s.new]), ("S, new targets", s[s.new]),
                     ("S, without the second target of a shared lever", s[~s.question.isin(a3.SECOND_OF_LEVER)]),
                     ("O (other-type)", o)]:
        d = d.assign(cond=d.arm)
        for col in ("reached", "valid"):
            r = a3.test(d, col, "C", "P", rng)
            rows.append({"subset": label, "outcome": col, "comparison": "C vs P", "first": r["C"], "second": r["P"],
                         "difference": r["difference"], "p": r["p (permutation within question)"]})
    stops = pd.concat([s, o]).query("not reached").pivot_table(index=["set", "stop"], columns="arm",
                                                               values="log_file", aggfunc="count", fill_value=0)
    return pd.DataFrame(rows), stops.reset_index()


def historical(s: pd.DataFrame) -> pd.DataFrame:
    """Counts only: E4 against E3 (run separately; no test)."""
    e3 = pd.read_excel(OUT.parent / "e3_analysis.xlsx", sheet_name="Conversations (hand check)")
    rows = []
    for name, d in [("E4 C", s[s.arm == "C"]), ("E4 P", s[s.arm == "P"])] + \
                   [(f"E3 {a}", e3[(e3.set == "e3_S") & (e3.arm == a)]) for a in ("P", "H", "L", "T")] + \
                   [("E3 SX (P, explicit)", e3[e3.set == "e3_SX"])]:
        rows.append({"arm": name, "n": len(d), "reached": int(d.reached.sum()), "valid": int(d.valid.sum()),
                     "gave the lever's share": int((d.stop == "gave the lever's share").sum()),
                     "said unavailable": int((d.stop == "said unavailable").sum())})
    return pd.DataFrame(rows)


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold hand checks); move it before re-running")
    rng = np.random.default_rng(SEED)
    s, o = with_meaning(a3.conversations("e4_S", "general")), with_meaning(a3.conversations("e4_O", "general"))
    prim = primary(s, rng)
    g, gm = guard(rng)
    sec, stops = secondary(s, o, rng)
    hist = historical(s)
    allc = pd.concat([s, o])
    use = allc[allc.arm == "C"].groupby("set").agg(
        n=("log_file", "size"), asked_meaning=("asked meaning", lambda x: int((x > 0).sum())),
        asked_before_walking=("asked before walking", "sum"),
        looking_for_names_unit=("looking_for names a unit", "sum")).reset_index()
    with pd.ExcelWriter(OUT) as xw:
        pd.DataFrame({"note": [__doc__.strip()]}).to_excel(xw, sheet_name="Read me", index=False)
        pd.concat([prim, g]).round(4).to_excel(xw, sheet_name="Primary", index=False)
        sec.round(4).to_excel(xw, sheet_name="Secondary", index=False)
        stops.to_excel(xw, sheet_name="Why not reached", index=False)
        hist.to_excel(xw, sheet_name="Historical (E3, no test)", index=False)
        use.to_excel(xw, sheet_name="Meaning use (C)", index=False)
        gm.to_excel(xw, sheet_name="Guard G, C conversations", index=False)
        a3.by_question(allc).to_excel(xw, sheet_name="By question", index=False)
        allc.to_excel(xw, sheet_name="Conversations (hand check)", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    for t in (prim, g, sec, stops, hist, use):
        print(t.round(4).to_string(index=False), "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
