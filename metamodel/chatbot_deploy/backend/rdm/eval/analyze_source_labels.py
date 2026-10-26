"""
Source-label test (docs/preregistration_source_labels.md): measures per conversation and the before/after comparison.

    python -m backend.rdm.eval.analyze_source_labels
        → backend/rdm/eval/pilot_runs/source_labels_measures.csv, tests printed

Run `python -m backend.rdm.eval.failure_modes <dir> --reader` on each condition's folder first (P2 reads it).
P1–P5 are pre-registered; E1 was added after the 'before' results and is exploratory.
"""

import csv
import json
import re
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact

from backend.rdm.harness.agent import RUNS_DIR

CONDITIONS = ("before", "after")
P2_STATEMENT = "which part of the economic growth"


def _gdp_values(run: dict) -> list:
    """Every median / p10 / p90 GDP value the agent received from model_network (empty in v0)."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "median" in o:
                out.extend([o.get("median"), *(o.get("p10_p90") or [])])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for c in run["tool_log"]:
        if c["tool"] == "model_network" and c["status"] == "ok" and (c.get("args") or {}).get("node") == "GDP":
            walk(c.get("reply"))
    return [float(x) for x in out if isinstance(x, (int, float))]


def measures(run: dict, reader_row: dict) -> dict:
    answer, calls = run["final_answer"] or "", run["tool_log"]
    ms = reader_row.get("missing_statements") or ""
    x57 = [v for c in calls if c["tool"] == "exploratory_modeling"
           for k, v in ((c.get("args") or {}).get("x_ranges") or {}).items() if str(k) == "57"]
    received = _gdp_values(run)
    stated = [float(m) for m in re.findall(r"(?<![\d.])\d{3}(?:\.\d)?(?![\d.])", answer)]
    return {
        "P1_cites_679": bool(re.search(r"\b679(\.\d)?\b", answer)),
        "P2_places_580_reader": (None if reader_row.get("22_statement_missing") in ("", None)
                                 else P2_STATEMENT not in ms),
        "P3_network_gdp_or_x57": any(c["tool"] == "model_network" and c["status"] == "ok"
                                     and re.search(r"gdp|x57|\b57\b", json.dumps(c.get("args")), re.I) for c in calls),
        "P4_context_gdp": any(c["tool"] == "country_context" and (c.get("args") or {}).get("topic") == "gdp"
                              for c in calls),
        "P5_x57_low_bound_ge_0_6": any(lo >= 0.6 for lo, hi in x57),
        # E1 (exploratory): the answer states a GDP value it received from the runs (within ±2 bn), i.e. the
        # placement of 580 bn is justified by the experiment's numbers, not guessed
        "E1_justified_by_runs": any(abs(s - g) <= 2 for s in stated for g in received),
    }


def table() -> pd.DataFrame:
    rows = []
    for cond in CONDITIONS:
        d = RUNS_DIR / f"source_labels_{cond}"
        if not (d / "failure_modes.csv").exists():
            continue
        reader = {r["file"]: r for r in csv.DictReader(open(d / "failure_modes.csv"))}
        for p in sorted(d.glob("HC1_*_r*.json")):
            if p.name.endswith(".mismatch.json"):
                continue
            run = json.loads(p.read_text())
            rows.append({"condition": cond, "arm": run["arm"], "rep": run["rep"], "file": p.name,
                         **measures(run, reader.get(p.name, {}))})
    return pd.DataFrame(rows)


def _fisher(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna().astype(bool), b.dropna().astype(bool)
    return fisher_exact([[a.sum(), (~a).sum()], [b.sum(), (~b).sum()]])[1]


if __name__ == "__main__":
    t = table()
    out = RUNS_DIR / "source_labels_measures.csv"
    t.to_csv(out, index=False)
    cols = [c for c in t.columns if c[:2] in ("P1", "P2", "P3", "P4", "P5", "E1")]
    print(t.groupby(["condition", "arm"])[cols].agg(lambda s: f"{int(s.dropna().astype(bool).sum())}/{s.notna().sum()}")
          .T.to_string())
    if set(t.condition) == set(CONDITIONS):
        print("\nFisher exact, two-sided, before vs after")
        for c in ("P1_cites_679", "P2_places_580_reader", "E1_justified_by_runs"):
            b, a = t[t.condition == "before"], t[t.condition == "after"]
            per_arm = {arm: round(_fisher(b[b.arm == arm][c], a[a.arm == arm][c]), 3) for arm in ("v0", "v1")}
            print(f"  {c}: pooled p={_fisher(b[c], a[c]):.3f}  per arm {per_arm}")
        print("\nFisher exact, v1 vs v0 within condition")
        for c in ("P2_places_580_reader", "E1_justified_by_runs"):
            for cond in CONDITIONS:
                s = t[t.condition == cond]
                print(f"  {c} [{cond}]: p={_fisher(s[s.arm == 'v1'][c], s[s.arm == 'v0'][c]):.3f}")
    print("saved", out)
