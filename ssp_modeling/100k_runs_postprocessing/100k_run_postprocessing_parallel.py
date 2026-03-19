#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import traceback
from io import StringIO
from typing import List, Optional, Tuple
import multiprocessing as mp
import shutil

# Limit threaded libs to avoid oversubscription when we parallelize by processes
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import pandas as pd
import numpy as np
import yaml
import boto3

try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **k: x

# --------------------------
# Logging
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PID:%(process)d] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("postproc")

# Baseline is always primary_id == 0.
# Its file (input+output already merged) lives at tmp/uganda_0.csv.
# No lookup from attribute tables, no renaming ever needed.
PRIMARY_ID_BASE = 0

# --------------------------
# Small helpers
# --------------------------
def read_yaml(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def fetch_csv_from_s3(s3_resource, bucket_name, key):
    obj = s3_resource.Object(bucket_name, key)
    content = obj.get()['Body'].read().decode('utf-8')
    return pd.read_csv(StringIO(content))

def upload_df_to_s3(df, s3_resource, bucket, key):
    buf = StringIO()
    df.to_csv(buf, index=False)
    s3_resource.Object(bucket, key).put(Body=buf.getvalue(), ContentType="text/csv")
    logger.info(f"Uploaded to s3://{bucket}/{key}")

# --------------------------
# Core domain funcs
# --------------------------
def postprocess_cba(cb_raw_df: pd.DataFrame) -> pd.DataFrame:
    parts = cb_raw_df["variable"].astype(str).str.split(":", n=4, expand=True)
    parts.columns = ["name", "sector", "cb_type", "item_1", "item_2"]
    cb_data = pd.concat([cb_raw_df, parts], axis=1)
    cb_data["value"] = cb_data["value"] / 1e9

    group_cols = ["cb_type",  "primary_id",  "time_period"]

    cb_agg = (
        cb_data.groupby(group_cols, dropna=False, as_index=False)["value"]
        .sum()
        .rename(columns={"value": "Cumulative"})
    )

    agg_cb_df = (
        cb_agg.pivot_table(
            index=["primary_id", "time_period"],
            columns="cb_type",
            values="Cumulative",
            aggfunc="sum"
        )
        .reset_index()
    )
    agg_cb_df.columns.name = None

    cb_col_order = [
        "primary_id", "time_period",
        "air_pollution", "congestion", "consumer_savings", "crop_value",
        "ecosystem_services", "env_pollution", "fuel_cost", "human_health",
        "ippu_value", "land_pollution", "lvst_value", "road_safety",
        "sector_specific", "system_cost", "technical_cost", "technical_savings",
        "water_pollution",
    ]
    ordered_cols = [c for c in cb_col_order if c in agg_cb_df.columns]
    extra_cols   = [c for c in agg_cb_df.columns if c not in cb_col_order]
    agg_cb_df = agg_cb_df[ordered_cols + extra_cols]

    return agg_cb_df


def cleanup_tmp(tmp_dir: str, keep_tmp: bool = False) -> None:
    """Keep only uganda_0.csv (baseline); remove all other files and subdirectories."""
    if keep_tmp:
        logger.info("Keeping tmp/ contents (flag --keep-tmp is set).")
        return

    if not os.path.isdir(tmp_dir):
        return

    baseline_name = "uganda_0.csv"
    baseline_path = os.path.join(tmp_dir, baseline_name)

    if not os.path.isfile(baseline_path):
        logger.warning(f"Baseline file not found at {baseline_path}. Will delete all contents of tmp/.")

    for entry in os.scandir(tmp_dir):
        path = entry.path
        try:
            if entry.is_file(follow_symlinks=False):
                if os.path.isfile(baseline_path) and os.path.samefile(path, baseline_path):
                    continue
                os.remove(path)
                logger.info(f"Deleted file: {entry.name}")
            elif entry.is_dir(follow_symlinks=False):
                shutil.rmtree(path)
                logger.info(f"Removed directory: {entry.name}")
            else:
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Could not delete {path}: {e}")

    if os.path.isfile(baseline_path):
        logger.info(f"Cleanup complete. Preserved: {baseline_name}")
    else:
        logger.info("Cleanup complete. No baseline file to preserve.")


# --------------------------
# Python rescale (replaces R intertemporal_decomposition.r)
# --------------------------
def rescale_py(
    data_all: pd.DataFrame,
    te_all: pd.DataFrame,
    rall: List[str],
    initial_conditions_id: str,
    time_period_ref: int,
    growth_clip_pct: float = 1.0,
) -> pd.DataFrame:
    """
    Pure-Python equivalent of the R rescale() function.

    Replicates R behavior exactly:
      1. For each region in rall:
         a. Compute pct_diff and diff growth rates from the ORIGINAL uncalibrated data.
         b. For each sector-gas row in te_all:
            - Compute deviation_factor = target / uncalibrated_baseline_sum.
            - Apply deviation_factor to ALL primary_ids at time_period_ref.
            - Read calibrated init_value from baseline at time_period_ref.
            - Propagate through time:
                init==0  → cumsum(diff) * deviation_factor
                init!=0  → init_value * cumprod(1 + pct_diff)
         c. Compute emission_co2e_subsector_total_* columns.
      2. Concatenate all regions and return (Index column removed).
    """
    results: List[pd.DataFrame] = []

    for tregion in rall:
        data = data_all[data_all["region"] == tregion].copy()

        # All co2e_ columns except subsector totals  (mirrors R tv1_all)
        tv1_all = [
            c for c in data.columns
            if "co2e_" in c and "emission_co2e_subsector_total_" not in c
        ]

        # R: data$Index <- paste0(data$region, "_", data$primary_id)
        data["Index"] = data["region"].astype(str) + "_" + data["primary_id"].astype(str)
        data = data.sort_values(["Index", "time_period"]).reset_index(drop=True)

        # After sort, unique() first-appearance order == lex order  ✓ (matches R post-sort)
        inds     = list(data["Index"].unique())
        ref_inds = f"{tregion}{initial_conditions_id}"   # e.g. "uganda_0"

        tp_sorted = sorted(data["time_period"].unique())
        n_tp      = len(tp_sorted)
        n_inds    = len(inds)

        # Validate uniform time-period count (needed for flat-array assignment)
        tp_counts = data.groupby("Index")["time_period"].count()
        if tp_counts.nunique() != 1:
            raise RuntimeError(
                f"region={tregion}: unequal time_period counts per Index — "
                f"{tp_counts.unique().tolist()}"
            )

        # Snapshot of original data for pct_diff computation.
        # The main loop modifies `data`; pct_diffs must come from original values.
        data_orig = data.copy()

        # Build sector_gas key exactly as R does:
        #   paste(row.names(te_all), ssp_subsector, Gas, sep="-")
        # pandas2ri sends a 0-based DataFrame; R rownames become "1","2",... (1-based)
        te = te_all.copy()
        te["sector_gas"] = (
            (te.index + 1).astype(str) + "-"
            + te["ssp_subsector"].astype(str) + "-"
            + te["Gas"].astype(str)
        )
        sector_gas_all = te["sector_gas"].unique().tolist()

        # ---------------------------------------------------------------
        # Step 1 — Growth-rate cache  (computed from original data, lazy)
        # Each entry: (pct_diff_mat, diff_mat) of shape (n_inds, n_tp)
        # Rows are in `inds` order (= sorted lex = same as data row order).
        # ---------------------------------------------------------------
        _growth_cache: dict = {}

        def _get_growth(var: str):
            if var in _growth_cache:
                return _growth_cache[var]

            # Pivot: rows = inds (lex sorted), cols = tp_sorted
            pivot = (
                data_orig[["Index", "time_period", var]]
                .pivot(index="Index", columns="time_period", values=var)
                .reindex(index=inds, columns=tp_sorted)
            )
            vals = pivot.values.astype(float)   # (n_inds, n_tp)

            # R line 30: single-cell NAs → row mean
            row_means = np.nanmean(vals, axis=1, keepdims=True)
            row_means = np.where(np.isnan(row_means), 0.0, row_means)
            vals = np.where(np.isnan(vals), row_means, vals)
            # R line 32-33: fully-NA row (nanmean still NaN) → 0
            vals = np.nan_to_num(vals, nan=0.0)

            pct_diff_mat = np.zeros((n_inds, n_tp))
            diff_mat     = np.zeros((n_inds, n_tp))

            # R line 35: if (mean(unique(row)) == 0) → pct_diff = 0  (keep zeros)
            # Exact replication: compute mean-of-uniques per row
            row_unique_means = np.array([np.mean(np.unique(row)) for row in vals])
            nonzero = row_unique_means != 0

            if nonzero.any():
                v = vals[nonzero]                          # (k, n_tp)

                # R: pivot$diff = c(diff(vals), 0)
                raw_diff   = np.diff(v, axis=1)            # (k, n_tp-1)
                pivot_diff = np.c_[raw_diff, np.zeros(v.shape[0])]  # (k, n_tp)

                # R: pct_diff = c(0, pivot_diff[1:(n-1)] / vals[1:(n-1)])
                # R 1-based [1:(n-1)] → Python [0:n-1]
                denom = v[:, :n_tp - 1]
                numer = pivot_diff[:, :n_tp - 1]
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = np.where(denom != 0, numer / denom, 0.0)
                # R lines 40-41: NA and Inf → 0
                ratio = np.where(np.isfinite(ratio), ratio, 0.0)

                pct_d = np.zeros_like(v)
                pct_d[:, 1:] = ratio

                # R: diff_var = c(0, diff(vals))
                d_var = np.zeros_like(v)
                d_var[:, 1:] = np.diff(v, axis=1)

                # Winsorize growth rates per time_period (across primary_ids) to
                # prevent a single outlier scenario from distorting the rescaling.
                # Clip at [growth_clip_pct, 100-growth_clip_pct] across the
                # primary_id dimension at each time step.
                if growth_clip_pct > 0 and v.shape[0] > 1:
                    p_lo = np.nanpercentile(pct_d, growth_clip_pct,       axis=0, keepdims=True)
                    p_hi = np.nanpercentile(pct_d, 100 - growth_clip_pct, axis=0, keepdims=True)
                    pct_d = np.clip(pct_d, p_lo, p_hi)

                    d_lo = np.nanpercentile(d_var, growth_clip_pct,       axis=0, keepdims=True)
                    d_hi = np.nanpercentile(d_var, 100 - growth_clip_pct, axis=0, keepdims=True)
                    d_var = np.clip(d_var, d_lo, d_hi)

                pct_diff_mat[nonzero] = pct_d
                diff_mat[nonzero]     = d_var

            _growth_cache[var] = (pct_diff_mat, diff_mat)
            return pct_diff_mat, diff_mat

        # ---------------------------------------------------------------
        # Step 2 — Sector-gas loop: deviation factor + propagation
        # ---------------------------------------------------------------
        ref_tp_mask = (data["Index"] == ref_inds) & (data["time_period"] == time_period_ref)
        all_tp_ref_mask = data["time_period"] == time_period_ref

        for sg in sector_gas_all:
            sg_row     = te[te["sector_gas"] == sg]
            vars_str   = sg_row["Vars"].values[0]
            tv1        = [v.strip() for v in str(vars_str).split(":") if v.strip()]
            tv1        = [v for v in tv1 if v in data.columns]
            if not tv1:
                continue

            target_total = float(sg_row["tvalue"].values[0])

            # R line 67: uncalibrated_total from CURRENT data (may be modified by prev iterations)
            uncal      = float(data.loc[ref_tp_mask, tv1].values.sum())
            dev_factor = 1.0 if uncal == 0 else (target_total / uncal)

            # R line 69: apply deviation_factor to ALL inds at time_period_ref
            data.loc[all_tp_ref_mask, tv1] = (
                data.loc[all_tp_ref_mask, tv1].values * dev_factor
            )

            # R lines 81-87: propagate per var
            for var in tv1:
                pct_diff_mat, diff_mat = _get_growth(var)

                # R line 81: init_value from BASELINE (ref_inds) at time_period_ref
                # (reads AFTER deviation factor was applied → calibrated value)
                init_arr   = data.loc[ref_tp_mask, var].values
                init_value = float(init_arr[0]) if len(init_arr) > 0 else 0.0

                # R lines 82-87: vectorised over all inds
                if init_value == 0.0:
                    # cumsum of absolute diffs, scaled by dev_factor
                    new_vals = np.cumsum(diff_mat, axis=1) * dev_factor   # (n_inds, n_tp)
                else:
                    # init_value × cumulative product of (1 + growth_rate)
                    new_vals = init_value * np.cumprod(1.0 + pct_diff_mat, axis=1)

                # Forward-fill outlier values: for each time_period scan the
                # distribution of new_vals across primary_ids (axis=0).
                # Any scenario whose value falls outside K×IQR from [Q1, Q3]
                # is replaced with its own previous-period value.  Processing
                # left-to-right ensures the replacement value is already clean.
                if n_inds > 3:
                    _K = 5.0
                    for t_idx in range(1, n_tp):
                        col = new_vals[:, t_idx]
                        q1, q3 = np.percentile(col, [25, 75])
                        iqr = q3 - q1
                        if iqr > 0:
                            spike = (col < q1 - _K * iqr) | (col > q3 + _K * iqr)
                            if spike.any():
                                new_vals[spike, t_idx] = new_vals[spike, t_idx - 1]

                # Assign back — data is sorted (Index lex, time_period asc) and every
                # ind has exactly n_tp rows, so flatten maps directly to data rows.
                data[var] = new_vals.flatten()

        # ---------------------------------------------------------------
        # Step 3 — Subsector totals  (R lines 92-108)
        # ---------------------------------------------------------------
        for subsector in te["ssp_subsector"].dropna().unique():
            sub_vars_raw = te.loc[te["ssp_subsector"] == subsector, "Vars"].dropna()
            sub_vars: List[str] = []
            for v_str in sub_vars_raw:
                for v in str(v_str).split(":"):
                    v = v.strip()
                    if v and v not in sub_vars:
                        sub_vars.append(v)
            sub_vars = [v for v in sub_vars if v in data.columns]

            col = f"emission_co2e_subsector_total_{subsector}"
            data[col] = data[sub_vars].sum(axis=1) if sub_vars else 0.0

        # R line 113: data$Index <- NULL
        data = data.drop(columns=["Index"])
        results.append(data)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


# --------------------------
# Global (per-process) state for workers
# --------------------------
PROC_STATE = {
    "PID_CACHE_DIR":       None,
    "CONFIG_DIR":          None,
    "attribute_primary_df":  None,
    "attribute_strategy_df": None,
    "baseline_decomposed_df": None,
}

def worker_init(
    pid_cache_dir: str,
    cache_dir: str,
    config_dir: str,
):
    """Runs once per worker process. Loads shared data into memory; per-pid data is read per task."""
    PROC_STATE["PID_CACHE_DIR"] = pid_cache_dir
    PROC_STATE["CONFIG_DIR"]    = config_dir
    # Load shared tables once per worker process (not once per task)
    PROC_STATE["attribute_primary_df"]   = pd.read_pickle(os.path.join(cache_dir, "attribute_primary_df.pkl"))
    PROC_STATE["attribute_strategy_df"]  = pd.read_pickle(os.path.join(cache_dir, "attribute_strategy_df.pkl"))
    PROC_STATE["baseline_decomposed_df"] = pd.read_pickle(os.path.join(cache_dir, "baseline_decomposed_df.pkl"))

    # Patch CostBenefits.initialize_session to use a per-process unique tmp DB file.
    # The default implementation writes to a single shared tmp_cb_data.db; when multiple
    # worker processes run concurrently they overwrite each other → "malformed" / "no such table".
    import inspect as _inspect, shutil as _shutil
    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy.orm import sessionmaker as _sessionmaker
    from costs_benefits_ssp.cb_calculate import CostBenefits as _CB

    def _per_process_initialize_session(self):
        _lib_dir = os.path.dirname(os.path.abspath(_inspect.getfile(type(self))))
        _src_db  = os.path.join(_lib_dir, "database", "backup", "cb_data.db")
        _tmp_db  = os.path.join(_lib_dir, "database", f"tmp_cb_data_{os.getpid()}.db")
        _shutil.copyfile(_src_db, _tmp_db)
        _engine  = _create_engine(f"sqlite:///{_tmp_db}")
        _Session = _sessionmaker(bind=_engine)
        return _Session()

    _CB.initialize_session = _per_process_initialize_session



def run_decomposition_worker(
    primary_id_to_decompose: int,
) -> Tuple[int, Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[str]]:
    """
    CB + emissions for a single primary_id.
    Returns (primary_id, emissions_df, cb_df, error).
    Workers do NOT upload to S3 — main() concatenates all results and uploads once.
    """
    try:
        # Load only this pid's slice (small file) — shared tables are already in PROC_STATE
        pid_pkl = os.path.join(PROC_STATE["PID_CACHE_DIR"], f"{primary_id_to_decompose}.pkl")
        if not os.path.exists(pid_pkl):
            return primary_id_to_decompose, None, None, f"No cached file for primary_id={primary_id_to_decompose}"
        decomposed_df         = pd.read_pickle(pid_pkl)
        attribute_primary_df  = PROC_STATE["attribute_primary_df"]
        attribute_strategy_df = PROC_STATE["attribute_strategy_df"]
        base_decomposed_df    = PROC_STATE["baseline_decomposed_df"]

        if decomposed_df.empty:
            return primary_id_to_decompose, None, None, f"No rows in decomposed_df for primary_id={primary_id_to_decompose}"

        if base_decomposed_df.empty:
            return primary_id_to_decompose, None, None, "Baseline data is empty in cache."

        # Build emissions summary — columns already present in decomposed_df
        decomposed_df["total_emissions"] = (
            decomposed_df.filter(like="emission_co2e_subsector_total").sum(axis=1)
        )
        
        cols_to_keep = ["primary_id", "time_period", "total_emissions"]
        emissions_df = decomposed_df[[c for c in cols_to_keep if c in decomposed_df.columns]].copy()

        # --- Strategy / future lookup (soft-fail) ---
        # These are only required for CB. If the attribute tables don't cover this
        # primary_id, we still save emissions and skip CB (no error raised).
        future_id     = None
        strategy_code = None
        _cb_skip_reason = None
        try:
            attr_row = attribute_primary_df.loc[
                attribute_primary_df["primary_id"] == primary_id_to_decompose
            ]
            if len(attr_row) == 0:
                _cb_skip_reason = f"pid={primary_id_to_decompose} not found in attribute_primary_df"
            else:
                future_id = int(attr_row["future_id"].values[0])
                sc = attr_row["strategy_code"].values[0]
                if pd.isna(sc):
                    _cb_skip_reason = f"pid={primary_id_to_decompose} has no strategy_code (strategy_id not in attribute_strategy_df)"
                else:
                    strategy_code = sc
        except Exception as _e:
            _cb_skip_reason = f"pid={primary_id_to_decompose} lookup error: {_e}"

        # Add future_id to emissions for traceability (if available)
        if future_id is not None:
            emissions_df["future_id"] = future_id

        # --- Cost Benefits (optional — skipped when strategy_code unavailable) ---
        if strategy_code is None:
            import logging as _logging
            _logging.getLogger(__name__).warning(f"CB skipped — {_cb_skip_reason}")
            return primary_id_to_decompose, emissions_df, None, None

        from costs_benefits_ssp.cb_calculate import CostBenefits

        # Append baseline (primary_id=0) + current run.
        ssp_data = pd.concat([base_decomposed_df, decomposed_df], ignore_index=True)
        ssp_data = ssp_data.replace(np.nan, 0.0)
        strategy_code_base = "BASE"

        cb_config_path = os.path.join(PROC_STATE["CONFIG_DIR"], "cb_config_params.xlsx")
        if not os.path.exists(cb_config_path):
            return primary_id_to_decompose, emissions_df, None, None  # no CB config → skip CB

        try:
            import contextlib, io as _io, warnings as _warnings
            _devnull = _io.StringIO()
            with contextlib.redirect_stdout(_devnull), \
                 _warnings.catch_warnings():
                _warnings.simplefilter("ignore")  # suppress SettingWithCopyWarning and others from cb lib
                # Drop strategy_code if present — CostBenefits.marge_attribute_strategy merges
                # att_primary with att_strategy on strategy_id; duplicate strategy_code columns
                # would be renamed to strategy_code_x / strategy_code_y, breaking the CB library.
                _att_primary_for_cb = attribute_primary_df.drop(columns=["strategy_code"], errors="ignore")
                cb = CostBenefits(ssp_data, _att_primary_for_cb, attribute_strategy_df, strategy_code_base)
                cb.ssp_data["future_id"] = 0
                cb.load_cb_parameters(cb_config_path)

                results_system = cb.compute_system_cost_for_strategy(strategy_code_tx=strategy_code)
                results_tx     = cb.compute_technical_cost_for_strategy(strategy_code_tx=strategy_code)
                results_all    = pd.concat([results_system, results_tx], ignore_index=True)
                results_all_pp = cb.cb_process_interactions(results_all)
                results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)

            results_all_pp_shifted["primary_id"] = primary_id_to_decompose
            if future_id is not None:
                results_all_pp_shifted["future_id"] = future_id

            agg_cb_df = postprocess_cba(results_all_pp_shifted)
            return primary_id_to_decompose, emissions_df, agg_cb_df, None

        except Exception as cb_err:
            # CB failed (e.g. malformed SQLite DB) — still preserve emissions
            import logging as _logging
            _logging.getLogger(__name__).warning(
                f"CB failed for pid={primary_id_to_decompose}: {type(cb_err).__name__}: {cb_err}"
            )
            return primary_id_to_decompose, emissions_df, None, None

    except Exception as e:
        return primary_id_to_decompose, None, None, f"{e}\n{traceback.format_exc()}"


