"""Network values: the 4,989-run sample the agent read vs all the runs. Writes results_analysis/sample_vs_100k.xlsx.

    PYTHONPATH=. python results_analysis/code/sample_vs_100k.py
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

from backend.rdm.network.ranges import OUT
from backend.rdm.runs import get_run

XLSX = "results_analysis/sample_vs_100k.xlsx"
if os.path.exists(XLSX):
    sys.exit(f"{XLSX} exists: reviewed files are never overwritten")
run = get_run()
full_dir = run.cache_dir / "full_100k"
KEY = ["year", "lever_id", "x_id", "x_bin", "lever_level", "field"]
sam = pd.read_parquet(OUT / f"{run.name}_ranges.parquet")
for c in ("x_bin", "lever_level", "field"):
    sam[c] = sam[c].astype(str)
full = pd.concat([pd.read_parquet(full_dir / f"full_ranges_{y}.parquet") for y in run.years])
m = sam.merge(full, on=KEY, suffixes=("_s", "_f"), how="left", validate="1:1")
print("cells", len(m), "no full value", int(m.median_f.isna().sum()))
m = m.dropna(subset=["median_f", "median_s"])
spread = (m.p90_f - m.p10_f)
m["moves"] = spread > 1e-9 * (1 + m.median_f.abs())         # a field that varies at all in this cell
m["d_median_spread"] = np.where(m.moves, (m.median_s - m.median_f).abs() / spread.where(spread > 0), np.nan)
m["d_p10_spread"] = np.where(m.moves, (m.p10_s - m.p10_f).abs() / spread.where(spread > 0), np.nan)
m["d_p90_spread"] = np.where(m.moves, (m.p90_s - m.p90_f).abs() / spread.where(spread > 0), np.nan)
m["pct_median"] = np.where(m.median_f.abs() > 0, (m.median_s - m.median_f).abs() / m.median_f.abs() * 100, np.nan)


def row(label, d):
    v = d[d.moves]
    return {"Cells": label, "Number of cells": len(d), "Varying": len(v), "Runs per cell, sample (min)": int(d.n_s.min()),
            "Median difference, % of the value: median": v.pct_median.median(), "95th pct": v.pct_median.quantile(.95),
            "Median difference, share of the p10-p90 spread: median": v.d_median_spread.median(),
            "95th pct ": v.d_median_spread.quantile(.95), "99th pct": v.d_median_spread.quantile(.99),
            "Share within 5% of spread": (v.d_median_spread < .05).mean(), "Share within 10% of spread": (v.d_median_spread < .10).mean(),
            "p10: 95th pct": v.d_p10_spread.quantile(.95), "p90: 95th pct": v.d_p90_spread.quantile(.95)}


any_ = m[(m.x_id == 0)]
summary = pd.DataFrame([row("All cells", m), row("No uncertainty filter", any_),
                        row("No filter, a lever's third", any_[any_.lever_id > 0]),
                        row("With an uncertainty filter", m[m.x_id > 0])])

# lever effect: what the agent reads across low -> high
e = any_[any_.lever_id > 0].pivot_table(index=["year", "lever_id", "field"], columns="lever_level", values=["median_s", "median_f", "p10_f", "p90_f"], observed=True)
eff = pd.DataFrame({"s": e[("median_s", "high")] - e[("median_s", "low")], "f": e[("median_f", "high")] - e[("median_f", "low")],
                    "spread": e[("p90_f", "low")] - e[("p10_f", "low")]}).dropna().reset_index()
eff = eff[eff.spread > 0]
eff["size"] = eff.f.abs() / eff.spread
eff["same_sign"] = np.sign(eff.s) == np.sign(eff.f)
bins = [(0, .01, "under 1% of spread"), (.01, .05, "1-5%"), (.05, .2, "5-20%"), (.2, 1e12, "over 20%")]
rows = []
for lo, hi, lab in bins:
    g = eff[(eff["size"] >= lo) & (eff["size"] < hi)]
    rows.append({"Size of the lever's effect (all runs)": lab, "Lever-field pairs": len(g), "Same direction in the sample": g.same_sign.mean(),
                 "Median error in the effect, % of the effect": ((g.s - g.f).abs() / g.f.abs().replace(0, np.nan)).median() * 100})
effects = pd.DataFrame(rows)

# numbers used in the talk and in the answer keys
get = lambda f, l, x, xb, lb, y=2050: m[(m.year == y) & (m.field == f) & (m.lever_id == l) & (m.x_id == x) & (m.x_bin == xb) & (m.lever_level == lb)].iloc[0]
items = [("Slide 19: diesel km, cars and vans (bn), lever low", "vehicle_distance_traveled_trns_road_light_diesel", 35, 0, "any", "low", 1e-9),
         ("Slide 19: diesel km, cars and vans (bn), lever high", "vehicle_distance_traveled_trns_road_light_diesel", 35, 0, "any", "high", 1e-9),
         ("Slide 19: CO2, cars and vans (Mt), lever low", "emission_co2e_co2_trns_road_light", 35, 0, "any", "low", 1),
         ("Slide 19: CO2, cars and vans (Mt), lever high", "emission_co2e_co2_trns_road_light", 35, 0, "any", "high", 1),
         ("Slide 19: all transport (Mt), lever low", "emissions_transportation", 35, 0, "any", "low", 1),
         ("Slide 19: all transport (Mt), lever high", "emissions_transportation", 35, 0, "any", "high", 1),
         ("Early-stop quote and HD1 key: transport electricity (PJ), low", "energy_consumption_electricity_trns_total", 35, 0, "any", "low", 1),
         ("Early-stop quote and HD1 key: transport electricity (PJ), high", "energy_consumption_electricity_trns_total", 35, 0, "any", "high", 1),
         ("HC1 key: GDP, X57 low", "gdp_mmm_usd", 0, 57, "low", "all", 1),
         ("HC1 key: GDP, X57 mid", "gdp_mmm_usd", 0, 57, "mid", "all", 1),
         ("HC1 key: GDP, X57 high", "gdp_mmm_usd", 0, 57, "high", "all", 1)]
talk = []
for lab, f, l, x, xb, lb, k in items:
    r = get(f, l, x, xb, lb)
    talk.append({"Number": lab, "Field": f, "Sample": r.median_s * k, "All runs": r.median_f * k, "Difference %": (r.median_s - r.median_f) / r.median_f * 100,
                 "Runs, sample": int(r.n_s), "Runs, all": int(r.n_f)})
talk = pd.DataFrame(talk)

# what the agent uses to choose levers: per emission category, the levers ranked by their change low -> high
cat = eff[eff.field.str.startswith("emissions_")]
rank = []
for (y, fld), g in cat.groupby(["year", "field"]):
    g = g[g.f.abs() > 0]
    if len(g) < 2:
        continue
    top = lambda col, k: set(g.assign(a=g[col].abs()).nlargest(k, "a").lever_id)
    k3, k5 = min(3, len(g)), min(5, len(g))
    rank.append({"Year": y, "Category": fld, "Levers reaching it": len(g), "Same top lever": top("s", 1) == top("f", 1),
                 "Top 3 in common": len(top("s", k3) & top("f", k3)), "Of": k3, "Top 5 in common": len(top("s", k5) & top("f", k5)), "Of ": k5,
                 "Rank correlation": g.s.abs().corr(g.f.abs(), method="spearman"), "Same direction": g.same_sign.mean(),
                 "Same direction, top 5 levers": g.assign(a=g.f.abs()).nlargest(k5, "a").same_sign.mean()})
rank = pd.DataFrame(rank)

# answer keys read from these values
KEYS = [("S50 p10", "gasrecovered_waso_biogas_landfills_tonne", 50, 0, "high", "any", "p10", 120_000, .05), ("S50 p90", "gasrecovered_waso_biogas_landfills_tonne", 50, 0, "high", "any", "p90", 1.4e6, .05),
        ("S3 p10", "area_lndu_improved_croplands", 3, 0, "high", "any", "p10", 2.2e6, .05), ("S3 p90", "area_lndu_improved_croplands", 3, 0, "high", "any", "p90", 3.1e6, .05),
        ("S35 p10", "vehicle_distance_traveled_trns_road_light_electricity", 35, 0, "high", "any", "p10", 18e9, .05), ("S35 p90", "vehicle_distance_traveled_trns_road_light_electricity", 35, 0, "high", "any", "p90", 28e9, .05),
        ("HD1 low", "energy_consumption_electricity_trns_total", 35, 0, "low", "any", "median", 56.0, .01), ("HD1 high", "energy_consumption_electricity_trns_total", 35, 0, "high", "any", "median", 59.9, .01),
        ("HC1 low", "gdp_mmm_usd", 0, 57, "all", "low", "median", 444, .01), ("HC1 mid", "gdp_mmm_usd", 0, 57, "all", "mid", "median", 540, .01), ("HC1 high", "gdp_mmm_usd", 0, 57, "all", "high", "median", 632, .01)]
keys = []
for name, fl, l, x, lb, xb, st, want, tol in KEYS:
    r = get(fl, l, x, xb, lb)
    v = r[f"{st}_f"]
    keys.append({"Key": name, "Written in the key": want, "Sample": r[f"{st}_s"], "All runs": v, "Off by %": (v - want) / want * 100, "Tolerance %": tol * 100, "Within tolerance": abs(v - want) <= tol * abs(want)})
keys = pd.DataFrame(keys)

worst = m[m.moves & (m.x_id == 0) & (m.n_s >= 100)].nlargest(40, "d_median_spread")[
    ["year", "lever_id", "lever_level", "field", "n_s", "n_f", "median_s", "median_f", "p10_f", "p90_f", "d_median_spread", "pct_median"]]

with pd.ExcelWriter(XLSX, engine="xlsxwriter") as w:
    for name, t in (("Summary", summary), ("Lever effects", effects), ("Talk numbers", talk), ("Answer keys", keys), ("Levers by category", rank), ("Largest differences", worst)):
        t.to_excel(w, sheet_name=name, index=False)
        w.sheets[name].set_column(0, len(t.columns), 22)
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
print(summary.T.to_string()); print(effects.to_string()); print(talk.drop(columns="Field").round(3).to_string()); print(keys.round(3).to_string()); print(rank[rank.Year==2050].drop(columns=["Year"]).round(2).to_string()); print("ALL YEARS same top", rank["Same top lever"].mean(), "top3", (rank["Top 3 in common"]/rank["Of"]).mean(), "top5", (rank["Top 5 in common"]/rank["Of "]).mean(), "corr", rank["Rank correlation"].median(), "dir top5", rank["Same direction, top 5 levers"].mean())
print(json.loads((full_dir / "kept.json").read_text()))
