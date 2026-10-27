"""
Full bank run, analysis as fixed in docs/question_bank_v3.md ("Run design").

    python -m backend.rdm.eval.analyze_bank      (after failure_modes … bank_v3_full --reader)
        → backend/rdm/eval/pilot_runs/bank_v3_full/analysis_{long,checks,primary}.csv, tables printed

One row per (question or part of a conversation, arm, repetition, check). Groups are reported apart: dev, designed,
hypothesis (HA1–HE1) and blind (descriptive only, no test). The arm difference (v1 − v0) is tested with a permutation
test that shuffles v0 / v1 within each question (10,000 permutations, two-sided).
"""

import re

import numpy as np
import pandas as pd

from backend.rdm.harness.agent import RUNS_DIR

D = RUNS_DIR / "bank_v3_full"
HYPOTHESIS = {"HA1", "HB1", "HC1", "HD1", "HE1"}
GROUPS = ("dev", "designed", "hypothesis", "blind")
CHECK = re.compile(r"^(?:(\w+):)?(\d\d_\w+|network_calls)$")
N_PERM, SEED = 10_000, 20261026


def long_table() -> pd.DataFrame:
    t = pd.read_csv(D / "failure_modes.csv")
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


def permutation_p(d: pd.DataFrame, rng) -> tuple:
    """v1 − v0 mean, and its two-sided p-value with arm labels shuffled within each question."""
    obs = d[d.arm == "v1"].value.mean() - d[d.arm == "v0"].value.mean()
    vals, is_v1, qs = d.value.to_numpy(), (d.arm == "v1").to_numpy(), d.question.to_numpy()
    blocks = [np.flatnonzero(qs == q) for q in np.unique(qs)]
    n1, n0 = is_v1.sum(), (~is_v1).sum()
    if not n1 or not n0:
        return obs, np.nan
    hits = 0
    for _ in range(N_PERM):
        lab = is_v1.copy()
        for b in blocks:
            lab[b] = rng.permutation(lab[b])
        diff = vals[lab].mean() - vals[~lab].mean()
        hits += abs(diff) >= abs(obs) - 1e-12
    return obs, (hits + 1) / (N_PERM + 1)


def summarize(lt: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    out = []
    for (g, c), d in lt.groupby(["group", "check"]):
        row = {"group": g, "check": c, "questions": d.question.nunique(),
               "n_v0": int((d.arm == "v0").sum()), "n_v1": int((d.arm == "v1").sum()),
               "v0": d[d.arm == "v0"].value.mean(), "v1": d[d.arm == "v1"].value.mean()}
        if g != "blind":
            row["diff"], row["p"] = permutation_p(d, rng)
        out.append(row)
    return pd.DataFrame(out)


def primary(lt: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    sel = {"1 · level off the key (T1)": lt[(lt.check == "03_level_off_key") & (lt.kind == "T1")],
           "2 · model_network calls": lt[lt.check == "network_calls"],
           "3 · uncertainty range wrong or missing": lt[lt.check == "05_uncertainty_range_wrong_or_missing"]}
    out = []
    for name, d in sel.items():
        for g in GROUPS:
            dg = d[d.group == g]
            if dg.empty:
                continue
            row = {"outcome": name, "group": g, "questions": dg.question.nunique(),
                   "n": len(dg), "v0": dg[dg.arm == "v0"].value.mean(), "v1": dg[dg.arm == "v1"].value.mean()}
            if g != "blind":
                row["diff"], row["p"] = permutation_p(dg, rng)
            out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    lt = long_table()
    lt.to_csv(D / "analysis_long.csv", index=False)
    pr = primary(lt)
    pr.to_csv(D / "analysis_primary.csv", index=False)
    sm = summarize(lt)
    sm.to_csv(D / "analysis_checks.csv", index=False)
    pd.set_option("display.width", 200)
    print("PRIMARY (RQ2)\n", pr.round(3).to_string(index=False))
    print("\nALL CHECKS (share failing; network_calls = mean calls)\n", sm.round(3).to_string(index=False))