# --------------------------
# Main
# --------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir-id", required=True, help="Model output directory id (e.g., 42)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    parser.add_argument("--profile", default=None, help="AWS profile name (overrides YAML)")
    parser.add_argument("--run-id", default=None, help="Override RUN_ID (else use value in script)")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep files in tmp/ (skip cleanup)")
    args = parser.parse_args()

    # Paths
    SCRIPT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR_PATH = os.path.join(SCRIPT_DIR_PATH, "config")
    CW_DIR_PATH     = os.path.join(SCRIPT_DIR_PATH, "cw")
    TMP_DIR_PATH    = os.path.join(SCRIPT_DIR_PATH, "tmp")


    os.makedirs(TMP_DIR_PATH, exist_ok=True)

    # Validate baseline file exists before doing anything else
    base_file = os.path.join(TMP_DIR_PATH, "uganda_0.csv")
    if not os.path.exists(base_file):
        raise FileNotFoundError(
            f"Baseline file not found: {base_file}\n"
            "This file (input+output merged, primary_id=0) must exist before running."
        )
    logger.info(f"Baseline file confirmed: {base_file}")
    baseline_df = pd.read_csv(base_file)

    # AWS
    aws_config   = read_yaml(os.path.join(CONFIG_DIR_PATH, "aws_credentials_config.yaml"))
    PROFILE_NAME = args.profile or aws_config["profile_name"]
    BUCKET_NAME  = aws_config["bucket_name"]

    # RUN/Prefixes
    RUN_ID              = args.run_id or "sisepuede_run_2026-03-10t13;27;53.264959"
    RUN_DB_PREFIX       = f'run_database/{RUN_ID}/'
    MODEL_OUTPUT_PREFIX = f'{RUN_DB_PREFIX}model_output/region=uganda/model_output_{args.dir_id}/'
    MODEL_INPUT_PREFIX  = f'{RUN_DB_PREFIX}model_input/region=uganda/model_input_{args.dir_id}/'
    TRANSFER_PREFIX     = f"transfers/{RUN_ID}/"

    # Decomposition params
    TARGET_COUNTRY            = "UGA"
    EMISSION_TARGETS_CSV_PATH = os.path.join(CW_DIR_PATH, 'emission_targets_uganda_2019_LULUCF.csv')
    TIME_PERIOD_REF           = 4
    S3_DECOMPOSED_DIR_PREFIX  = f"{RUN_DB_PREFIX}decomposed_outputs/"
    S3_CB_DIR_PREFIX          = f"{RUN_DB_PREFIX}cb_outputs/"

    session = boto3.Session(profile_name=PROFILE_NAME)
    s3      = session.resource('s3')

    # Fetch data once from S3
    logger.info("Fetching inputs from S3 (one-time)…")
    output_df             = fetch_csv_from_s3(s3, BUCKET_NAME, f'{MODEL_OUTPUT_PREFIX}data.csv')
    input_df              = fetch_csv_from_s3(s3, BUCKET_NAME, f'{MODEL_INPUT_PREFIX}data.csv')
    attribute_primary_df  = fetch_csv_from_s3(s3, BUCKET_NAME, f'{TRANSFER_PREFIX}ATTRIBUTE_PRIMARY.csv')
    attribute_strategy_df = fetch_csv_from_s3(s3, BUCKET_NAME, f'{TRANSFER_PREFIX}ATTRIBUTE_STRATEGY.csv')
    emission_targets_df   = pd.read_csv(EMISSION_TARGETS_CSV_PATH)

    # Build processing list — exclude primary_id=0 (baseline already on disk)
    primary_ids = sorted([
        pid for pid in output_df["primary_id"].dropna().astype(int).unique()
        if pid != PRIMARY_ID_BASE
    ])
    logger.info(f"Found {len(primary_ids)} non-baseline primary_ids to process.")

    # Build data_all: merge output+input for ALL primary_ids.
    # Remove pid=0 from output_df before the merge to avoid duplicating the baseline
    # rows that pd.concat([baseline_df, ...]) adds below.
    logger.info("Building data_all (output merged with input, all primary_ids)…")
    output_df_no_base = output_df[output_df["primary_id"] != PRIMARY_ID_BASE].copy()
    data_all = pd.merge(output_df_no_base, input_df, on=["primary_id", "region", "time_period"], how="left")
    data_all = pd.concat([baseline_df, data_all], ignore_index=True)
    data_all = data_all.fillna(0)
    logger.info(f"data_all shape: {data_all.shape}  |  primary_ids: {len(data_all['primary_id'].unique())}")

    # Build te_df (emission targets for rescale)
    te_cols = ["Subsector", "Gas", "Vars", "Subsector_Category", "ssp_subsector", TARGET_COUNTRY]
    te_df   = emission_targets_df[[c for c in te_cols if c in emission_targets_df.columns]].copy()
    te_df   = te_df.rename(columns={TARGET_COUNTRY: "tvalue"})

    # Filter data to time_period >= TIME_PERIOD_REF (same as R input)
    data_all_r = data_all.loc[data_all["time_period"] >= TIME_PERIOD_REF].copy()
    rall = data_all_r["region"].dropna().astype(str).unique().tolist()
    if not rall:
        raise RuntimeError("No regions found in data_all after filtering by time_period.")

    # Pre-flight: replace zeros in emission vars at TIME_PERIOD_REF with 0.01
    # (prevents division-by-zero in the deviation-factor calculation)
    _EXCLUDE_VARS = {
        "emission_co2e_co2_ccsq_direct_air_capture",
        "emission_co2e_ch4_ccsq_direct_air_capture",
        "emission_co2e_n2o_ccsq_direct_air_capture",
    }
    _all_vars: set = set()
    for _v in te_df["Vars"].dropna():
        for _part in str(_v).split(":"):
            _part = _part.strip()
            if _part:
                _all_vars.add(_part)
    _all_vars -= _EXCLUDE_VARS

    for _var in sorted(_all_vars):
        if _var not in data_all_r.columns:
            logger.warning(f"Pre-flight: missing column '{_var}' in data_all_r")
            continue
        _mask = (data_all_r["time_period"] == TIME_PERIOD_REF) & (data_all_r[_var] == 0)
        if _mask.any():
            data_all_r[_var] = data_all_r[_var].astype(float)
            data_all_r.loc[_mask, _var] = 0.01

    # Run Python rescale (replaces R intertemporal_decomposition.r)
    logger.info(f"Running rescale_py() for {len(primary_ids)} primary_ids…")
    decomposed_df = rescale_py(
        data_all_r,
        te_df,
        rall,
        "_0",
        TIME_PERIOD_REF,
    )
    decomposed_df = decomposed_df[decomposed_df["primary_id"] != PRIMARY_ID_BASE].copy()
    logger.info(f"rescale_py() completed. decomposed_df shape: {decomposed_df.shape}  |  primary_ids: {len(decomposed_df['primary_id'].unique())}")

    # Cache shared tables (loaded once per worker process)
    CACHE_DIR = os.path.join(TMP_DIR_PATH, "cache")
    os.makedirs(CACHE_DIR, exist_ok=True)
    logger.info(f"attribute_primary_df columns: {attribute_primary_df.columns.tolist()}")
    logger.info(f"attribute_strategy_df columns: {attribute_strategy_df.columns.tolist()}")
    # Pre-join strategy_code into attribute_primary_df so workers do a single lookup
    _strat_cols = [c for c in ["strategy_id", "strategy_code"] if c in attribute_strategy_df.columns]
    if "strategy_code" in attribute_strategy_df.columns:
        attribute_primary_df = attribute_primary_df.merge(
            attribute_strategy_df[_strat_cols],
            on="strategy_id",
            how="left",
        )
    else:
        logger.warning("attribute_strategy_df has no 'strategy_code' column — CB will be skipped for all pids")
    attribute_primary_df.to_pickle(os.path.join(CACHE_DIR, "attribute_primary_df.pkl"))
    attribute_strategy_df.to_pickle(os.path.join(CACHE_DIR, "attribute_strategy_df.pkl"))
    baseline_df.to_pickle(os.path.join(CACHE_DIR, "baseline_decomposed_df.pkl"))

    # Pre-split decomposed_df into one small pickle per primary_id
    # so each worker reads only its own slice instead of the full dataframe
    PID_CACHE_DIR = os.path.join(CACHE_DIR, "pids")
    os.makedirs(PID_CACHE_DIR, exist_ok=True)
    decomposed_pids = set()
    for pid, grp in decomposed_df.groupby("primary_id"):
        grp.reset_index(drop=True).to_pickle(os.path.join(PID_CACHE_DIR, f"{int(pid)}.pkl"))
        decomposed_pids.add(int(pid))
    logger.info(f"Pre-split: {len(decomposed_pids)} pickles created → {PID_CACHE_DIR}")
    logger.info(f"Cached shared tables: baseline={baseline_df.shape}")

    # Diagnose any primary_id mismatch between processing list and rescale output
    primary_ids_set = set(primary_ids)
    missing_from_decomposed = primary_ids_set - decomposed_pids
    extra_in_decomposed     = decomposed_pids - primary_ids_set
    if missing_from_decomposed:
        logger.warning(
            f"DIAGNOSTIC: {len(missing_from_decomposed)} primary_id(s) in output_df "
            f"but missing from rescale output (no pickle will be created): "
            f"{sorted(missing_from_decomposed)[:20]}"
        )
    if extra_in_decomposed:
        logger.info(
            f"DIAGNOSTIC: {len(extra_in_decomposed)} primary_id(s) in rescale output "
            f"but not in processing list (ignored): {sorted(extra_in_decomposed)[:20]}"
        )

    mp.set_start_method("spawn", force=True)

    init_args = (
        PID_CACHE_DIR,
        CACHE_DIR,
        CONFIG_DIR_PATH,
    )

    logger.info(f"Starting pool with {args.workers} workers…")
    with mp.get_context("spawn").Pool(
        processes=args.workers,
        initializer=worker_init,
        initargs=init_args
    ) as pool:
        results = list(tqdm(
            pool.imap_unordered(run_decomposition_worker, primary_ids),
            total=len(primary_ids)
        ))

    # Clean up per-process tmp CB database files left by the patched initialize_session
    import glob as _glob, costs_benefits_ssp.cb_calculate as _cb_mod
    _cb_db_dir = os.path.join(os.path.dirname(os.path.abspath(_cb_mod.__file__)), "database")
    for _f in _glob.glob(os.path.join(_cb_db_dir, "tmp_cb_data_*.db")):
        try:
            os.remove(_f)
        except Exception:
            pass

    # Collect and separate results.
    # Unit of analysis is primary_id + time_period → emissions are ALWAYS saved.
    # CB is optional: missing strategy mapping is a soft-skip, not a hard error.
    emissions_frames: List[pd.DataFrame] = []
    cb_frames: List[pd.DataFrame] = []
    hard_errors   = []   # could not compute even emissions
    cb_skipped    = 0    # emissions ok but CB skipped (no strategy mapping)
    for pid, em_df, cb_df, err in results:
        # Always save emissions when available, regardless of CB outcome
        if em_df is not None and not em_df.empty:
            emissions_frames.append(em_df)
        if cb_df is not None and not cb_df.empty:
            cb_frames.append(cb_df)
        # Hard error = could not load / process decomposed data
        if err:
            hard_errors.append((pid, err))
        elif cb_df is None and (em_df is not None and not em_df.empty):
            cb_skipped += 1

    logger.info(
        f"Results: {len(emissions_frames)} emissions, {len(cb_frames)} CB, "
        f"{cb_skipped} CB-skipped (no strategy mapping), {len(hard_errors)} hard errors."
    )
    if hard_errors:
        logger.warning(f"{len(hard_errors)} primary_id(s) failed entirely:")
        for pid, err in hard_errors[:10]:
            logger.warning(f"  - {pid}: {err}")
        if len(hard_errors) > 10:
            logger.warning("  … (more errors not shown)")

    # Upload single combined file per table
    region = rall[0]

    if emissions_frames:
        all_emissions = pd.concat(emissions_frames, ignore_index=True)
        em_key = f"{S3_DECOMPOSED_DIR_PREFIX}region={region}/decomposed_emissions_{args.dir_id}/data.csv"
        _em_upload = all_emissions[[c for c in ["primary_id", "time_period", "total_emissions"] if c in all_emissions.columns]]
        upload_df_to_s3(_em_upload, s3, BUCKET_NAME, em_key)
        logger.info(f"Uploaded combined emissions ({len(emissions_frames)} primary_ids) → {em_key}")
    else:
        logger.warning("No emission frames to upload.")

    if cb_frames:
        all_cb = pd.concat(cb_frames, ignore_index=True)
        cb_key = f"{S3_CB_DIR_PREFIX}region={region}/cb_{args.dir_id}/data.csv"
        upload_df_to_s3(all_cb, s3, BUCKET_NAME, cb_key)
        logger.info(f"Uploaded combined CB ({len(cb_frames)} primary_ids) → {cb_key}")
    else:
        logger.warning("No CB frames to upload.")

    cleanup_tmp(TMP_DIR_PATH, keep_tmp=args.keep_tmp)

if __name__ == "__main__":
    main()
