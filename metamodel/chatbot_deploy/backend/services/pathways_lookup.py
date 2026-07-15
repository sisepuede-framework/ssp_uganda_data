"""
Pre-run Pathways Lookup Service
================================
Serves REAL SISEPUEDE run data for Uganda's 6 officially named pathways, as an
accurate alternative to the XGBoost surrogate (`predictor.py`).

Why this exists
---------------
The surrogate estimates un-run scenarios well near BAU (±5%), but it was trained
only on the independent random LHS and cannot reproduce the coordinated
high-ambition pathways: for HBLE / Candidate NDC3 it predicts ~115 MtCO₂e @2070
where the real run is 6.4. For the 6 named pathways a real pre-run already
exists, so we read it straight from the curated `pathways/` CSVs instead of
predicting. The surrogate stays for custom "what-if" exploration only.

This module mirrors `predict()` / `predict_comparison()` output shapes exactly, so
the same `SimulationResponse` schema, `agent._build_result_summary`, and the two
frontend charts work unchanged — they never learn whether the data came from the
surrogate or a real run.

Public API
----------
resolve_pathway(name_or_id)        -> (display_name, meta)
get_pathway_emissions(pid)         -> {sector: {year: MtCO₂e}}
get_pathway_cost_benefit(pid)      -> {year: {benefits, costs, gdp, ...}}
build_reference_bundle()           -> {"bau": series, "hble": series}  (real BAU + HBLE)
compare_series(scenario, baseline) -> {comparison, sector_deltas, cost_benefit_deltas}
build_pathway_comparison(name_or_id) -> predict_comparison()-shaped bundle + references
get_pathway_driver_variables(name, group_ids) -> {primary_id, groups, design_note}

Data sources (curated, under the run dir's `pathways/` subfolder)
-----------------------------------------------------------------
uganda_pathways.csv        WIDE — one row per (primary_id, time_period 4..55).
                           15 emission_co2e_subsector_total_<sector> cols + drivers
                           + gdp_mmm_usd. Emissions read by anchor time_period.
cba_data_air_pollution.csv LONG — one row per (primary_id, Year, cb_type, item).
                           Sum `value` per cb_type. Costs are the 3 *_cost types,
                           passed through AS-IS (mixed sign — do NOT re-negate;
                           matches the surrogate/training convention). BAU(0) is
                           absent (values are diffs vs baseline → BAU c-b ≡ 0).
"""

import io
import logging
from functools import lru_cache

import pandas as pd
from botocore.exceptions import ClientError

from backend.config import settings
from backend.services import s3_lookup, sector_crosswalk
from backend.services.predictor import (
    COST_BENEFIT_LABELS,
    EMISSION_UNIT,
    SECTOR_DISPLAY_NAMES,
)

logger = logging.getLogger(__name__)

# ── Registry: the 6 officially named pathways ─────────────────────────────────
# display_name → real run identity. primary_id is the join key into both CSVs;
# strategy_id is the SISEPUEDE strategy (design_id=0). aliases are extra spellings
# the agent/user might use. is_baseline marks BAU (no strategy, zero cost-benefit).
PATHWAY_REGISTRY: dict[str, dict] = {
    "BAU": {
        "primary_id": 0, "strategy_id": 0, "is_baseline": True,
        "strategy_code": "BASE",
        "aliases": ["business as usual", "baseline", "bau", "no policy", "reference"],
    },
    "NDC 2.0": {
        "primary_id": 1001, "strategy_id": 6003, "is_baseline": False,
        "strategy_code": "PFLO:NDC_2",
        "aliases": ["ndc2", "ndc 2", "ndc2.0", "ndc 2.0", "pflo:ndc_2"],
    },
    "NDC 2.5": {
        "primary_id": 2002, "strategy_id": 6004, "is_baseline": False,
        "strategy_code": "PFLO:NDC_25",
        "aliases": ["ndc2.5", "ndc 2.5", "ndc25", "pflo:ndc_25"],
    },
    "NDC2 Unconditional": {
        "primary_id": 3003, "strategy_id": 6005, "is_baseline": False,
        "strategy_code": "PFLO:NDC_25_UNCONDITIONAL",
        "aliases": ["ndc2 unconditional", "ndc 2.5 unconditional",
                    "unconditional", "pflo:ndc_25_unconditional"],
    },
    "NDC2 Unconditional (Alt)": {
        "primary_id": 4004, "strategy_id": 6006, "is_baseline": False,
        "strategy_code": "PFLO:NDC_25_UNCONDITIONAL_CE",
        "aliases": ["ndc2 unconditional alt", "unconditional alt",
                    "unconditional ce", "pflo:ndc_25_unconditional_ce"],
    },
    "Candidate NDC3": {
        "primary_id": 5005, "strategy_id": 6007, "is_baseline": False,
        "strategy_code": "PFLO:HBLE",
        "aliases": ["candidate ndc3", "ndc3", "ndc 3", "hble",
                    "high ble", "net zero", "netzero", "nz", "pflo:hble"],
    },
}

