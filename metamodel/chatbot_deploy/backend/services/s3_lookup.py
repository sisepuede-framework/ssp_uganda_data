"""
S3 Lookup Service
==================
Retrieves SISEPUEDE model inputs from S3 and finds the nearest LHS trial
for a given set of group values.

Public API
----------
find_nearest_lhs_trial(group_values, design_id=4) -> int
    Return the primary_id of the LHS trial closest (Euclidean) to
    the given lever values.

get_model_inputs_row(primary_id) -> dict
    Fetch the model inputs CSV for one primary_id from S3.
    Result is cached (lru_cache, maxsize=50).

get_scenario_variable_trajectories(group_ids, l_values) -> dict
    High-level call: given changed group IDs and their L values, return the
    trajectories of the model variables each lever moves — the input drivers
    (from model_input, all groups) plus the downstream output variables (from
    model_output, where they exist) — for the nearest matching trial.

Design ID rules (2026-05-30 run)
--------------------------------
design_id=4  the 100,001 LHS scenarios — BOTH L and X vary together (NZ strategy).
design_id=0  a single baseline/reference scenario (primary_id=0, strategy_id=0).

This run has NO L-only design (the old design_id=3). So nearest-trial lookups use
design_id=4: the match is closest by L values, but its X is also perturbed — it is
the best available pre-computed scenario, not a clean L-only counterfactual.
"""

import io
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

import boto3
import boto3.session
import numpy as np
import pandas as pd
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

_BACKEND_DIR = Path(__file__).parent.parent   # .../chatbot/backend/
_METAMODEL_DIR = _BACKEND_DIR.parent.parent   # .../metamodel/

# Normalise run_id to the S3 key format: lowercase 't', semicolons not colons.
# settings.s3_run_id may be stored as "sisepuede_run_2025-11-12T22:19:28.194097"
# but S3 (and local data/) uses "sisepuede_run_2025-11-12t22;19;28.194097".
_S3_RUN_KEY: str = settings.s3_run_id.lower().replace(":", ";")

_SSP_DIR = settings.ssp_data_dir                  # parent of the per-run dir
                                                  # (env-overridable: SSP_DATA_DIR)
_LOCAL_DATA_DIR = _SSP_DIR / _S3_RUN_KEY
_LHS_CSV_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv"
_ATTR_PRIMARY_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_PRIMARY.csv"
_ATTR_STRATEGY_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_STRATEGY.csv"

# transformation → model-variable maps (which variable_field columns each lever
# moves). Input drivers (read from model_input) and downstream outputs (read from
# model_output). VARIABLE_TRAJECTORY_GROUPS_L is the input fallback keyed directly
# by integer group, guaranteeing all 54 lever groups resolve to ≥1 driver.
_INPUT_VAR_MAP_CSV = _SSP_DIR / "transformation_variable_map.csv"
_OUTPUT_VAR_MAP_CSV = _SSP_DIR / "transformation_output_variable_map.csv"
_VTL_CSV_LOCAL = _LOCAL_DATA_DIR / "VARIABLE_TRAJECTORY_GROUPS_L.csv"

# Pre-built index: primary_id (str) → S3 directory number (int).
# Generated from the Athena query and stored as a static file.
# Each model_input_{n}/data.csv in S3 contains data for multiple primary_ids
# (one batch per directory). This index tells us which directory to fetch,
# after which we filter the CSV to the exact primary_id row.
_S3_DIR_INDEX_PATH = _BACKEND_DIR / "s3_model_input_index.json"


# ── S3 client (lazy singleton) ────────────────────────────────────────────────

_s3_client = None


def _get_s3():
    """Return a boto3 S3 client.

    Priority order:
      1. Explicit key/secret from settings (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
      2. Named profile from settings.aws_profile (e.g. "alexa" for SSO)
      3. Default boto3 credential chain (env vars, ~/.aws/credentials, instance role)
    """
    global _s3_client
    if _s3_client is None:
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            session = boto3.session.Session(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_default_region,
            )
        elif settings.aws_profile:
            session = boto3.session.Session(
                profile_name=settings.aws_profile,
                region_name=settings.aws_default_region,
            )
        else:
            session = boto3.session.Session(region_name=settings.aws_default_region)

        _s3_client = session.client("s3")
        logger.info(
            "S3 client initialised (region=%s, profile=%s)",
            settings.aws_default_region,
            settings.aws_profile or "default",
        )
    return _s3_client


