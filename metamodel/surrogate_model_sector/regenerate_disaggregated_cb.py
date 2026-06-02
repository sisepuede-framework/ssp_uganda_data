"""
regenerate_disaggregated_cb.py
------------------------------
Rebuilds training_data_sector_<RUN>.parquet with DISAGGREGATED cost/benefit
targets (per type × per year) replacing the 8 aggregate cost/benefit columns.

This mirrors the updated cost/benefit cells in data_prep_sector.ipynb, but works
off the EXISTING sector parquet (features + 48 sector×year emissions + ids), so
it does not need to re-run the full notebook or hit S3. GDP per year is read from
the IDE results CSV in chunks (only the 3 needed columns).

New target columns:
  benefit_<type>_yr<year>   (14 types × 4 years = 56, positive)
  cost_<type>_yr<year>      (3 types  × 4 years = 12, negative)
  gdp_mmm_usd_yr<year>      (4, for cost-as-%-of-GDP in the chatbot)

Run:  python regenerate_disaggregated_cb.py
"""

import os
import glob

import numpy as np
import pandas as pd

RUN = "2025-11-12t22;19;28.194097"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # metamodel/
SIM = os.path.join(BASE, "data", "ssp", f"sisepuede_run_{RUN}")
TRAIN = os.path.join(BASE, "data", "training")

SECTOR_PARQUET = os.path.join(TRAIN, f"training_data_sector_{RUN}.parquet")
CB_CSV = glob.glob(os.path.join(SIM, "wide_cb_data_lhc_*.csv"))[0]
IDE_CSV = os.path.join(SIM, f"sisepuede_results_IDE_{RUN}.csv")

TARGET_YEARS = [2030, 2040, 2050, 2070]
AGG_COLS = [
    "2025_2035_mean_benefits", "2025_2070_mean_benefits",
    "2025_2035_mean_costs", "2025_2070_mean_costs",
    "2025_2035_max_costs_rel_to_gdp", "2025_2070_max_costs_rel_to_gdp",
    "2025_2035_cumulative_cost_rel_to_gdp", "2025_2070_cumulative_cost_rel_to_gdp",
]


def pivot_field(df, field, prefix):
    piv = df.pivot_table(index="primary_id", columns="year", values=field, aggfunc="sum")
    piv = piv[[y for y in TARGET_YEARS if y in piv.columns]]
    piv.columns = [f"{prefix}_yr{int(y)}" for y in piv.columns]
    return piv


def build_cost_benefit() -> pd.DataFrame:
    cb = pd.read_csv(CB_CSV)
    cb.columns = cb.columns.str.lower()
    cb = cb.fillna(0)
    cost_fields = [c for c in cb.columns if "cost" in c]                       # fuel/system/technical_cost
    benefit_fields = [c for c in cb.columns
                      if c not in cost_fields and c not in ["primary_id", "future_id", "strategy_code", "year"]]
    # Raw convention is already diverging: benefits are positive, costs are
    # negative cash flows (technical_cost is ~85% negative). Keep raw signs so
    # the chart shows benefits up / costs down and net = benefits + costs.

    cb_year = cb[cb["year"].isin(TARGET_YEARS)]
    frames = []
    for f in benefit_fields:
        frames.append(pivot_field(cb_year, f, f"benefit_{f}"))
    for f in cost_fields:
        frames.append(pivot_field(cb_year, f, f"cost_{f.replace('_cost', '')}"))
    out = pd.concat(frames, axis=1).reset_index()
    print(f"  cost/benefit: {len(benefit_fields)} benefits + {len(cost_fields)} costs "
          f"→ {out.shape[1]-1} cols for {out.shape[0]} primary_ids")
    return out


def build_gdp(primary_ids: set) -> pd.DataFrame:
    tp_to_year = {y - 2015: y for y in TARGET_YEARS}  # 15→2030, 25→2040, 35→2050, 55→2070
    keep = []
    for chunk in pd.read_csv(IDE_CSV, usecols=["primary_id", "time_period", "gdp_mmm_usd"],
                             chunksize=1_000_000):
        chunk = chunk[chunk["time_period"].isin(tp_to_year) & chunk["primary_id"].isin(primary_ids)]
        if len(chunk):
            keep.append(chunk)
    gdp = pd.concat(keep, ignore_index=True)
    gdp["year"] = gdp["time_period"].map(tp_to_year)
    piv = pivot_field(gdp, "gdp_mmm_usd", "gdp_mmm_usd").reset_index()
    print(f"  gdp: {piv.shape[1]-1} year cols for {piv.shape[0]} primary_ids")
    return piv


def main():
    print("Loading existing sector parquet ...")
    df = pd.read_parquet(SECTOR_PARQUET)
    print(f"  before: {df.shape}")
    # Drop the old aggregates AND any disaggregated cols from a prior run (idempotent).
    stale = [c for c in df.columns
             if c in AGG_COLS or c.startswith(("benefit_", "cost_", "gdp_mmm_usd_yr"))]
    df = df.drop(columns=stale)

    print("Building disaggregated cost/benefit from CB CSV ...")
    cb_agg = build_cost_benefit()

    print("Reading GDP per year from IDE results (chunked) ...")
    gdp = build_gdp(set(df["primary_id"].astype(int)))

    cb_agg["primary_id"] = cb_agg["primary_id"].astype(int)
    gdp["primary_id"] = gdp["primary_id"].astype(int)
    df["_pid"] = df["primary_id"].astype(int)

    merged = df.merge(cb_agg, left_on="_pid", right_on="primary_id", how="left", suffixes=("", "_cb"))
    merged = merged.merge(gdp, left_on="_pid", right_on="primary_id", how="left", suffixes=("", "_gdp"))
    merged = merged.drop(columns=[c for c in ["_pid", "primary_id_cb", "primary_id_gdp"] if c in merged.columns])

    new_cols = [c for c in merged.columns if c.startswith(("benefit_", "cost_", "gdp_mmm_usd_yr"))]
    nan_count = merged[new_cols].isnull().sum().sum()
    print(f"  after: {merged.shape}  | new target cols: {len(new_cols)}  | NaNs in new cols: {nan_count}")
    if nan_count:
        raise SystemExit("ERROR: NaNs in new cost/benefit columns — check primary_id coverage.")

    merged.to_parquet(SECTOR_PARQUET, index=False)
    print(f"Saved: {SECTOR_PARQUET}")
    print("Sample new columns:", new_cols[:3], "...", new_cols[-3:])


if __name__ == "__main__":
    main()