BAU_PID: int = 0
HBLE_PID: int = 5005

# Emission anchors: (time_period, year); year = 2015 + time_period. 2019 (tp4) is
# the shared historical anchor both pathways share pre-divergence. 2060 (tp45) is
# included so real pathways line up with the surrogate's 6 reported years.
EMISSION_ANCHORS: list[tuple[int, int]] = [
    (4, 2019), (10, 2025), (20, 2035), (25, 2040), (35, 2050), (45, 2060), (55, 2070),
]
EMISSION_YEARS: list[int] = [y for _, y in EMISSION_ANCHORS]

# Cost-benefit years — match predictor.COST_BENEFIT_YEARS and the frontend default.
CB_YEARS: list[int] = [2025, 2035, 2040, 2050, 2070]

# The 3 cost cb_types in the LONG file. Everything else is a benefit. `technical_savings`
# is a BENEFIT that shares the `technical` prefix — membership is EXACT, never substring.
COST_CB_TYPES: set[str] = {"technical_cost", "system_cost", "fuel_cost"}
# Strip `_cost` so keys match the surrogate/frontend cost keys (technical/system/fuel).
_COST_KEY_MAP: dict[str, str] = {c: c[: -len("_cost")] for c in COST_CB_TYPES}

# Real pathways are re-aggregated into the 23 official inventory categories from
# their granular `emission_co2e_*` fields — the SAME crosswalk the surrogate trains
# on — so both flows label sectors identically (no per-source relabel hack needed).
# This is what fixed the old mismatch where uganda_pathways.csv's raw `entc` column
# held "Forest Land - Removals" (Uganda's ~62 Mt biomass energy) while the surrogate
# put that carbon elsewhere.

# Where the curated pathways CSVs live (local-first, S3 fallback).
_PATHWAYS_LOCAL_DIR = s3_lookup._LOCAL_DATA_DIR / "pathways"
_PATHWAYS_CSV = "uganda_pathways.csv"
_CBA_CSV = "cba_data_air_pollution.csv"
_LEVERS_CSV = "tableau_levers_table.csv"


# ── CSV loaders (local-first, then S3) ────────────────────────────────────────

def _read_curated_csv(filename: str) -> pd.DataFrame:
    """Read a curated pathways CSV: local disk first, then S3 as a fallback.

    Mirrors s3_lookup's BytesIO→read_csv idiom. The S3 key prefix for these
    curated files is NOT yet confirmed with the run producers; until it is, a
    missing local file raises a clear FileNotFoundError rather than silently
    falling back to the surrogate.
    """
    local = _PATHWAYS_LOCAL_DIR / filename
    if local.exists():
        return pd.read_csv(local)

    # S3 fallback (key prefix provisional — see Component 5 of the plan).
    key = f"run_database/{s3_lookup._S3_RUN_KEY}/pathways/{filename}"
    try:
        s3 = s3_lookup._get_s3()
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        logger.info("Loaded curated pathways CSV from S3: s3://%s/%s",
                    settings.s3_bucket, key)
        return pd.read_csv(io.BytesIO(obj["Body"].read()))
    except (ClientError, FileNotFoundError) as exc:
        raise FileNotFoundError(
            f"Curated pathway file '{filename}' not found locally at {local} "
            f"nor in S3 at s3://{settings.s3_bucket}/{key}. Confirm the S3 key "
            "for the curated pathways/ files with the run producers, or populate "
            "the local data dir from the run transfers."
        ) from exc


