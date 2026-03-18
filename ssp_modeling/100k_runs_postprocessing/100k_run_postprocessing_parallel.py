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

# rpy2
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri, default_converter
from rpy2.robjects.conversion import localconverter
from rpy2.rinterface_lib.embedded import RRuntimeError

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

def sanitize_for_r(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    def _is_scalar(x):
        import pandas as pd
        return not isinstance(x, (list, dict, pd.Series))
    for c in df.columns:
        s = df[c]
        if not s.map(_is_scalar).all():
            df[c] = s.astype(str)
        elif s.dtype == "object":
            df[c] = df[c].astype("string")
    return df

# --------------------------
# Core domain funcs
# --------------------------
def postprocess_cba(cb_raw_df: pd.DataFrame) -> pd.DataFrame:
    parts = cb_raw_df["variable"].astype(str).str.split(":", n=4, expand=True)
    parts.columns = ["name", "sector", "cb_type", "item_1", "item_2"]
    cb_data = pd.concat([cb_raw_df, parts], axis=1)
    cb_data["value"] = cb_data["value"] / 1e9
    cb_data["Year"]  = cb_data["time_period"] + 2015

    group_cols = ["cb_type", "strategy_code", "primary_id", "future_id", "Year"]
    cb_agg = (
        cb_data.groupby(group_cols, dropna=False, as_index=False)["value"]
        .sum()
        .rename(columns={"value": "Cumulative"})
    )

    agg_cb_df = (
        cb_agg.pivot_table(
            index=["primary_id", "future_id", "strategy_code", "Year"],
            columns="cb_type",
            values="Cumulative",
            aggfunc="sum"
        )
        .reset_index()
    )
    agg_cb_df.columns.name = None
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
# Global (per-process) state for workers
# --------------------------
PROC_STATE = {
    "S3": None,
    "BUCKET": None,
    "TMP_DIR": None,
    "S3_DECOMP_PREFIX": None,
    "S3_CB_PREFIX": None,
    "CACHE_DIR": None,
    "LOCAL_FILES": {},
    "CONFIG_DIR": None,
}

def worker_init(
    profile_name: str,
    bucket_name: str,
    tmp_dir: str,
    cache_dir: str,
    s3_decomp_prefix: str,
    s3_cb_prefix: str,
    config_dir: str,
):
    """Runs once per worker process. R decomposition is done in main; workers handle CB."""
    session = boto3.Session(profile_name=profile_name)
    s3_resource = session.resource('s3')

    PROC_STATE["S3"] = s3_resource
    PROC_STATE["BUCKET"] = bucket_name
    PROC_STATE["TMP_DIR"] = tmp_dir
    PROC_STATE["S3_DECOMP_PREFIX"] = s3_decomp_prefix
    PROC_STATE["S3_CB_PREFIX"] = s3_cb_prefix
    PROC_STATE["CACHE_DIR"] = cache_dir
    PROC_STATE["CONFIG_DIR"] = config_dir

    PROC_STATE["LOCAL_FILES"] = {
        # Full decomposed output (all primary_ids, input+output already merged by main).
        "decomposed_df":          os.path.join(cache_dir, "decomposed_df.pkl"),
        "attribute_primary_df":   os.path.join(cache_dir, "attribute_primary_df.pkl"),
        "attribute_strategy_df":  os.path.join(cache_dir, "attribute_strategy_df.pkl"),
        "baseline_decomposed_df": os.path.join(cache_dir, "baseline_decomposed_df.pkl"),
    }



def run_decomposition_worker(primary_id_to_decompose: int) -> Tuple[int, Optional[str]]:
    """
    CB + Jobs for a single primary_id.
    R decomposition is done once in main(); workers receive the pre-computed
    decomposed_df (all primary_ids, input+output already merged).
    """
    try:
        s3               = PROC_STATE["S3"]
        bucket           = PROC_STATE["BUCKET"]
        tmp_dir          = PROC_STATE["TMP_DIR"]
        s3_decomp_prefix = PROC_STATE["S3_DECOMP_PREFIX"]
        s3_cb_prefix     = PROC_STATE["S3_CB_PREFIX"]

        # Load cached data
        decomposed_all        = pd.read_pickle(PROC_STATE["LOCAL_FILES"]["decomposed_df"])
        attribute_primary_df  = pd.read_pickle(PROC_STATE["LOCAL_FILES"]["attribute_primary_df"])
        attribute_strategy_df = pd.read_pickle(PROC_STATE["LOCAL_FILES"]["attribute_strategy_df"])
        base_decomposed_df    = pd.read_pickle(PROC_STATE["LOCAL_FILES"]["baseline_decomposed_df"])

        # Filter decomposed output for this primary_id
        # decomposed_all already has input+output merged — no additional merge needed.
        decomposed_df = decomposed_all[decomposed_all["primary_id"] == primary_id_to_decompose].copy()
        if decomposed_df.empty:
            return primary_id_to_decompose, f"No rows in decomposed_df for primary_id={primary_id_to_decompose}"

        if base_decomposed_df.empty:
            return primary_id_to_decompose, "Baseline data is empty in cache."

        # Upload emissions summary — columns already present in decomposed_df
        decomposed_df["total_emissions"] = (
            decomposed_df.filter(like="emission_co2e_subsector_total").sum(axis=1)
        )
        energy_demand_cols    = [c for c in decomposed_df.columns if c.startswith("energy_demand_")]
        total_value_enfu_cols = [c for c in decomposed_df.columns if c.startswith("totalvalue_enfu_fuel_consumed_inen")]
        frac_inen_energy_cols = [c for c in decomposed_df.columns if c.startswith("frac_inen_energy_")]
        efficfactor_cols      = [c for c in decomposed_df.columns if c.startswith("efficfactor_enfu_industrial_energy_fuel")]

        cols_to_keep = (
            ["primary_id", "time_period", "total_emissions"]
            + efficfactor_cols
            + energy_demand_cols
            + frac_inen_energy_cols
            + total_value_enfu_cols
        )
        df_to_upload = decomposed_df[[c for c in cols_to_keep if c in decomposed_df.columns]]
        upload_df_to_s3(df_to_upload, s3, bucket, f"{s3_decomp_prefix}emission_total_{primary_id_to_decompose}.csv")

        # --- Cost Benefits ---
        try:
            future_id   = int(attribute_primary_df.loc[attribute_primary_df["primary_id"] == primary_id_to_decompose, "future_id"].values[0])
            strategy_id = int(attribute_primary_df.loc[attribute_primary_df["primary_id"] == primary_id_to_decompose, "strategy_id"].values[0])
            strategy_code = attribute_strategy_df.loc[attribute_strategy_df["strategy_id"] == strategy_id, "strategy_code"].values[0]
        except Exception:
            return primary_id_to_decompose, f"Missing strategy/future mapping for primary_id={primary_id_to_decompose}"

        from costs_benefits_ssp.cb_calculate import CostBenefits

        # Append baseline (primary_id=0) + current run.
        # Both have input+output merged — schemas are compatible.
        ssp_data = pd.concat([base_decomposed_df, decomposed_df], ignore_index=True)
        ssp_data = ssp_data.replace(np.nan, 0.0)
        strategy_code_base = "BASE"

        cb = CostBenefits(ssp_data, attribute_primary_df, attribute_strategy_df, strategy_code_base)
        cb.ssp_data["future_id"] = 0

        cb_config_path = os.path.join(PROC_STATE["CONFIG_DIR"], "cb_config_params.xlsx")
        if not os.path.exists(cb_config_path):
            return primary_id_to_decompose, f"CB config not found: {cb_config_path}"
        cb.load_cb_parameters(cb_config_path)

        results_system = cb.compute_system_cost_for_strategy(strategy_code_tx=strategy_code)
        results_tx     = cb.compute_technical_cost_for_strategy(strategy_code_tx=strategy_code)
        results_all    = pd.concat([results_system, results_tx], ignore_index=True)
        results_all_pp = cb.cb_process_interactions(results_all)
        results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)
        results_all_pp_shifted["primary_id"] = primary_id_to_decompose
        results_all_pp_shifted["future_id"]  = future_id

        agg_cb_df = postprocess_cba(results_all_pp_shifted)
        if agg_cb_df is not None and not agg_cb_df.empty:
            upload_df_to_s3(agg_cb_df, s3, bucket, f"{s3_cb_prefix}cb_{primary_id_to_decompose}.csv")

        return primary_id_to_decompose, None

    except Exception as e:
        return primary_id_to_decompose, f"{e}\n{traceback.format_exc()}"


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
    R_SCRIPTS_DIR_PATH = os.path.join(SCRIPT_DIR_PATH, "r_scripts")


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
    R_SCRIPT_PATH             = os.path.join(R_SCRIPTS_DIR_PATH, 'intertemporal_decomposition.r')
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
    # data_all needs both input and output because the output of rescale()
    # will be the input for CB, which requires both sources.
    logger.info("Building data_all (output merged with input, all primary_ids)…")
    data_all = pd.merge(output_df, input_df, on=["primary_id", "region", "time_period"], how="left")
    data_all = pd.concat([baseline_df, data_all], ignore_index=True)
    data_all = data_all.fillna(0)
    logger.info(f"data_all shape: {data_all.shape}  |  primary_ids: {len(data_all['primary_id'].unique())}")

    # Call R rescale() once for all primary_ids
    logger.info(f"Loading R script: {R_SCRIPT_PATH}")
    ro.r['source'](R_SCRIPT_PATH)
    r_rescale = ro.globalenv['rescale']

    te_cols = ["Subsector", "Gas", "Vars", "Subsector_Category", "ssp_subsector", TARGET_COUNTRY]
    te_df = emission_targets_df[[c for c in te_cols if c in emission_targets_df.columns]].copy()
    te_df = te_df.rename(columns={TARGET_COUNTRY: "tvalue"})
    te_df = sanitize_for_r(te_df)

    data_all_r = sanitize_for_r(data_all.loc[data_all["time_period"] >= TIME_PERIOD_REF].copy())
    rall = data_all_r["region"].dropna().astype(str).unique().tolist()
    if not rall:
        raise RuntimeError("No regions found in data_all after filtering by time_period.")

    # Pre-flight check: replace zeros in emission vars at TIME_PERIOD_REF
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
        _changed = int(_mask.sum())
        data_all_r.loc[_mask, _var] = 0.01
        if _changed > 0:
            logger.info(f"Pre-flight: changed {_changed} zeros → 0.01 in '{_var}' (time_period == {TIME_PERIOD_REF})")

    with localconverter(default_converter + pandas2ri.converter):
        r_data_all = ro.conversion.py2rpy(data_all_r)
    with localconverter(default_converter + pandas2ri.converter):
        r_te_all = ro.conversion.py2rpy(te_df)

    out_dir = TMP_DIR_PATH if TMP_DIR_PATH.endswith(os.sep) else TMP_DIR_PATH + os.sep
    logger.info(f"Calling rescale() for {len(primary_ids)} primary_ids → {out_dir}")
    r_rescale(
        ro.IntVector([1]),
        ro.StrVector([str(x) for x in rall]),
        r_data_all,
        r_te_all,
        ro.StrVector(["_0"]),
        ro.StrVector([out_dir]),
        ro.IntVector([TIME_PERIOD_REF]),
    )
    logger.info("rescale() completed.")

    # Read R output (one CSV, all primary_ids, input+output preserved)
    r_output = os.path.join(TMP_DIR_PATH, f"{rall[0]}.csv")
    if not os.path.exists(r_output):
        raise FileNotFoundError(f"R output not found: {r_output}")
    decomposed_df = pd.read_csv(r_output)
    decomposed_df = decomposed_df[decomposed_df["primary_id"] != PRIMARY_ID_BASE].copy()
    logger.info(f"decomposed_df shape: {decomposed_df.shape}  |  primary_ids: {len(decomposed_df['primary_id'].unique())}")

    # Cache everything workers need
    CACHE_DIR = os.path.join(TMP_DIR_PATH, "cache")
    os.makedirs(CACHE_DIR, exist_ok=True)
    decomposed_df.to_pickle(os.path.join(CACHE_DIR, "decomposed_df.pkl"))
    attribute_primary_df.to_pickle(os.path.join(CACHE_DIR, "attribute_primary_df.pkl"))
    attribute_strategy_df.to_pickle(os.path.join(CACHE_DIR, "attribute_strategy_df.pkl"))
    baseline_df.to_pickle(os.path.join(CACHE_DIR, "baseline_decomposed_df.pkl"))
    logger.info(f"Cached: decomposed_df={decomposed_df.shape}, baseline={baseline_df.shape}")

    # Spawn-based pool (rpy2-safe)
    mp.set_start_method("spawn", force=True)

    init_args = (
        PROFILE_NAME,
        BUCKET_NAME,
        TMP_DIR_PATH,
        CACHE_DIR,
        S3_DECOMPOSED_DIR_PREFIX,
        S3_CB_DIR_PREFIX,
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

    errors = [(pid, err) for pid, err in results if err]
    if errors:
        logger.warning(f"{len(errors)} primary_id(s) failed:")
        for pid, err in errors[:10]:
            logger.warning(f"  - {pid}: {err}")
        if len(errors) > 10:
            logger.warning("  … (more errors not shown)")
    else:
        logger.info("All primary_id tasks completed successfully.")

    cleanup_tmp(TMP_DIR_PATH, keep_tmp=args.keep_tmp)

if __name__ == "__main__":
    main()