# ── LHS data (module-level lazy cache) ────────────────────────────────────────

_lhs_df: pd.DataFrame | None = None
_attr_primary_df: pd.DataFrame | None = None
_attr_strategy_df: pd.DataFrame | None = None
_s3_dir_index: dict[str, int] | None = None


def _load_s3_dir_index() -> dict[str, int]:
    """Load the primary_id → S3 directory_n index (lazy, cached)."""
    global _s3_dir_index
    if _s3_dir_index is None:
        if not _S3_DIR_INDEX_PATH.exists():
            raise FileNotFoundError(
                f"S3 directory index not found at {_S3_DIR_INDEX_PATH}. "
                "Run the Athena query to generate d0d0eb18-*.csv, then convert "
                "it to s3_model_input_index.json."
            )
        with open(_S3_DIR_INDEX_PATH) as fh:
            _s3_dir_index = json.load(fh)
        logger.info("Loaded S3 directory index: %d entries", len(_s3_dir_index))
    return _s3_dir_index


def _load_lhs_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load LHS lever-effects CSV and ATTRIBUTE_PRIMARY from local disk.

    Both files are read once and cached for the lifetime of the process.
    They are small (~350 KB combined) so keeping them in memory is fine.
    """
    global _lhs_df, _attr_primary_df

    if _lhs_df is None:
        if not _LHS_CSV_LOCAL.exists():
            raise FileNotFoundError(
                f"LHS CSV not found at {_LHS_CSV_LOCAL}. "
                "Ensure the data/ssp/ directory is populated from the run transfers."
            )
        _lhs_df = pd.read_csv(_LHS_CSV_LOCAL)
        logger.info(
            "Loaded ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS: %d rows, %d cols",
            len(_lhs_df),
            len(_lhs_df.columns),
        )

    if _attr_primary_df is None:
        if not _ATTR_PRIMARY_LOCAL.exists():
            raise FileNotFoundError(
                f"ATTRIBUTE_PRIMARY not found at {_ATTR_PRIMARY_LOCAL}."
            )
        _attr_primary_df = pd.read_csv(_ATTR_PRIMARY_LOCAL)
        logger.info("Loaded ATTRIBUTE_PRIMARY: %d rows", len(_attr_primary_df))

    return _lhs_df, _attr_primary_df


def _load_strategy_data() -> pd.DataFrame:
    """Load ATTRIBUTE_STRATEGY.csv from local disk (lazy, cached)."""
    global _attr_strategy_df
    if _attr_strategy_df is None:
        if not _ATTR_STRATEGY_LOCAL.exists():
            raise FileNotFoundError(
                f"ATTRIBUTE_STRATEGY.csv not found at {_ATTR_STRATEGY_LOCAL}."
            )
        _attr_strategy_df = pd.read_csv(_ATTR_STRATEGY_LOCAL)
        logger.info("Loaded ATTRIBUTE_STRATEGY: %d rows", len(_attr_strategy_df))
    return _attr_strategy_df


# ── Public functions ──────────────────────────────────────────────────────────


def list_strategies() -> list[dict]:
    """
    Return all strategies from ATTRIBUTE_STRATEGY.csv as a list of dicts.

    Each dict has:
        strategy_id   (int)  — numeric ID used in ATTRIBUTE_PRIMARY
        strategy_code (str)  — short code, e.g. "PFLO:NDC_2_2025_TUNED"
        description   (str)  — human-readable name from the 'strategy' column
    """
    df = _load_strategy_data()
    result = []
    for _, row in df.iterrows():
        # The 'strategy' column is the human-readable name; 'description' is often empty.
        desc = str(row.get("strategy", "")) or str(row.get("description", ""))
        result.append({
            "strategy_id": int(row["strategy_id"]),
            "strategy_code": str(row["strategy_code"]),
            "description": desc,
        })
    return result


def get_strategy_l_values(strategy_id: int) -> dict[int, float]:
    """
    Return the L group values (groups 1–54) for the given strategy_id.

    Mechanism
    ---------
    1. Looks up strategy_id in ATTRIBUTE_PRIMARY to find (design_id, future_id).
    2. Retrieves the matching LHS row from ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.
       For the baseline design (no per-future variation), the first available row
       for that design_id is used instead.
    3. Returns {group_id: l_value} for all L columns present in the LHS.

    Notes
    -----
    - This run defines only two strategies: 0 (baseline, design_id=0) and
      6007 (Net Zero, design_id=4 where L and X vary).

    Raises
    ------
    LookupError  if strategy_id is not in ATTRIBUTE_PRIMARY
    LookupError  if no LHS rows exist for the resolved design_id
    """
    lhs_df, attr_primary = _load_lhs_data()

    match = attr_primary[attr_primary["strategy_id"] == strategy_id]
    if match.empty:
        raise LookupError(
            f"strategy_id={strategy_id} not found in ATTRIBUTE_PRIMARY."
        )

    row = match.iloc[0]
    design_id = int(row["design_id"])
    future_id = int(row["future_id"])

    lhs_subset = lhs_df[lhs_df["design_id"] == design_id]
    if lhs_subset.empty:
        raise LookupError(
            f"No LHS rows found for design_id={design_id} "
            f"(from strategy_id={strategy_id})."
        )

    # Exact match first; fall back to first row in the design when future_id is
    # a deterministic sentinel (e.g. 0) that doesn't appear in the LHS.
    lhs_exact = lhs_subset[lhs_subset["future_id"] == future_id]
    if lhs_exact.empty:
        logger.warning(
            "future_id=%d not in LHS for design_id=%d (strategy_id=%d); "
            "using first available row — L values are constant for this design.",
            future_id, design_id, strategy_id,
        )
        lhs_row = lhs_subset.iloc[0]
    else:
        lhs_row = lhs_exact.iloc[0]

    # Columns named '1'..'54' hold the L group values.
    l_values: dict[int, float] = {}
    for gid in range(1, 55):
        col = str(gid)
        if col in lhs_row.index:
            l_values[gid] = float(lhs_row[col])

    logger.info(
        "get_strategy_l_values: strategy_id=%d → design_id=%d, %d L groups loaded",
        strategy_id, design_id, len(l_values),
    )
    return l_values


def find_nearest_lhs_trial(
    group_values: dict[int, float],
    design_id: int = 4,
) -> int:
    """
    Find the LHS trial whose lever values are closest (Euclidean) to
    the requested group_values and return its primary_id.

    Parameters
    ----------
    group_values : {group_id: x_value}
        Group IDs 1–54 mapped to values in [0, 1]. Only groups present in
        the LHS CSV columns are used for distance computation.
    design_id : int
        4 = the LHS design where L (and X) vary (default; this run's only
        varying design). 0 = the single baseline scenario.

    Returns
    -------
    int
        primary_id from ATTRIBUTE_PRIMARY for the nearest matching row.
    """
    lhs_df, attr_primary = _load_lhs_data()

    subset = lhs_df[lhs_df["design_id"] == design_id]
    if subset.empty:
        raise ValueError(f"No LHS rows found for design_id={design_id}")

    # CSV group columns are strings ("1", "2", ...). Convert keys accordingly.
    query_cols = {str(k): float(v) for k, v in group_values.items()}
    available_cols = [c for c in query_cols if c in subset.columns]

    if not available_cols:
        raise ValueError(
            f"None of the requested group_ids {sorted(group_values)} "
            "appear as columns in the LHS CSV."
        )

    query_vec = np.array([query_cols[c] for c in available_cols])
    candidate_matrix = subset[available_cols].to_numpy(dtype=float)
    distances = np.sqrt(((candidate_matrix - query_vec) ** 2).sum(axis=1))

    # ~0.2% of scenarios failed to simulate and have no S3 output. Walk candidates
    # nearest-first and return the first whose primary_id was actually simulated
    # (present in the directory index). Fall back to the absolute nearest if the
    # index is unavailable, so this still works without it.
    try:
        sim_index = _load_s3_dir_index()
    except FileNotFoundError:
        sim_index = None

    ap_design = attr_primary[attr_primary["design_id"] == design_id]
    fut_to_pid = dict(zip(ap_design["future_id"], ap_design["primary_id"]))

    fallback_pid = None
    for pos in np.argsort(distances):
        fut = int(subset.iloc[int(pos)]["future_id"])
        pid = fut_to_pid.get(fut)
        if pid is None:
            continue
        pid = int(pid)
        if fallback_pid is None:
            fallback_pid = pid
        if sim_index is None or str(pid) in sim_index:
            logger.debug("Nearest simulated trial: future_id=%d primary_id=%d "
                         "distance=%.4f design_id=%d", fut, pid, float(distances[pos]), design_id)
            return pid

    if fallback_pid is not None:
        return fallback_pid
    raise LookupError(f"No ATTRIBUTE_PRIMARY rows for design_id={design_id}")


@lru_cache(maxsize=50)
def get_model_outputs_row(primary_id: int) -> dict:
    """
    Fetch the SISEPUEDE model outputs for one primary_id from S3.

    Mirrors get_model_inputs_row but reads from the model_output prefix.
    The same s3_model_input_index.json maps primary_id → directory_n for both
    inputs and outputs (verified: identical primary_id sets, identical batching).

    Returns {column_name: [value_tp0, ..., value_tp55]}.
    Results are cached (LRU, maxsize=50). Do not mutate the returned dict.
    """
    index = _load_s3_dir_index()
    directory_n = index.get(str(primary_id))
    if directory_n is None:
        raise KeyError(
            f"primary_id={primary_id} not found in S3 directory index."
        )

    key = (
        f"run_database/{_S3_RUN_KEY}"
        f"/model_output/region=uganda/model_output_{directory_n}/data.csv"
    )
    s3 = _get_s3()
    logger.info(
        "S3 GET model_output_%d (primary_id=%d): s3://%s/%s",
        directory_n, primary_id, settings.s3_bucket, key,
    )

    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            raise FileNotFoundError(
                f"Model output directory not found in S3 (directory_n={directory_n}). "
                f"Key: {key}"
            ) from exc
        raise

    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    df = df[df["primary_id"] == primary_id]

    if df.empty:
        raise LookupError(
            f"primary_id={primary_id} not found in model_output_{directory_n}/data.csv"
        )

    if "time_period" in df.columns:
        df = df.sort_values("time_period").reset_index(drop=True)

    return df.to_dict(orient="list")


# ── Transformation → variable maps (the "how": which variables each lever moves) ──

@lru_cache(maxsize=1)
def _load_variable_maps() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the input-driver and downstream-output transformation→variable maps.
    Both have columns: transformation_code, variable, variable_field."""
    input_map = pd.read_csv(_INPUT_VAR_MAP_CSV)
    output_map = pd.read_csv(_OUTPUT_VAR_MAP_CSV)
    logger.info(
        "Loaded variable maps: %d input rows, %d output rows",
        len(input_map), len(output_map),
    )
    return input_map, output_map