@lru_cache(maxsize=1)
def _load_pathways_df() -> pd.DataFrame:
    """WIDE uganda_pathways.csv — read once, cached (4000+ cols, all 6 pids)."""
    df = _read_curated_csv(_PATHWAYS_CSV)
    logger.info("Loaded uganda_pathways.csv: %d rows, %d cols", len(df), len(df.columns))
    return df


@lru_cache(maxsize=1)
def _load_cba_df() -> pd.DataFrame:
    """LONG cba_data_air_pollution.csv — read once, cached."""
    df = _read_curated_csv(_CBA_CSV)
    logger.info("Loaded cba_data_air_pollution.csv: %d rows", len(df))
    return df


# ── Resolution ────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def resolve_pathway(name_or_id) -> tuple[str, dict]:
    """Resolve a display name / alias / primary_id to (display_name, meta).

    Raises LookupError (listing the valid names) if nothing matches.
    """
    # Numeric primary_id?
    try:
        pid = int(name_or_id)
        for name, meta in PATHWAY_REGISTRY.items():
            if meta["primary_id"] == pid:
                return name, meta
    except (TypeError, ValueError):
        pass

    q = _norm(name_or_id)
    for name, meta in PATHWAY_REGISTRY.items():
        if q == _norm(name) or q in {_norm(a) for a in meta["aliases"]}:
            return name, meta

    raise LookupError(
        f"'{name_or_id}' is not a named pathway. Valid pathways: "
        + ", ".join(PATHWAY_REGISTRY.keys())
    )


# ── Emissions ─────────────────────────────────────────────────────────────────

def get_pathway_emissions(pid: int) -> dict[str, dict[int, float]]:
    """Per-category emissions at the anchor years for one primary_id.

    Returns {category_slug: {year: MtCO₂e}}, re-aggregating the granular
    `emission_co2e_*` fields into the 23 official inventory categories via the
    crosswalk (same as the surrogate). Indexed by `time_period` (NOT row position —
    the file starts at tp4). Sequestration categories stay negative (carbon sinks).
    """
    df = _load_pathways_df()
    sub = df[df["primary_id"] == pid]
    if sub.empty:
        raise LookupError(f"primary_id={pid} not present in {_PATHWAYS_CSV}")

    # One row per time_period → a dict getter over its granular fields.
    row_by_tp = {int(tp): row for tp, row in zip(sub["time_period"], sub.to_dict("records"))}

    trajectories: dict[str, dict[int, float]] = {slug: {} for slug in sector_crosswalk.CATEGORIES}
    for tp, year in EMISSION_ANCHORS:
        row = row_by_tp.get(tp)
        if row is None:
            continue
        cats = sector_crosswalk.categories_from_fields(row.get)  # NaN-safe, COALESCE-like
        for slug, val in cats.items():
            trajectories[slug][year] = round(float(val), 3)
    return trajectories


def _pathway_gdp_by_year(pid: int) -> dict[int, float]:
    """GDP (billion USD) at the CB anchor years, from uganda_pathways.csv.

    Read straight from the `gdp_mmm_usd` column (it IS present — no derivation).
    """
    df = _load_pathways_df()
    sub = df[df["primary_id"] == pid]
    if sub.empty or "gdp_mmm_usd" not in sub.columns:
        return {}
    by_tp = dict(zip(sub["time_period"], sub["gdp_mmm_usd"]))
    out: dict[int, float] = {}
    for year in CB_YEARS:
        tp = year - 2015
        if tp in by_tp and pd.notna(by_tp[tp]):
            out[year] = round(float(by_tp[tp]), 4)
    return out


# ── Cost / benefit ────────────────────────────────────────────────────────────

