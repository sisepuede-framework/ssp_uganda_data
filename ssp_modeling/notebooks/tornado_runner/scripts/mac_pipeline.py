"""
mac_pipeline.py  (tornado)
--------------------------
Marginal Abatement Cost (MAC) computation for the tornado experiment.

Differences vs whirlpool mac_pipeline:
  - Baseline = strategy_code 'BASE' (not 'PFLO:HBLE')
  - NO subtraction of baseline technical cost (costs are already relative to BASE
    because CostBenefits was initialised with strategy_code_base='BASE')
  - MAC sign: abs(ratio) * sign(technical_cost)  — preserves TC sign direction
  - Output file: marginal_abatement_costs_tornado.csv

Shared logic (inventory mapping, EDGAR loading, cumulative aggregation) is
identical to whirlpool and lives in the same file; only the normalisation and
formula blocks differ.
"""

import numpy as np
import pandas as pd
from pathlib import Path


def run_mac_analysis(
    df_decomposed: pd.DataFrame,
    cb_data: pd.DataFrame,
    att_primary: pd.DataFrame,
    att_strategy: pd.DataFrame,
    iso_code3: str,
    region: str,
    invent_dir: Path,
    run_output_dir: Path,
    strategy_code_baseline: str = "BASE",
) -> pd.DataFrame:
    """
    Compute MAC curves for tornado strategies and export CSV.

    Steps
    -----
    1. Load inventory mapping and EDGAR historical data.
    2. Map SSP variables to inventory categories; aggregate to data_inv.
    3. Compute cumulative emissions by strategy; diff vs BASE baseline.
    4. Compute cumulative technical costs by strategy.
    5. Merge and calculate MAC (USD/tCO2e) preserving TC sign.
    6. Export to CSV.

    Returns
    -------
    mac_df : pd.DataFrame
    """

    # ── 1. Inventory mapping ──────────────────────────────────────────────────
    mapping = pd.read_csv(invent_dir / "emission_targets_uganda_2019_LULUCF.csv")
    mapping = mapping.rename(columns={
        "ssp_subsector":      "subsector_ssp",
        "Gas":                "gas",
        "Vars":               "vars",
        "Subsector_Category": "ID",
        "Subsector":          "subsector",
    })
    if "sector" not in mapping.columns:
        mapping["sector"] = mapping["subsector_ssp"]
    mapping = (
        mapping
        .drop(columns=[iso_code3, "est_from_sisepuede"], errors="ignore")
        .reset_index(drop=False)
        .rename(columns={"index": "row_idx"})
    )
    mapping["ids"] = (
        mapping["row_idx"].astype(str) + ":" +
        mapping["subsector_ssp"].astype(str) + ":" +
        mapping["gas"].astype(str)
    )

    # ── 2. EDGAR historical ───────────────────────────────────────────────────
    edgar = pd.read_csv(invent_dir / "inventory_trajectories.csv")
    edgar = edgar.rename(columns={"CSC.Sector": "sector", "CSC.Subsector": "subsector"})
    edgar = edgar[edgar["Code"] == iso_code3].copy()
    edgar["ID"] = edgar["Subsector_Category"]

    year_cols  = [c for c in edgar.columns if str(c).isdigit()]
    edgar_long = edgar.melt(
        id_vars=["Code", "sector", "subsector", "Gas", "ID"],
        value_vars=year_cols, var_name="year_str", value_name="value",
    )
    edgar_long["Year"] = edgar_long["year_str"].astype(int)
    edgar_long = edgar_long.drop(columns=["year_str"])
    for col in ["strategy_id", "primary_id", "design_id", "future_id"]:
        edgar_long[col] = float("nan")
    edgar_long["strategy"] = "Historical"
    edgar_long["source"]   = "EDGAR"
    edgar_long["Contry"]   = region
    edgar_max_year = int(edgar_long["Year"].max())

    # ── 3. Map SSP vars → inventory categories ────────────────────────────────
    id_vars = ["region", "time_period", "primary_id"]
    data    = df_decomposed[df_decomposed["region"] == region].copy()

    rows_agg = []
    for _, row in mapping.iterrows():
        tvars = [v.strip() for v in str(row["vars"]).split(":") if v.strip() in data.columns]
        if len(tvars) > 1:
            agg_col = data[tvars].sum(axis=1)
        elif len(tvars) == 1:
            agg_col = data[tvars[0]]
        else:
            agg_col = pd.Series(0.0, index=data.index)
        tmp          = data[id_vars].copy()
        tmp["ids"]   = row["ids"]
        tmp["value"] = agg_col.values
        rows_agg.append(tmp)

    data_long = pd.concat(rows_agg, ignore_index=True)
    meta      = mapping[["ids", "sector", "subsector", "gas", "ID"]].copy()
    data_long = data_long.merge(meta, on="ids", how="left")

    data_inv = (
        data_long
        .groupby(["primary_id", "time_period", "ID", "sector", "subsector"], dropna=False)["value"]
        .sum()
        .reset_index()
    )
    data_inv["Year"]   = data_inv["time_period"] + 2015
    data_inv["Gas"]    = data_inv["ID"].str.split(":").str[-1]
    data_inv["Code"]   = iso_code3
    data_inv["Contry"] = region
    data_inv["source"] = "SISEPUEDE"

    data_inv = data_inv.merge(
        att_primary[["primary_id", "strategy_id", "design_id", "future_id"]],
        on="primary_id", how="left",
    )
    data_inv = data_inv.merge(
        att_strategy[["strategy_id", "strategy"]], on="strategy_id", how="left"
    )
    data_inv = data_inv[data_inv["Year"] >= edgar_max_year].copy()

    shared = [
        "primary_id", "strategy_id", "design_id", "future_id",
        "sector", "subsector", "Gas", "ID", "Year", "value",
        "Code", "Contry", "strategy", "source",
    ]
    emissions = pd.concat(
        [
            data_inv[[c for c in shared if c in data_inv.columns]],
            edgar_long[[c for c in shared if c in edgar_long.columns]],
        ],
        ignore_index=True,
    )
    emissions = (
        emissions
        .sort_values(["strategy_id", "sector", "subsector", "Gas", "Year"])
        .reset_index(drop=True)
    )

    # ── 4. Cumulative emissions — diff vs BASE ────────────────────────────────
    em_ssp = emissions[emissions["source"] == "SISEPUEDE"].copy()
    cumul  = (
        em_ssp
        .groupby(["strategy_id", "primary_id"], dropna=False)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "emission_total"})
        .sort_values("strategy_id")
    )
    cumul["emission_total"] = cumul["emission_total"].round(4)

    base_sid = att_strategy.loc[
        att_strategy["strategy_code"] == strategy_code_baseline, "strategy_id"
    ].iloc[0]
    base_emission_val = cumul.loc[cumul["strategy_id"] == base_sid, "emission_total"].values[0]

    cumul["base_emission_total"] = base_emission_val
    cumul["emission_diff"]       = cumul["emission_total"] - base_emission_val

    # ── 5. Cumulative technical costs ─────────────────────────────────────────
    # cb_data['value'] is already in B USD and already relative to BASE
    # (CostBenefits was initialised with strategy_code_base='BASE')
    tc = (
        cb_data[cb_data["cb_type"] == "technical_cost"]
        .groupby(["strategy_id", "primary_id"], dropna=False)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "technical_cost"})
        .sort_values("strategy_id")
    )
    tc["technical_cost"] = tc["technical_cost"] * -1

    # ── 6. Merge, compute MAC, filter ─────────────────────────────────────────
    mac_df = cumul.merge(tc, on=["strategy_id", "primary_id"], how="left")
    mac_df = mac_df.merge(
        att_strategy[["strategy_id", "sector", "transformation_code"]],
        on="strategy_id", how="left",
    )

    # Exclude strategy_id == 0 placeholder
    mac_df = mac_df[mac_df["strategy_id"] != 0]
    mac_df["emission_diff"]  = round(mac_df["emission_diff"],  0)
    mac_df["technical_cost"] = round(mac_df["technical_cost"], 4)

    # MAC = B USD / MtCO2e → USD / tCO2e  (sign follows technical_cost)
    raw_mac = (
        (mac_df["technical_cost"] * 1e9)   # B USD → USD
        / (mac_df["emission_diff"] * 1e6)  # MtCO2e → tCO2e
    )
    mac_df["marginal_abatement_cost"] = raw_mac.abs() * np.sign(mac_df["technical_cost"])

    # Filter invalid values
    mac_df = mac_df[
        mac_df["marginal_abatement_cost"].notna()
        & ~mac_df["marginal_abatement_cost"].isin([float("inf"), float("-inf")])
        & (mac_df["marginal_abatement_cost"] != 0)
    ]

    # Reorder columns
    first_cols = ["strategy_id", "primary_id", "sector", "transformation_code"]
    rest_cols  = [c for c in mac_df.columns if c not in first_cols]
    mac_df = mac_df[first_cols + rest_cols]

    # ── 7. Export ─────────────────────────────────────────────────────────────
    run_output_dir.mkdir(parents=True, exist_ok=True)
    mac_df.to_csv(
        run_output_dir / "marginal_abatement_costs_tornado.csv",
        index=False, encoding="UTF-8",
    )

    return mac_df


def build_tableau_tornado(
    mac_df: pd.DataFrame,
    run_output_dir: Path,
    tableau_dir: Path,
) -> pd.DataFrame:
    """
    Build and export the Tableau tornado plot data.

    Joins ATTRIBUTE_MAP_TORNADO_WHIRLPOOL with MAC results,
    filters out strategies with zero emission difference,
    and writes to tableau_tornado.csv.

    Parameters
    ----------
    mac_df         : output of run_mac_analysis
    run_output_dir : directory containing ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv
    tableau_dir    : destination directory for tableau_tornado.csv
    """
    att_map = pd.read_csv(run_output_dir / "ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv")

    mac_cols = [
        "primary_id", "emission_total", "base_emission_total",
        "emission_diff", "technical_cost", "marginal_abatement_cost",
    ]
    tableau = att_map.merge(
        mac_df[mac_cols],
        left_on="primary_id_tornado",
        right_on="primary_id",
        how="left",
    )
    tableau = tableau[tableau["emission_diff"] != 0].reset_index(drop=True)

    tableau_dir.mkdir(parents=True, exist_ok=True)
    tableau.to_csv(tableau_dir / "tableau_tornado.csv", index=False, encoding="UTF-8")

    return tableau
