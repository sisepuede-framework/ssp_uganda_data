"""
Analysis of E4 (docs/run_design_E4_2026-11-17.md), fixed before the run. Same outcomes and test as E3
(analyze_e3.py); the arms are a 2×2 of two changes to Map+ plus calibration hidden, all run together.

    # 1. score each folder (reader = Haiku, as before)
    for d in e4_S e4_O e4_G; do
      AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/$d --reader; done
    # 2. python -m backend.rdm.eval.run_manifest && python -m backend.rdm.eval.run_manifest --check
    # 3. python -m backend.rdm.eval.analyze_e4        → results_analysis/e4_analysis.xlsx (never overwritten)

Arms (tools/network.py)
                              calibration in the lever's reply    calibration on request (meaning=true)
  no stated target            P  v1 (Map+, control)               R  v7
  looking_for in every call   F  v8                               C  v6
  and H v3: calibration hidden, not available at all (as E3).

Outcomes per conversation: reached, valid, stop (as E3); whether and when the agent asked for a lever's meaning (R, C);
the looking_for it first wrote and whether it names a unit (F, C).

Primary, set S (12 share-type questions × 10), outcome valid (reached reported alongside). Arm labels permuted within
question, two-sided, 10,000 permutations; Holm adjustment over the six contrasts (conclusions use the adjusted p):
  1  R vs P   calibration on request, no target
  2  C vs F   calibration on request, with target
  3  F vs P   target, calibration shown
  4  C vs R   target, calibration on request
  5  C vs P   the whole design
  6  R vs H   what having the calibration on request costs against not having it
  Interaction (C − R) − (F − P): estimate only.
Translation guard, set G (15 T1 × 3): lever level off the key (no policy run counts as off the key, as in E1–E3),
  H, R, F, C vs P (with p, unadjusted); plus how many conversations ran no policy.
Secondary: set O (8 other-type × 3) the same contrasts; S old vs new targets; S without N1, N6; stop codes by arm;
meaning use; in G, off the key by whether the agent asked for the meaning.
Historical (counts only, run separately): E3's arms on set S next to E4's.
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
a3.ARM.update(v6="C", v7="R", v8="F")      # a3.conversations maps arm codes with this dict
CONTRASTS = [("R", "P", "calibration on request, no target"), ("C", "F", "calibration on request, with target"),
             ("F", "P", "target, calibration shown"), ("C", "R", "target, calibration on request"),
             ("C", "P", "the whole design"), ("R", "H", "on request vs not available")]
UNIT_WORD = re.compile(r"tonne|\bt\b|\bMt\b|\bkt\b|\bPJ\b|hectare|\bha\b|km|kilomet|\bm3\b|m³|TWh|GWh|litre|head",
                       re.I)


def holm(ps: list) -> list:
    order = np.argsort(ps)
    adj, running = [np.nan] * len(ps), 0.0
    for k, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = running
    return adj


def meaning_use(log_file: str) -> dict:
    run = json.loads((RUNS_DIR / log_file).read_text())
    calls = [c for c in run["tool_log"] if c["tool"] == "model_network"]
    args = [c.get("args") or {} for c in calls]
    asked = [i for i, a in enumerate(args) if a.get("meaning")]
    walk = [i for i, a in enumerate(args) if not a.get("meaning") and not str(a.get("node", "")).upper().startswith("L")]
    first_lf = next((a.get("looking_for") for a in args if a.get("looking_for")), "") or ""
    return {"asked meaning": len(asked), "asked before walking": bool(asked) and (not walk or asked[0] < walk[0]),
            "first looking_for": first_lf, "looking_for names a unit": bool(UNIT_WORD.search(first_lf))}


def with_meaning(t: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([t.reset_index(drop=True), pd.DataFrame([meaning_use(f) for f in t.log_file])], axis=1)


def contrasts(d: pd.DataFrame, label: str, rng, adjust: bool) -> pd.DataFrame:
    d = d.assign(cond=d.arm)
    rows = []
    for col in ("valid", "reached"):
        block = []
        for a, b, what in CONTRASTS:
            r = a3.test(d, col, a, b, rng)
            block.append({"set": label, "outcome": col, "comparison": f"{a} vs {b}", "what it isolates": what,
                          "first": r[a], "second": r[b], "difference": r["difference"],
                          "p": r["p (permutation within question)"]})
        if adjust:
            for row, q in zip(block, holm([x["p"] for x in block])):
                row["p Holm (6 contrasts)"] = q
        rate = {a: d[d.arm == a][col].mean() for a in "PRFC"}
        block.append({"set": label, "outcome": col, "comparison": "(C − R) − (F − P)",
                      "what it isolates": "interaction: does the target help more when the calibration is shown?",
                      "difference": (rate["C"] - rate["R"]) - (rate["F"] - rate["P"])})
        rows += block
    return pd.DataFrame(rows)


def guard(rng) -> tuple:
    lt = long_table(RUNS_DIR / "e4_G")
    d = lt[(lt.check == "03_level_off_key") & (lt.kind == "T1")].assign(arm=lambda x: x.arm.map(a3.ARM))
    d = d.assign(cond=d.arm)
    rows = []
    for a in ("H", "R", "F", "C"):
        r = a3.test(d, "value", a, "P", rng)
        rows.append({"set": "G", "outcome": "lever level off the key (T1)", "comparison": f"{a} vs P", "first": r[a],
                     "second": r["P"], "difference": r["difference"], "p": r["p (permutation within question)"]})
    fm = pd.read_csv(RUNS_DIR / "e4_G" / "failure_modes.csv")
    fm = fm[~fm.file.str.startswith("_infra")].assign(arm=lambda x: x.arm.map(a3.ARM))
    if "level_set" in fm:
        for a, g in fm.groupby("arm"):
            rows.append({"set": "G", "outcome": "ran no policy", "comparison": a,
                         "first": f"{int(g.level_set.isna().sum())} of {len(g)}"})
    m = pd.DataFrame([{"file": f, "arm": a, **meaning_use(f"e4_G/{f}")} for f, a in zip(fm.file, fm.arm)])
    off = d.assign(file=lambda x: x.question + "_" + x.arm.map({v: k for k, v in a3.ARM.items()}) + "_r" +
                   x.rep.astype(str) + ".json")[["file", "value"]].rename(columns={"value": "off key"})
    m = m.merge(off, on="file", how="left")
    return pd.DataFrame(rows), m


def historical(s: pd.DataFrame) -> pd.DataFrame:
    """Counts only: E4 next to E3 (run separately; no test)."""
    e3 = pd.read_excel(OUT.parent / "e3_analysis.xlsx", sheet_name="Conversations (hand check)")
    parts = [(f"E4 {a}", s[s.arm == a]) for a in ("P", "H", "R", "F", "C")] + \
            [(f"E3 {a}", e3[(e3.set == "e3_S") & (e3.arm == a)]) for a in ("P", "H", "L", "T")] + \
            [("E3 SX (P, explicit)", e3[e3.set == "e3_SX"])]
    return pd.DataFrame([{"arm": n, "n": len(d), "reached": int(d.reached.sum()), "valid": int(d.valid.sum()),
                          "gave the lever's share": int((d.stop == "gave the lever's share").sum()),
                          "said unavailable": int((d.stop == "said unavailable").sum())} for n, d in parts])


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold hand checks); move it before re-running")
    rng = np.random.default_rng(SEED)
    s, o = with_meaning(a3.conversations("e4_S", "general")), with_meaning(a3.conversations("e4_O", "general"))
    prim = contrasts(s, "S", rng, adjust=True)
    g, gm = guard(rng)
    sec = pd.concat([contrasts(o, "O", rng, adjust=False)] +
                    [contrasts(d, lab, rng, adjust=False) for lab, d in
                     [("S, old targets", s[~s.new]), ("S, new targets", s[s.new]),
                      ("S, without N1 and N6", s[~s.question.isin(a3.SECOND_OF_LEVER)])]])
    allc = pd.concat([s, o])
    stops = allc.query("not reached").pivot_table(index=["set", "stop"], columns="arm", values="log_file",
                                                  aggfunc="count", fill_value=0).reset_index()
    hist = historical(s)
    use = allc[allc.arm.isin(["R", "F", "C"])].groupby(["set", "arm"]).agg(
        n=("log_file", "size"), asked_meaning=("asked meaning", lambda x: int((x > 0).sum())),
        asked_before_walking=("asked before walking", "sum"),
        looking_for_names_unit=("looking_for names a unit", "sum")).reset_index()
    with pd.ExcelWriter(OUT) as xw:
        pd.DataFrame({"note": [__doc__.strip()]}).to_excel(xw, sheet_name="Read me", index=False)
        prim.round(4).to_excel(xw, sheet_name="Primary (S)", index=False)
        g.round(4).to_excel(xw, sheet_name="Guard (G)", index=False)
        sec.round(4).to_excel(xw, sheet_name="Secondary", index=False)
        stops.to_excel(xw, sheet_name="Why not reached", index=False)
        hist.to_excel(xw, sheet_name="Historical (E3, no test)", index=False)
        use.to_excel(xw, sheet_name="Meaning and target use", index=False)
        gm.to_excel(xw, sheet_name="Guard G, per conversation", index=False)
        a3.by_question(allc).to_excel(xw, sheet_name="By question", index=False)
        allc.to_excel(xw, sheet_name="Conversations (hand check)", index=False)
    pd.set_option("display.width", 240, "display.max_colwidth", 50)
    for t in (prim, g, stops, hist, use):
        print(t.round(4).to_string(index=False), "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