def get_pathway_cost_benefit(pid: int) -> dict[int, dict]:
    """Per-year cost/benefit block for one primary_id, shaped like predict()['cost_benefit'].

    {year: {benefits:{type:val}, costs:{type:val}, gdp, total_benefit,
            total_cost, net, cost_pct_gdp, benefit_pct_gdp}}

    Costs are the 3 *_cost cb_types summed and passed through AS-IS (mixed sign;
    not re-negated). BAU(0) is absent from the source (diffs vs baseline) → an
    all-zero block, GDP still filled from uganda_pathways.csv.
    """
    gdp_by_year = _pathway_gdp_by_year(pid)

    # BAU baseline: cost-benefit is measured as a difference vs baseline, so it is
    # identically zero for BAU itself.
    if pid == BAU_PID:
        return {
            year: {
                "benefits": {}, "costs": {},
                "gdp": gdp_by_year.get(year, 0.0),
                "total_benefit": 0.0, "total_cost": 0.0, "net": 0.0,
                "cost_pct_gdp": 0.0, "benefit_pct_gdp": 0.0,
            }
            for year in CB_YEARS
        }

    cba = _load_cba_df()
    sub = cba[(cba["primary_id"] == pid) & (cba["Year"].isin(CB_YEARS))]
    if sub.empty:
        raise LookupError(f"primary_id={pid} has no rows in {_CBA_CSV}")

    # Sum the disaggregated line-items to a single value per (year, cb_type).
    grouped = sub.groupby(["Year", "cb_type"])["value"].sum()

    cost_benefit: dict[int, dict] = {}
    for year in CB_YEARS:
        benefits: dict[str, float] = {}
        costs: dict[str, float] = {}
        if year in grouped.index.get_level_values("Year"):
            for cb_type, val in grouped.loc[year].items():
                v = round(float(val), 4)
                if cb_type in COST_CB_TYPES:
                    costs[_COST_KEY_MAP[cb_type]] = v      # pass through as-is
                else:
                    benefits[cb_type] = v
        total_b = round(sum(benefits.values()), 4)
        total_c = round(sum(costs.values()), 4)
        gdp = gdp_by_year.get(year, 0.0)
        cost_benefit[year] = {
            "benefits": benefits,
            "costs": costs,
            "gdp": gdp,
            "total_benefit": total_b,
            "total_cost": total_c,
            "net": round(total_b + total_c, 4),
            "cost_pct_gdp": round(100 * abs(total_c) / gdp, 4) if gdp else 0.0,
            "benefit_pct_gdp": round(100 * total_b / gdp, 4) if gdp else 0.0,
        }
    return cost_benefit


# ── predict()-shaped series ───────────────────────────────────────────────────

def _build_series(pid: int, name: str) -> dict:
    """Assemble one pathway into a `predict()`-shaped dict so the schema, the agent
    summary, and both charts consume it exactly like a surrogate result."""
    sector_trajectories = get_pathway_emissions(pid)
    cost_benefit = get_pathway_cost_benefit(pid)

    # Derived economy-wide headline totals per anchor year = sum over sectors.
    predictions: dict[str, dict] = {}
    for year in EMISSION_YEARS:
        total = sum(traj.get(year, 0.0) for traj in sector_trajectories.values())
        predictions[f"emission_total_yr{year}"] = {
            "value": round(total, 3),
            "unit": EMISSION_UNIT,
            "display_name": f"Total Net Emissions ({year})",
        }

    return {
        "scenario_name": name,
        "feature_vector": {},      # real run — no surrogate feature vector
        "group_values": {},        # real run — no synthetic lever settings
        "predictions": predictions,
        "sector_trajectories": sector_trajectories,
        "cost_benefit": cost_benefit,
    }


@lru_cache(maxsize=1)
def build_reference_bundle() -> dict:
    """Real BAU + real HBLE series, shared by BOTH the named-pathway flow and the
    surrogate flow so "real references everywhere" is implemented once."""
    return {
        "bau": _build_series(BAU_PID, "Business as Usual (Real Run)"),
        "hble": _build_series(HBLE_PID, "Candidate NDC3 / HBLE (Real Run)"),
    }


# ── Comparison bundle (predict_comparison()-shaped) ───────────────────────────

