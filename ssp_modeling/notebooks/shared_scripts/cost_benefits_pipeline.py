"""
cost_benefits_pipeline.py
--------------------------
Full cost-benefits computation: system costs + technical costs → reshaped
cb_data DataFrame (B USD).  Exports cost_benefits_data_whirlpool.csv.
"""

import sys
import pandas as pd
from pathlib import Path


def run_cost_benefits(
    df_decomposed: pd.DataFrame,
    att_primary: pd.DataFrame,
    att_strategy: pd.DataFrame,
    cb_config_path: Path,
    run_output_dir: Path,
    project_dir: Path,
    strategy_code_base: str = "BASE",
) -> pd.DataFrame:
    """
    Run cost-benefit analysis and return the reshaped *cb_data* DataFrame.

    Steps
    -----
    1. Instantiate CostBenefits and load parameters.
    2. Compute system costs and technical costs for all strategies.
    3. Process interactions and shift costs.
    4. Reshape, scale to B USD, and enrich with strategy metadata.
    5. Export to CSV.

    Returns
    -------
    cb_data : pd.DataFrame  (values in B USD)
    """
    cb_costs_path = str(project_dir / "ssp_modeling" / "cost-benefits")
    if cb_costs_path not in sys.path:
        sys.path.insert(0, cb_costs_path)

    from costs_benefits_ssp.cb_calculate import CostBenefits

    if strategy_code_base not in att_strategy["strategy_code"].values:
        raise ValueError(
            f"Base strategy '{strategy_code_base}' not found in att_strategy"
        )

    # ── 1. Instantiate and load parameters ───────────────────────────────────
    cb = CostBenefits(df_decomposed, att_primary, att_strategy, strategy_code_base)
    cb.load_cb_parameters(str(cb_config_path))

    # ── 2. Compute costs ─────────────────────────────────────────────────────
    results_system = cb.compute_system_cost_for_all_strategies(verbose=False)
    results_tx     = cb.compute_technical_cost_for_all_strategies(verbose=False)

    # ── 3. Process and shift ─────────────────────────────────────────────────
    results_all            = pd.concat([results_system, results_tx], ignore_index=True)
    results_all_pp         = cb.cb_process_interactions(results_all)
    results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)

    # ── 4. Reshape ────────────────────────────────────────────────────────────
    cb_data = results_all_pp_shifted.copy()

    cb_chars = cb_data["variable"].astype(str).str.split(":", n=4, expand=True)
    cb_chars.columns = ["name", "sector", "cb_type", "item_1", "item_2"]
    cb_data = pd.concat([cb_data, cb_chars], axis=1)

    # Scale USD → B USD
    for col in ["value", "variable_value_baseline", "variable_value_pathway"]:
        cb_data[col] = cb_data[col] / 1e9

    # Remove 'shifted' rows
    cb_data = cb_data[
        ~cb_data["item_2"].astype(str).str.contains("shifted", na=False)
    ]
    cb_data = cb_data[
        ~cb_data["variable"].astype(str).str.contains("shifted2", na=False)
    ]

    # Calendar year
    cb_data["Year"] = cb_data["time_period"] + 2015

    # Dynamic mappings from att_strategy / att_primary
    strategy_id_map   = att_strategy.set_index("strategy_code")["strategy_id"].to_dict()
    strategy_name_map = att_strategy.set_index("strategy_code")["strategy"].to_dict()
    primary_id_map = (
        att_strategy[["strategy_code", "strategy_id"]]
        .merge(att_primary[["primary_id", "strategy_id"]], on="strategy_id", how="left")
        .drop_duplicates("strategy_code")
        .set_index("strategy_code")["primary_id"]
        .to_dict()
    )

    cb_data["strategy"]    = (
        cb_data["strategy_code"].astype(str).map(strategy_name_map).fillna(cb_data["strategy_code"])
    )
    cb_data["strategy_id"] = cb_data["strategy_code"].astype(str).map(strategy_id_map)
    cb_data["primary_id"]  = cb_data["strategy_code"].astype(str).map(primary_id_map)
    cb_data["ids"]         = (
        cb_data["variable"].astype(str) + ":" + cb_data["strategy_id"].astype(str)
    )

    # Fix ENTC electricity capex sign (must be negative = investment)
    mask_entc = cb_data["variable"].astype(str).str.contains(
        "cb:entc:technical_cost:electricity:capex", na=False
    )
    cb_data.loc[mask_entc, "value"] = -cb_data.loc[mask_entc, "value"].abs()

    # Merge GDP
    gdp = df_decomposed[["primary_id", "time_period", "gdp_mmm_usd"]].copy()
    cb_data = cb_data.merge(gdp, on=["primary_id", "time_period"], how="left")

    # ── 5. Export ─────────────────────────────────────────────────────────────
    run_output_dir.mkdir(parents=True, exist_ok=True)
    cb_data.to_csv(run_output_dir / "cost_benefits_data_whirlpool.csv", index=False, encoding="UTF-8")

    return cb_data