@lru_cache(maxsize=1)
def _load_vtl() -> pd.DataFrame:
    """VARIABLE_TRAJECTORY_GROUPS_L.csv — input drivers keyed directly by integer
    variable_trajectory_group. Used as the input fallback (covers all 54 groups)."""
    return pd.read_csv(_VTL_CSV_LOCAL)


def _normalize_tcode(code: str) -> str:
    """Strip the strategy suffix so a registry transformation_code
    (TX:AGRC:DEC_CH4_RICE_STRATEGY_NZ) matches the maps' base code
    (TX:AGRC:DEC_CH4_RICE)."""
    return re.sub(r"(_STRATEGY)?(_NZ)?$", "", code or "")


def _dedup_field_pairs(fields, variables) -> list[tuple[str, str]]:
    """Zip parallel field/variable columns into ordered, de-duplicated
    (variable_field, display_name) pairs, dropping blanks/NaN."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for field, var in zip(fields, variables):
        f = str(field)
        if f and f.lower() != "nan" and f not in seen:
            seen.add(f)
            out.append((f, str(var)))
    return out


def _input_fields_for_group(gid: int, lever_features: dict) -> list[tuple[str, str]]:
    """Input driver (variable_field, display_name) pairs for a lever group.
    Falls back to VARIABLE_TRAJECTORY_GROUPS_L (by group id) so all 54 resolve."""
    input_map, _ = _load_variable_maps()
    meta = lever_features.get(str(gid)) or {}
    base = _normalize_tcode(meta.get("transformation_code", ""))
    rows = input_map[input_map["transformation_code"] == base]
    pairs = _dedup_field_pairs(rows["variable_field"], rows["variable"])
    if pairs:
        return pairs
    # Fallback: VARIABLE_TRAJECTORY_GROUPS_L keyed by integer group.
    vtl = _load_vtl()
    vrows = vtl[vtl["variable_trajectory_group"] == gid]
    return _dedup_field_pairs(vrows["variable_field"], vrows["variable"])


def _output_fields_for_group(gid: int, lever_features: dict) -> list[tuple[str, str]]:
    """Downstream output (variable_field, display_name) pairs for a lever group.
    Empty for the ~10 groups with no mapped outputs (no fallback)."""
    _, output_map = _load_variable_maps()
    meta = lever_features.get(str(gid)) or {}
    base = _normalize_tcode(meta.get("transformation_code", ""))
    rows = output_map[output_map["transformation_code"] == base]
    return _dedup_field_pairs(rows["variable_field"], rows["variable"])


# Time-period → year: year = 2015 + time_period. Outputs are predictions from 2019 on.
_INPUT_ANCHORS = [(0, 2015), (15, 2030), (35, 2050), (55, 2070)]
_OUTPUT_ANCHORS = [(4, 2019), (15, 2030), (35, 2050), (55, 2070)]


def _summarize_field(values: list, anchors: list[tuple[int, int]]) -> dict | None:
    """Given a full tp0..tp55 trajectory, return {year: value} at the anchor time
    periods plus pct_change (last vs first anchor). None if unusable."""
    if not values:
        return None
    n = len(values)
    series: dict[int, float] = {}
    for tp, year in anchors:
        idx = tp if tp >= 0 else n + tp
        if 0 <= idx < n:
            try:
                series[year] = round(float(values[idx]), 4)
            except (TypeError, ValueError):
                return None
    if len(series) < 2:
        return None
    first = series[anchors[0][1]]
    last = series[anchors[-1][1]]
    pct = round((last - first) / abs(first) * 100.0, 1) if first not in (0, 0.0) else None
    return {"by_year": series, "pct_change": pct}


def _collect_trajectories(
    fields: list[tuple[str, str]],
    row: dict,
    anchors: list[tuple[int, int]],
    top_n: int,
) -> tuple[list[dict], int]:
    """Summarize the fields present in `row`, sort by |pct_change|, and return
    (top_n records, total matched count)."""
    recs: list[dict] = []
    for field, name in fields:
        summ = _summarize_field(row.get(field), anchors)
        if summ is None:
            continue
        recs.append({
            "field": field,
            "name": name,
            "by_year": summ["by_year"],
            "pct_change": summ["pct_change"],
        })
    recs.sort(
        key=lambda r: abs(r["pct_change"]) if r["pct_change"] is not None else -1.0,
        reverse=True,
    )
    return recs[:top_n], len(recs)


def get_scenario_variable_trajectories(
    group_ids: list[int],
    l_values: dict[int, float],
    top_n: int = 6,
) -> dict:
    """
    For each changed lever group, return the trajectories of the model variables
    that transformation moves:
      - input drivers      (from model_input; all 54 groups; anchored 2015→2070)
      - downstream outputs (from model_output; the 44 groups that have them; 2019→2070)

    Uses the nearest LHS trial (design_id=4; L and X vary) to pick the closest
    pre-computed scenario, then reads its input and output rows from S3.

    Returns
    -------
    dict:
        primary_id (int)
        groups (dict) — {group_id: {
            display_name, transformation_code,
            inputs:  [ {field, name, by_year, pct_change}, ... ]  (≤ top_n),
            outputs: [ ... ]  (≤ top_n, may be empty),
            counts: {inputs, outputs},
            has_outputs (bool),
        }}
        design_note (str)
    """
    with open(settings.feature_registry_path) as fh:
        lever_features = json.load(fh).get("lever_features", {})

    primary_id = find_nearest_lhs_trial(l_values, design_id=4)
    inputs_row = get_model_inputs_row(primary_id)
    outputs_row = get_model_outputs_row(primary_id)

    groups: dict[int, dict] = {}
    for gid in group_ids:
        meta = lever_features.get(str(gid)) or {}
        in_fields = _input_fields_for_group(gid, lever_features)
        out_fields = _output_fields_for_group(gid, lever_features)
        in_recs, in_total = _collect_trajectories(in_fields, inputs_row, _INPUT_ANCHORS, top_n)
        out_recs, out_total = _collect_trajectories(out_fields, outputs_row, _OUTPUT_ANCHORS, top_n)
        groups[gid] = {
            "display_name": meta.get("display_name", f"Group {gid}"),
            "transformation_code": meta.get("transformation_code", ""),
            "inputs": in_recs,
            "outputs": out_recs,
            "counts": {"inputs": in_total, "outputs": out_total},
            "has_outputs": out_total > 0,
        }

    logger.info(
        "get_scenario_variable_trajectories: groups=%s → primary_id=%d",
        group_ids, primary_id,
    )
    return {
        "primary_id": primary_id,
        "groups": groups,
        "design_note": "Nearest match in design_id=4 (L and X both vary); not a clean L-only counterfactual.",
    }


@lru_cache(maxsize=50)
def get_model_inputs_row(primary_id: int) -> dict:
    """
    Fetch the SISEPUEDE model inputs for one primary_id from S3.

    S3 layout
    ---------
    Each model_input_{n}/data.csv contains data for a batch of primary_ids
    (typically 4–6 per file). This function looks up the correct directory_n
    from the pre-built index, fetches the batch file, and filters to the
    requested primary_id.

    The CSV has one row per time period (tp 0–55, years 2015–2070).
    The returned dict maps column_name → list of values ordered by time_period.

    Results are cached (LRU, maxsize=50) to avoid redundant S3 reads.
    Do not mutate the returned dict — it is shared with the cache.

    Parameters
    ----------
    primary_id : int

    Returns
    -------
    dict : {column_name: [value_tp0, value_tp1, ..., value_tp55]}
    """
    index = _load_s3_dir_index()
    directory_n = index.get(str(primary_id))
    if directory_n is None:
        raise KeyError(
            f"primary_id={primary_id} not found in S3 directory index. "
            "Only primary_ids present in s3_model_input_index.json are fetchable."
        )

    key = (
        f"run_database/{_S3_RUN_KEY}"
        f"/model_input/region=uganda/model_input_{directory_n}/data.csv"
    )
    s3 = _get_s3()
    logger.info(
        "S3 GET model_input_%d (primary_id=%d): s3://%s/%s",
        directory_n, primary_id, settings.s3_bucket, key,
    )

    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            raise FileNotFoundError(
                f"Model input directory not found in S3 (directory_n={directory_n}). "
                f"Key: {key}"
            ) from exc
        raise

    df = pd.read_csv(io.BytesIO(obj["Body"].read()))

    # Filter to the requested primary_id (batch files contain multiple)
    df = df[df["primary_id"] == primary_id]

    if df.empty:
        raise LookupError(
            f"primary_id={primary_id} not found in model_input_{directory_n}/data.csv "
            "despite being in the directory index. Index may be stale."
        )

    if "time_period" in df.columns:
        df = df.sort_values("time_period").reset_index(drop=True)

    return df.to_dict(orient="list")