def compare_series(scenario: dict, baseline: dict) -> dict:
    """Compute comparison / sector_deltas / cost_benefit_deltas of a `predict()`-shaped
    scenario against a `predict()`-shaped baseline.

    Shared by BOTH flows so the delta math lives in one place:
      • named-pathway flow — scenario is a real pre-run, baseline is real BAU;
      • surrogate flow (run_simulation) — scenario is the XGBoost prediction,
        baseline is real BAU (so policymakers get a real comparison; this knowingly
        includes surrogate model error, to be revisited).

    Iterates the FIXED anchor years (`EMISSION_YEARS` for sectors, `CB_YEARS` for
    cost-benefit), not the scenario's own year keys, so it is robust to a scenario
    carrying a denser/different year grid than the baseline — the surrogate emits
    predictor.TARGET_YEARS while the real BAU baseline carries only the anchors.
    A year absent from the scenario trajectory is skipped (matches the prior
    per-trajectory behaviour for real pathways, whose trajectories are anchor-only).

    Returns {comparison, sector_deltas, cost_benefit_deltas} — the same three keys
    the callers splice into their result bundle.
    """
    # % change vs baseline for the derived economy-wide emission headline metrics.
    comparison: dict[str, float] = {}
    for metric, pred in scenario["predictions"].items():
        s_val = pred["value"]
        b_val = baseline["predictions"].get(metric, {}).get("value", 0.0)
        comparison[metric] = round(100 * (s_val - b_val) / abs(b_val), 2) if b_val else 0.0

    # Per sector × anchor-year absolute + % deltas vs baseline.
    sector_deltas: dict[str, dict[int, dict]] = {}
    for sector, traj in scenario["sector_trajectories"].items():
        sector_deltas[sector] = {}
        bau_traj = baseline["sector_trajectories"].get(sector, {})
        for year in EMISSION_YEARS:
            if year not in traj:
                continue
            val = traj[year]
            bau_val = bau_traj.get(year, 0.0)
            sector_deltas[sector][year] = {
                "scenario": val,
                "bau": round(bau_val, 3),
                "delta": round(val - bau_val, 3),
                "pct_change": round(100 * (val - bau_val) / abs(bau_val), 2) if bau_val else 0.0,
            }

    # Per-year cost/benefit: scenario vs baseline totals + cost-as-%-of-GDP.
    cost_benefit_deltas: dict[int, dict] = {}
    for year in CB_YEARS:
        s = scenario["cost_benefit"].get(year, {})
        b = baseline["cost_benefit"].get(year, {})
        cost_benefit_deltas[year] = {
            "benefit_scenario": s.get("total_benefit", 0.0),
            "benefit_bau": b.get("total_benefit", 0.0),
            "cost_scenario": s.get("total_cost", 0.0),
            "cost_bau": b.get("total_cost", 0.0),
            "net_scenario": s.get("net", 0.0),
            "net_bau": b.get("net", 0.0),
            "cost_pct_gdp_scenario": s.get("cost_pct_gdp", 0.0),
            "cost_pct_gdp_bau": b.get("cost_pct_gdp", 0.0),
        }

    return {
        "comparison": comparison,
        "sector_deltas": sector_deltas,
        "cost_benefit_deltas": cost_benefit_deltas,
    }


def build_pathway_comparison(name_or_id) -> dict:
    """For a named pathway, return a `predict_comparison()`-shaped bundle vs real BAU,
    plus the real BAU+HBLE reference bundle.

    Keys: scenario, baseline, comparison, sector_deltas, cost_benefit_deltas,
    references{bau,hble} — mirrors predictor.predict_comparison so agent code and
    the charts are reused unchanged.
    """
    display_name, meta = resolve_pathway(name_or_id)
    pid = meta["primary_id"]

    scenario = _build_series(pid, display_name)
    baseline = _build_series(BAU_PID, "Business as Usual (Real Run)")
    deltas = compare_series(scenario, baseline)

    logger.info("build_pathway_comparison: %s (primary_id=%d)", display_name, pid)
    return {
        "scenario": scenario,
        "baseline": baseline,
        "references": build_reference_bundle(),
        # Full label/colour/order for the 23 categories (from the crosswalk sidecar);
        # the frontend merges these over its built-in SECTOR_META.
        "sector_meta_overrides": sector_crosswalk.SECTOR_META,
        **deltas,
    }


