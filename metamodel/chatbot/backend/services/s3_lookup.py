"""
S3 Lookup Service
==================
Retrieves SISEPUEDE model inputs from S3 and finds the nearest LHS trial
for a given set of group values.

Public API
----------
find_nearest_lhs_trial(group_values, design_id=3) -> int
    Return the primary_id of the LHS trial closest (Euclidean) to
    the given lever values.

get_model_inputs_row(primary_id) -> dict
    Fetch the model inputs CSV for one primary_id from S3.
    Result is cached (lru_cache, maxsize=50).

get_changed_variables(group_ids, l_values) -> dict
    High-level call: given a list of changed group IDs and their L values,
    return the raw SISEPUEDE variable values from the nearest matching trial.

Design ID rules (CLAUDE.md)
----------------------------
design_id=3  vary_l=1, vary_x=0  — use for L-only lookups
design_id=0  vary_l=0, vary_x=1  — use for X-only lookups
NEVER mix L and X variable lookups in the same row.
"""

import io
import json
import logging
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

_LOCAL_DATA_DIR = _METAMODEL_DIR / "data" / "ssp" / _S3_RUN_KEY
_LHS_CSV_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv"
_ATTR_PRIMARY_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_PRIMARY.csv"
_ATTR_STRATEGY_LOCAL = _LOCAL_DATA_DIR / "ATTRIBUTE_STRATEGY.csv"

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
    Return the L group values (groups 1–59) for the given strategy_id.

    Mechanism
    ---------
    1. Looks up strategy_id in ATTRIBUTE_PRIMARY to find (design_id, future_id).
    2. Retrieves the matching LHS row from ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.
       For design_id=0 (X-only), L values are identical across all rows in that
       design — future_id=0 is a deterministic sentinel not stored in the LHS, so
       the first available row for that design_id is used instead.
    3. Returns {group_id: l_value} for all L columns present in the LHS.

    Notes
    -----
    - Strategy 6009 (NDC_2.5) lives in design_id=0 with all L groups = 1.0,
      reflecting comprehensive maximum-ambition policy action.
    - Strategy 6004 (NZ) lives in design_id=3 (L-varying); for any specific L
      lookup you should use find_nearest_lhs_trial instead.

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

    # Columns named '1'..'59' hold the L group values.
    l_values: dict[int, float] = {}
    for gid in range(1, 60):
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
    design_id: int = 3,
) -> int:
    """
    Find the LHS trial whose lever values are closest (Euclidean) to
    the requested group_values and return its primary_id.

    Parameters
    ----------
    group_values : {group_id: x_value}
        Group IDs 1–59 mapped to values in [0, 1]. Only groups present in
        the LHS CSV columns are used for distance computation.
    design_id : int
        3 = L-only design (default for lever lookups).
        0 = X-only design (for exogenous uncertainty lookups).

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
    nearest_pos = int(np.argmin(distances))
    nearest_future_id = int(subset.iloc[nearest_pos]["future_id"])

    logger.debug(
        "Nearest LHS trial: future_id=%d  distance=%.4f  design_id=%d  "
        "cols_used=%d",
        nearest_future_id,
        float(distances[nearest_pos]),
        design_id,
        len(available_cols),
    )

    # Resolve future_id → primary_id via ATTRIBUTE_PRIMARY.
    # For design_id=3 every future_id maps to exactly one primary_id
    # (strategy_id=6004 only). For other designs, take the first match.
    match = attr_primary[
        (attr_primary["design_id"] == design_id)
        & (attr_primary["future_id"] == nearest_future_id)
    ]
    if match.empty:
        raise LookupError(
            f"ATTRIBUTE_PRIMARY has no row for "
            f"design_id={design_id}, future_id={nearest_future_id}"
        )

    return int(match.iloc[0]["primary_id"])


_S3_OUTPUT_KEY_PREFIX = "model_output"


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


# Sector codes embedded in SISEPUEDE variable names (e.g. ef_agrc_* → agrc).
# Only the codes that have a corresponding subsector_total column in outputs.
_VARIABLE_SECTOR_CODES = [
    "agrc", "ccsq", "entc", "fgtv", "frst", "inen",
    "ippu", "lndu", "lsmm", "lvst", "scoe", "soil",
    "trns", "trww", "waso",
]


def _infer_sector(variable_name: str) -> str | None:
    """Return the SISEPUEDE sector code embedded in a variable name, or None."""
    for code in _VARIABLE_SECTOR_CODES:
        if f"_{code}_" in variable_name or variable_name.startswith(code + "_"):
            return code
    return None


def get_scenario_outcomes(
    group_ids: list[int],
    l_values: dict[int, float],
) -> dict:
    """
    Return SISEPUEDE simulation output trajectories (emissions by sector) for
    the sectors affected by the requested lever groups.

    Uses the nearest LHS trial (design_id=3, L-only) to find the closest
    pre-computed simulation, then extracts emission_co2e_subsector_total_{sector}
    columns for every sector touched by the changed groups.

    Parameters
    ----------
    group_ids : list[int]
        Lever group IDs (1–59) whose sectors should be reported.
    l_values  : dict[int, float]
        Full L override dict used to find the nearest LHS trial.

    Returns
    -------
    dict with keys:
        primary_id      (int)  — matched LHS trial
        sector_emissions (dict) — {sector_code: [co2e_tp0, ..., co2e_tp55]}
                                  for each sector touched by group_ids
        sectors_by_group (dict) — {group_id: sector_code} for traceability
        design_note     (str)
    """
    with open(settings.feature_registry_path) as fh:
        registry = json.load(fh)
    lever_features = registry.get("lever_features", {})

    sectors_needed: set[str] = set()
    sectors_by_group: dict[int, str] = {}

    for gid in group_ids:
        meta = lever_features.get(str(gid))
        if meta is None:
            logger.warning("Group %d not in feature registry — skipping", gid)
            continue
        for var_name in meta.get("variables", []):
            sector = _infer_sector(var_name)
            if sector:
                sectors_needed.add(sector)
                sectors_by_group[gid] = sector
                break

    primary_id = find_nearest_lhs_trial(l_values, design_id=3)
    logger.info(
        "get_scenario_outcomes: groups=%s → primary_id=%d, sectors=%s",
        group_ids, primary_id, sorted(sectors_needed),
    )

    model_outputs = get_model_outputs_row(primary_id)

    sector_emissions: dict[str, list] = {}
    for sector in sorted(sectors_needed):
        col = f"emission_co2e_subsector_total_{sector}"
        if col in model_outputs:
            sector_emissions[sector] = model_outputs[col]
        else:
            logger.warning("Output column '%s' not found (primary_id=%d)", col, primary_id)

    return {
        "primary_id": primary_id,
        "sector_emissions": sector_emissions,
        "sectors_by_group": {gid: s for gid, s in sorted(sectors_by_group.items())},
        "design_note": "L-only lookup design_id=3. Do not mix with X variables.",
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


def get_changed_variables(
    group_ids: list[int],
    l_values: dict[int, float],
) -> dict:
    """
    Return SISEPUEDE model input variable values for the groups that changed.

    Uses the nearest LHS trial (design_id=3, L-only) to find the closest
    pre-computed simulation row, then extracts only the variables that belong
    to the requested groups.

    Parameters
    ----------
    group_ids : list[int]
        Lever group IDs (1–59) whose variables should be returned.
    l_values  : dict[int, float]
        Full L override dict {group_id: x_value} used to find the nearest
        LHS trial via Euclidean distance. Values should be in [0, 1].

    Returns
    -------
    dict with keys:
        primary_id    (int)   — matched LHS trial
        variables     (dict)  — {variable_name: [values by time_period]}
                                for all variables in the requested groups
        groups_matched (dict) — {group_id: [variable_names]} for traceability
        design_note   (str)   — advisory about design constraints

    Raises
    ------
    FileNotFoundError  if the local LHS CSV or ATTRIBUTE_PRIMARY is missing
    LookupError        if no ATTRIBUTE_PRIMARY row matches the nearest trial
    FileNotFoundError  if the S3 model input key does not exist
    """
    with open(settings.feature_registry_path) as fh:
        registry = json.load(fh)

    lever_features = registry.get("lever_features", {})

    # Resolve group_id → SISEPUEDE variable names
    group_to_vars: dict[int, list[str]] = {}
    all_target_vars: set[str] = set()

    for gid in group_ids:
        meta = lever_features.get(str(gid))
        if meta is None:
            logger.warning("Group %d not in feature registry — skipping", gid)
            continue
        vars_for_group: list[str] = meta.get("variables", [])
        group_to_vars[gid] = vars_for_group
        all_target_vars.update(vars_for_group)

    if not all_target_vars:
        logger.warning(
            "get_changed_variables: no variables resolved for groups %s", group_ids
        )

    # Find the nearest LHS trial and fetch its model inputs
    primary_id = find_nearest_lhs_trial(l_values, design_id=3)
    logger.info(
        "get_changed_variables: groups=%s → primary_id=%d", group_ids, primary_id
    )

    model_inputs = get_model_inputs_row(primary_id)

    # Extract only the variables that belong to the requested groups
    variables: dict[str, list] = {}
    for var in sorted(all_target_vars):
        if var in model_inputs:
            variables[var] = model_inputs[var]
        else:
            logger.warning(
                "Variable '%s' not found in model inputs (primary_id=%d)",
                var,
                primary_id,
            )

    return {
        "primary_id": primary_id,
        "variables": variables,
        "groups_matched": {
            gid: vars_ for gid, vars_ in sorted(group_to_vars.items())
        },
        "design_note": (
            "L-only lookup design_id=3. Do not mix with X variables."
        ),
    }
