"""
Analysis of run design v4 (docs/run_design_v4_2026-11-16.md, frozen in 498c254), as fixed there.

    # 1. score each folder (the reader is Haiku, as in October)
    AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/bank_v4 --reader
    AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/retrieval_v4 --reader
    AWS_PROFILE=alexa python -m backend.rdm.eval.failure_modes backend/rdm/eval/pilot_runs/bank_v4_drift --reader
    # 2. this script
    python -m backend.rdm.eval.analyze_v4      → results_analysis/run_v4_analysis.xlsx (never overwritten)

Sheets
  Primary RQ3        part A: level off the key (T1) and model_network calls, per group; v2 against October's v0 and
                     v1, pairwise, arm labels permuted within question (analyze_bank.permutation_p)
  Drift (C)          v0 and v1 rerun once now vs October: primary outcomes, and October's spread between repetitions
  Held-out (B)       R1–R8 per conversation: process (reached the answer node, check 25) and answer (value with the
                     right unit inside p10–p90, by text rule), with a column for the hand check of every match
  Held-out summary   per arm, and pairwise permutation tests (v1–v0, v2–v0, v2–v1) for the two primary outcomes
  All checks         every check, per group and arm, for parts A + October and B (secondary; no claim)
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.eval.analyze_bank import CHECK, HYPOTHESIS, permutation_p
from backend.rdm.eval.questions import RETRIEVAL_V4_SPECS
from backend.rdm.harness.agent import RUNS_DIR

OCT, A, B, C = (RUNS_DIR / d for d in ("bank_v3_full", "bank_v4", "retrieval_v4", "bank_v4_drift"))
OUT = Path(__file__).parents[3] / "results_analysis" / "run_v4_analysis.xlsx"
ARM = {"v0": "Map", "v1": "Map+", "v2": "Map+lever"}
SEED = 20261116
UNIT_RX = {   # value with its unit, as in results_analysis/code/reanalysis_v2.py
    "tonne": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>million|thousand|kt|Mt)?\s*(?:tonnes|tons|t)\b",
    "PJ": r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<s>)PJ\b",
}
SCALE = {"million": 1e6, "thousand": 1e3, "kt": 1e3, "Mt": 1e6, "": 1}


def long_table(folder: Path) -> pd.DataFrame:
    """As analyze_bank.long_table, for any folder; files under _infra/ are never scored."""
    t = pd.read_csv(folder / "failure_modes.csv")
    t = t[~t.file.str.startswith("_infra")]
    rows = []
    for _, r in t.iterrows():
        for col, v in r.items():
            m = CHECK.match(col)
            if not m or pd.isna(v):
                continue
            part, check = m.groups()
            qid = part or r["question_id"]
            if part and str(r.get(f"{part}:reached")) == "False":
                continue
            group = "hypothesis" if qid in HYPOTHESIS else r["tag"]
            val = float(v) if check == "network_calls" else float(str(v) == "True")
            rows.append({"question": qid, "group": group, "kind": r["kind"] if not part else "T0",
                         "arm": r["arm"], "rep": r["rep"], "check": check, "value": val})
    return pd.DataFrame(rows)


def pair_test(d: pd.DataFrame, treat: str, ctrl: str, rng) -> tuple:
    """treat − ctrl and its p-value, with arm labels permuted within question (the October function)."""
    d = d[d.arm.isin([treat, ctrl])].assign(arm=lambda x: x.arm.map({treat: "v1", ctrl: "v0"}))
    if d.arm.nunique() < 2:
        return np.nan, np.nan
    return permutation_p(d, rng)


def primary_rq3(lt: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    sel = {"level off the key (T1)": lt[(lt.check == "03_level_off_key") & (lt.kind == "T1")],
           "model_network calls": lt[lt.check == "network_calls"]}
    out = []
    for name, d in sel.items():
        for g in ("dev", "designed", "hypothesis", "blind"):
            dg = d[d.group == g]
            if dg.empty:
                continue
            row = {"outcome": name, "group": g, "questions": dg.question.nunique()}
            for a in ("v0", "v1", "v2"):
                x = dg[dg.arm == a].value
                row[ARM[a]] = x.mean()
                row[f"n {ARM[a]}"] = len(x)
            if g != "blind":   # blind questions: descriptive only, as in October
                for t, c in (("v2", "v0"), ("v2", "v1")):
                    row[f"{ARM[t]} − {ARM[c]}"], row[f"p ({ARM[t]} vs {ARM[c]})"] = pair_test(dg, t, c, rng)
            out.append(row)
    return pd.DataFrame(out)


def drift(oct_lt: pd.DataFrame, c_lt: pd.DataFrame) -> pd.DataFrame:
    out = []
    for name, f in {"level off the key (T1)": lambda d: d[(d.check == "03_level_off_key") & (d.kind == "T1")],
                    "model_network calls": lambda d: d[d.check == "network_calls"],
                    "uncertainty range wrong or missing": lambda d: d[d.check == "05_uncertainty_range_wrong_or_missing"]
                    }.items():
        o, c = f(oct_lt), f(c_lt)
        for a in ("v0", "v1"):
            by_rep = o[o.arm == a].groupby("rep").value.mean()
            out.append({"outcome": name, "arm": ARM[a], "now (rep 0)": c[c.arm == a].value.mean(),
                        "October rep 0": by_rep.get(0, np.nan), "October min over reps": by_rep.min(),
                        "October max over reps": by_rep.max(),
                        "inside October's spread": by_rep.min() - 1e-9 <= c[c.arm == a].value.mean() <= by_rep.max() + 1e-9})
    return pd.DataFrame(out)


def held_out() -> pd.DataFrame:
    fm = pd.read_csv(B / "failure_modes.csv").set_index("file")
    rows = []
    for f, r in fm.iterrows():
        if f.startswith("_infra"):
            continue
        run = json.loads((B / f).read_text())
        spec = RETRIEVAL_V4_SPECS[run["question_id"]]
        key = spec["key"]
        ans = "\n".join(run.get("answers") or [run.get("final_answer") or ""])
        vals = [float(m.group("n").replace(",", "")) * SCALE[m.group("s") or ""]
                for m in re.finditer(UNIT_RX[key["unit"]], ans, re.I)]
        rows.append({"question": run["question_id"], "arm": ARM[run["arm"]], "rep": run["rep"], "log_file": f,
                     "answer key": f"{key['p10']:.4g}–{key['p90']:.4g} {key['unit']}",
                     "PROCESS: reached the node": str(r.get("25_required_node_not_visited")) == "False",
                     "ANSWER: value inside the key": any(key["p10"] <= v <= key["p90"] for v in vals),
                     "ANSWER: gives a range": bool(vals) and bool(re.search(r"p10|\d\s*(?:–|-|to)\s*\d", ans)),
                     "ANSWER: every number traced (check 15)": str(r.get("15_untraced_numbers")) != "True",
                     "values found": ", ".join(f"{v:,.4g}" for v in vals[:6]),
                     "network calls": r.get("network_calls"),
                     "answer (first 600 characters)": ans[:600],
                     "hand check: the matched value is the answer? y/n": ""})
    return pd.DataFrame(rows).sort_values(["question", "arm", "rep"])


def held_out_summary(h: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    inv = {v: k for k, v in ARM.items()}
    out = []
    for col in ("PROCESS: reached the node", "ANSWER: value inside the key", "ANSWER: gives a range",
                "ANSWER: every number traced (check 15)"):
        d = pd.DataFrame({"question": h.question, "arm": h.arm.map(inv), "value": h[col].astype(float)})
        row = {"measure": col, **{ARM[a]: f"{int(d[d.arm == a].value.sum())} of {int((d.arm == a).sum())}"
                                  for a in ("v0", "v1", "v2")}}
        for t, c in (("v1", "v0"), ("v2", "v0"), ("v2", "v1")):
            row[f"p ({ARM[t]} vs {ARM[c]})"] = pair_test(d, t, c, rng)[1]
        out.append(row)
    for a in ("Map", "Map+", "Map+lever"):
        x = h[h.arm == a]
        p, v = x["PROCESS: reached the node"], x["ANSWER: value inside the key"]
        out.append({"measure": f"process × answer, {a}", "Map": "", "Map+": "", "Map+lever": "",
                    "p (Map+ vs Map)": f"reached & valid {int((p & v).sum())}; reached, not valid {int((p & ~v).sum())}; "
                                       f"not reached, valid {int((~p & v).sum())}; neither {int((~p & ~v).sum())}"})
    return pd.DataFrame(out)


def all_checks(lt: pd.DataFrame) -> pd.DataFrame:
    t = lt.assign(arm=lt.arm.map(ARM)).pivot_table(index=["group", "check"], columns="arm", values="value",
                                                     aggfunc="mean")
    return t.reset_index().round(3)


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold hand checks); move it before re-running")
    oct_lt = long_table(OCT)
    a_lt = pd.concat([oct_lt, long_table(A)])
    c_lt = long_table(C)
    h = held_out()
    b_lt = long_table(B)
    sheets = {"Primary RQ3": primary_rq3(a_lt).round(4), "Drift (C)": drift(oct_lt, c_lt).round(3),
              "Held-out (B)": h, "Held-out summary": held_out_summary(h),
              "All checks A": all_checks(a_lt), "All checks B": all_checks(b_lt)}
    with pd.ExcelWriter(OUT) as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 120)
    for name in ("Primary RQ3", "Drift (C)", "Held-out summary"):
        print(f"\n{name}\n", sheets[name].to_string(index=False))
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