# ── Driver / lever detail ─────────────────────────────────────────────────────

def _summarize_field_by_tp(by_tp: dict[int, float], anchors: list[tuple[int, int]]) -> dict | None:
    """Like s3_lookup._summarize_field, but indexed by actual time_period instead of
    list position (the wide pathways file starts at tp4)."""
    series: dict[int, float] = {}
    for tp, year in anchors:
        if tp in by_tp and pd.notna(by_tp[tp]):
            try:
                series[year] = round(float(by_tp[tp]), 4)
            except (TypeError, ValueError):
                return None
    if len(series) < 2:
        return None
    first = series[anchors[0][1]]
    last = series[anchors[-1][1]]
    pct = round((last - first) / abs(first) * 100.0, 1) if first not in (0, 0.0) else None
    return {"by_year": series, "pct_change": pct}


def _collect_trajectories_by_tp(
    fields: list[tuple[str, str]],
    pid_df: pd.DataFrame,
    anchors: list[tuple[int, int]],
    top_n: int,
) -> tuple[list[dict], int]:
    """Summarize the field columns present in the (single-pid) wide dataframe,
    sorted by |pct_change|. Returns (top_n records, total matched)."""
    recs: list[dict] = []
    for field, disp_name in fields:
        if field not in pid_df.columns:
            continue
        by_tp = dict(zip(pid_df["time_period"], pid_df[field]))
        summ = _summarize_field_by_tp(by_tp, anchors)
        if summ is None:
            continue
        recs.append({
            "field": field,
            "name": disp_name,
            "by_year": summ["by_year"],
            "pct_change": summ["pct_change"],
        })
    recs.sort(key=lambda r: abs(r["pct_change"]) if r["pct_change"] is not None else -1.0,
              reverse=True)
    return recs[:top_n], len(recs)


# Input drivers anchor 2019→2070; the wide pathways file has no pre-2019 rows.
_DRIVER_ANCHORS: list[tuple[int, int]] = [(4, 2019), (20, 2035), (35, 2050), (55, 2070)]


def get_pathway_driver_variables(name_or_id, group_ids: list[int], top_n: int = 6) -> dict:
    """Real driver/output variable trajectories for a named pathway's changed levers,
    read from the pathway's own row in uganda_pathways.csv (no nearest-neighbour).

    Same shape as s3_lookup.get_scenario_variable_trajectories:
      {primary_id, groups:{gid: {...}}, design_note}
    """
    import json

    display_name, meta = resolve_pathway(name_or_id)
    pid = meta["primary_id"]

    df = _load_pathways_df()
    pid_df = df[df["primary_id"] == pid].sort_values("time_period")

    with open(settings.feature_registry_path) as fh:
        lever_features = json.load(fh).get("lever_features", {})

    groups: dict[int, dict] = {}
    for gid in group_ids:
        gmeta = lever_features.get(str(gid)) or {}
        in_fields = s3_lookup._input_fields_for_group(gid, lever_features)
        out_fields = s3_lookup._output_fields_for_group(gid, lever_features)
        in_recs, in_total = _collect_trajectories_by_tp(in_fields, pid_df, _DRIVER_ANCHORS, top_n)
        out_recs, out_total = _collect_trajectories_by_tp(out_fields, pid_df, _DRIVER_ANCHORS, top_n)
        groups[gid] = {
            "display_name": gmeta.get("display_name", f"Group {gid}"),
            "transformation_code": gmeta.get("transformation_code", ""),
            "inputs": in_recs,
            "outputs": out_recs,
            "counts": {"inputs": in_total, "outputs": out_total},
            "has_outputs": out_total > 0,
        }

    return {
        "primary_id": pid,
        "groups": groups,
        "design_note": (
            f"Real pre-run pathway values (primary_id={pid}, {display_name}), "
            "read directly from the pathway's own trajectory — not a nearest-neighbour match."
        ),
    }
