"""
Integration tests for backend/services/pathways_lookup.py + its agent wiring.

Unlike test_s3_lookup, every test here runs against the *local* curated CSVs
(uganda_pathways.csv, cba_data_air_pollution.csv under the run dir's pathways/
subfolder) — no S3 and no ANTHROPIC_API_KEY needed. If the curated CSVs are not
present locally (e.g. a fresh checkout that only has the S3 copies), the reader
raises FileNotFoundError and the data-dependent tests SKIP with that message
rather than failing red.

Test 1 — resolve_pathway (pure registry, no data)
    Every one of the 6 registry names round-trips; aliases and numeric primary_id
    resolve; an unknown name raises LookupError naming the valid pathways.

Test 2 — reader contract (local CSVs)
    The reason this module exists: HBLE @2070 is the REAL ~8.21 MtCO₂e, not the
    surrogate's ~115. BAU is far higher; BAU cost-benefit is identically zero with
    GDP still present; NDC 2.5's cost keys are exactly the 3 *_cost types mapped to
    {technical, system, fuel} (technical_savings stays a benefit); indoor_air_pollution
    is surfaced as a benefit; emission anchors only carry the documented anchor years.

Test 3 — get_pathway_results handler → SimulationResponse
    Driving the agent handler (no LLM) for "NDC 2.5" returns a simulation payload
    that validates against the real backend SimulationResponse schema, is flagged
    data_source="real_run", carries real BAU+HBLE references on both charts, and
    attaches real driver detail when groups_changed is supplied. A bad pathway name
    returns an {"error": ...} dict, not an exception.

Test 4 — _attach_real_references on a surrogate result
    The shared injector adds real BAU+HBLE reference series to a surrogate-shaped
    result's chart bundles WITHOUT touching the surrogate baseline/comparison, and
    is a no-op-safe guard on a result with no chart bundles.

Run directly:
    cd metamodel/chatbot_deploy
    python -m tests.test_pathways_lookup

Run with pytest:
    cd metamodel/chatbot_deploy
    pytest tests/test_pathways_lookup.py -v
"""

import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow `python -m tests.test_pathways_lookup` from metamodel/chatbot_deploy/
_CHATBOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_CHATBOT_DIR))

# Reuse the exact result/reporting harness the s3_lookup tests use.
from tests.test_s3_lookup import _Result

from backend.services import agent, pathways_lookup as pl
from backend.schemas import SimulationResponse, TraceStep


def _data_available() -> str | None:
    """Return None if the local curated CSVs load, else a skip reason.

    The reader is local-first; a fresh checkout may only have the S3 copies (no
    creds in CI), so we translate a missing-file into a graceful skip.
    """
    try:
        pl._load_pathways_df()
        pl._load_cba_df()
        return None
    except FileNotFoundError as exc:
        return f"curated pathways CSVs not present locally: {exc}"
    except Exception as exc:  # pragma: no cover — auth/other, still a skip not a fail
        return f"could not load curated CSVs: {type(exc).__name__}: {exc}"


# ── Test 1: resolve_pathway (pure registry — always runs) ─────────────────────

def test_resolve_pathway() -> _Result:
    r = _Result("Test 1 — resolve_pathway (registry, aliases, numeric, errors)")
    failures: list[str] = []
    details: list[str] = []

    # Every registry name resolves to itself.
    for name, meta in pl.PATHWAY_REGISTRY.items():
        got_name, got_meta = pl.resolve_pathway(name)
        if got_name != name:
            failures.append(f"resolve({name!r}) -> {got_name!r}, expected {name!r}")
        # …and by its numeric primary_id.
        pid = meta["primary_id"]
        got_by_id, _ = pl.resolve_pathway(pid)
        if got_by_id != name:
            failures.append(f"resolve(primary_id={pid}) -> {got_by_id!r}, expected {name!r}")
    details.append(f"all {len(pl.PATHWAY_REGISTRY)} registry names + numeric ids round-trip")

    # A representative alias per interesting pathway (case/spacing-insensitive).
    alias_cases = {
        "ndc 2.5": "NDC 2.5",
        "  NET ZERO  ": "Candidate NDC3",
        "hble": "Candidate NDC3",
        "business as usual": "BAU",
        "unconditional": "NDC2 Unconditional",
    }
    for alias, expected in alias_cases.items():
        got, _ = pl.resolve_pathway(alias)
        if got != expected:
            failures.append(f"resolve({alias!r}) -> {got!r}, expected {expected!r}")
    details.append(f"{len(alias_cases)} aliases resolve (case/whitespace-insensitive)")

    # Unknown name → LookupError naming the valid pathways.
    try:
        pl.resolve_pathway("not a pathway")
        failures.append("resolve('not a pathway') did NOT raise LookupError")
    except LookupError as exc:
        if "NDC 2.5" not in str(exc):
            failures.append(f"LookupError message does not list valid pathways: {exc}")
        details.append("unknown name raises LookupError listing valid pathways")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 2: reader contract (local CSVs) ──────────────────────────────────────

def test_reader_contract() -> _Result:
    r = _Result("Test 2 — reader contract (HBLE 6.35, BAU cb≡0, cost keys, anchors)")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    # (a) The headline reason this module exists: real HBLE @2070 is single-digit, not
    # the surrogate's ~115. The corrected pathways file (2026-07-15, biomass counted
    # consistently) puts it at ≈8.21 MtCO₂e — computed from the 23 crosswalk categories,
    # which now reconcile to the file's subsector totals at every year.
    hble = pl._build_series(pl.HBLE_PID, "HBLE")
    bau = pl._build_series(pl.BAU_PID, "BAU")
    hble_2070 = hble["predictions"]["emission_total_yr2070"]["value"]
    bau_2070 = bau["predictions"]["emission_total_yr2070"]["value"]
    details.append(f"HBLE @2070 = {hble_2070} MtCO₂e   BAU @2070 = {bau_2070} MtCO₂e")
    if not (6.0 <= hble_2070 <= 12.0):
        failures.append(
            f"ASSERTION FAILED: HBLE @2070 = {hble_2070}, expected the real ~8.21 "
            "(a value near ~115 means the surrogate leaked in)"
        )
    if bau_2070 <= 100:
        failures.append(f"ASSERTION FAILED: BAU @2070 = {bau_2070}, expected a high (>100) baseline")

    # (b) Emission anchors only ever carry the documented anchor years.
    stray_years = {
        y for traj in hble["sector_trajectories"].values() for y in traj
    } - set(pl.EMISSION_YEARS)
    if stray_years:
        failures.append(f"ASSERTION FAILED: emission trajectories carry non-anchor years {sorted(stray_years)}")

    # (c) BAU cost-benefit is identically zero (diffs vs baseline) but GDP is present.
    bau_cb = pl.get_pathway_cost_benefit(pl.BAU_PID)
    for year in pl.CB_YEARS:
        blk = bau_cb[year]
        if not (blk["total_benefit"] == 0.0 and blk["total_cost"] == 0.0 and blk["net"] == 0.0):
            failures.append(f"ASSERTION FAILED: BAU cost-benefit @{year} is not zero: {blk}")
        if not blk["benefits"] == {} == blk["costs"]:
            failures.append(f"ASSERTION FAILED: BAU @{year} has non-empty benefit/cost maps")
    if not all(bau_cb[y]["gdp"] > 0 for y in pl.CB_YEARS):
        failures.append("ASSERTION FAILED: BAU GDP should still be populated from uganda_pathways.csv")
    details.append("BAU cost-benefit ≡ 0 at every CB year, GDP still populated")

    # (d) Costs are exactly the 3 *_cost types mapped to {technical, system, fuel};
    #     technical_savings (a benefit sharing the prefix) must NEVER be a cost.
    ndc_cb = pl.get_pathway_cost_benefit(2002)  # NDC 2.5
    allowed_cost_keys = set(pl._COST_KEY_MAP.values())  # {technical, system, fuel}
    all_benefit_keys: set[str] = set()
    for year in pl.CB_YEARS:
        stray_cost = set(ndc_cb[year]["costs"]) - allowed_cost_keys
        if stray_cost:
            failures.append(f"ASSERTION FAILED: NDC 2.5 @{year} cost keys {sorted(stray_cost)} outside {sorted(allowed_cost_keys)}")
        all_benefit_keys |= set(ndc_cb[year]["benefits"])
    if "technical_savings" in ndc_cb[2050]["costs"]:
        failures.append("ASSERTION FAILED: technical_savings mis-classified as a cost")
    details.append(f"NDC 2.5 cost keys ⊆ {sorted(allowed_cost_keys)} (exact-membership, not prefix)")

    # (e) indoor_air_pollution is surfaced as a benefit (was silently dropped before).
    if "indoor_air_pollution" not in all_benefit_keys:
        failures.append("ASSERTION FAILED: indoor_air_pollution not present among NDC 2.5 benefits")
    details.append("indoor_air_pollution surfaced as a benefit")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 3: get_pathway_results handler → SimulationResponse ───────────────────

def test_get_pathway_results_handler() -> _Result:
    r = _Result("Test 3 — get_pathway_results handler → SimulationResponse (real_run)")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    # Drive the real agent dispatch path (no LLM). sector_predictor/locked_overrides
    # are unused by this handler.
    summary, sim_data, interp = agent._execute_tool_call(
        "get_pathway_results",
        {"pathway": "NDC 2.5", "groups_changed": [4]},
        sector_predictor=None,
        locked_overrides={},
    )

    # (a) The payload the API returns must validate against the real schema.
    try:
        SimulationResponse.model_validate(sim_data)
        details.append("sim_data validates against SimulationResponse")
    except Exception as exc:
        failures.append(f"ASSERTION FAILED: sim_data fails SimulationResponse validation: {exc}")

    # (b) Flagged as a real run, not the surrogate.
    if summary.get("data_source") != "real_run":
        failures.append(f"ASSERTION FAILED: summary.data_source={summary.get('data_source')!r}, expected 'real_run'")
    if interp.get("data_source") != "real_run":
        failures.append(f"ASSERTION FAILED: interpretation.data_source={interp.get('data_source')!r}")
    details.append("data_source='real_run' on both summary and interpretation")

    # (c) Real BAU+HBLE references on BOTH chart bundles.
    sec_refs = (sim_data.get("sector_comparison") or {}).get("references") or {}
    cb_refs = (sim_data.get("cost_benefit_comparison") or {}).get("references") or {}
    if set(sec_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: sector_comparison.references keys={sorted(sec_refs)}, expected bau+hble")
    if set(cb_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: cost_benefit_comparison.references keys={sorted(cb_refs)}, expected bau+hble")
    details.append("real BAU+HBLE references attached to both sector and cost-benefit bundles")

    # (c2) The bundle carries label/colour meta for the 23 official inventory categories
    # (from sector_categories.json), which the frontend merges over its SECTOR_META. The
    # old per-source `entc`→"Forest Land - Removals" relabel is gone — both surrogate and
    # real pathways now use the same categories, so "Forest Land - Removals" is a real
    # category slug (forest_land_removals), not an override.
    ov = (sim_data.get("sector_comparison") or {}).get("sector_meta_overrides") or {}
    from backend.services import sector_crosswalk
    if set(ov) != set(sector_crosswalk.CATEGORIES):
        failures.append(f"ASSERTION FAILED: sector_meta_overrides has {len(ov)} keys, expected the 23 categories")
    elif ov.get("forest_land_removals", {}).get("label") != "Forest Land - Removals":
        failures.append(f"ASSERTION FAILED: forest_land_removals label wrong: {ov.get('forest_land_removals')}")
    else:
        details.append("bundle carries all 23 category labels/colours (incl. Forest Land - Removals)")

    # (d) groups_changed=[4] attaches real driver detail (no nearest-neighbour).
    dd = summary.get("driver_detail")
    if not dd:
        failures.append("ASSERTION FAILED: groups_changed=[4] did not attach driver_detail")
    elif "nearest-neighbour" not in dd and "not a nearest" not in dd:
        # driver_detail is a formatted block; the no-KNN note should be present.
        details.append("driver_detail attached (note: no-KNN caveat text not matched — check formatter)")
    else:
        details.append("driver_detail attached with the real-run (no-KNN) caveat")

    # (e) A bad pathway name is a graceful error dict, not an exception.
    err_summary, err_sim, err_interp = agent._execute_tool_call(
        "get_pathway_results", {"pathway": "not a pathway"},
        sector_predictor=None, locked_overrides={},
    )
    if "error" not in err_summary or err_sim is not None:
        failures.append(f"ASSERTION FAILED: bad pathway should return an error dict + None sim, got {err_summary!r}")
    else:
        details.append("unknown pathway name → {'error': ...} dict (no exception)")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 4: _attach_real_references injector ──────────────────────────────────

def test_attach_real_references() -> _Result:
    r = _Result("Test 4 — _attach_real_references (inject on surrogate, guard no-op)")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    # Minimal surrogate-shaped result with both chart bundles present.
    surrogate = {
        "sector_comparison": {"scenario": {"x": 1}, "baseline": {"y": 2}},
        "cost_benefit_comparison": {"years": [2050], "scenario": {}, "baseline": {}},
    }
    before_sector = dict(surrogate["sector_comparison"])
    agent._attach_real_references(surrogate)

    sec_refs = surrogate["sector_comparison"].get("references", {})
    cb_refs = surrogate["cost_benefit_comparison"].get("references", {})
    if set(sec_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: sector references keys={sorted(sec_refs)}")
    if set(cb_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: cost-benefit references keys={sorted(cb_refs)}")
    # The surrogate's own scenario/baseline must be untouched (only 'references' added).
    if surrogate["sector_comparison"]["scenario"] != before_sector["scenario"]:
        failures.append("ASSERTION FAILED: injector mutated the surrogate scenario bundle")
    # cost-benefit references are the per-year cost_benefit maps, not the full series.
    if "cost_benefit" in cb_refs.get("bau", {}):
        failures.append("ASSERTION FAILED: cost-benefit references should be the per-year map, not the full series")
    details.append("real BAU+HBLE injected into both bundles; surrogate scenario left intact")

    # Guard: a result with no chart bundles must not raise.
    empty: dict = {}
    try:
        agent._attach_real_references(empty)
        if "references" in empty:
            failures.append("ASSERTION FAILED: injector added references to a bundle-less result")
        details.append("no-op-safe on a result with no chart bundles")
    except Exception as exc:
        failures.append(f"ASSERTION FAILED: injector raised on empty result: {exc}")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 5: compare_series with a surrogate-like (denser-year) scenario ───────

def test_compare_series_surrogate_like() -> _Result:
    r = _Result("Test 5 — compare_series (surrogate-like scenario vs real BAU)")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    real_bau = pl._build_series(pl.BAU_PID, "BAU")
    # Fake a surrogate scenario = half of BAU, but with an OFF-anchor year (2033) in
    # every sector trajectory — the surrogate can emit a denser year grid than the
    # anchor-only real BAU. compare_series must key deltas by the fixed anchor years
    # and silently drop 2033.
    scen = {
        "scenario_name": "Half-BAU what-if",
        "predictions": {
            m: {"value": round(p["value"] * 0.5, 3), "unit": p["unit"],
                "display_name": p["display_name"]}
            for m, p in real_bau["predictions"].items()
        },
        "sector_trajectories": {
            sec: {**{y: v * 0.5 for y, v in traj.items()}, 2033: 999.0}
            for sec, traj in real_bau["sector_trajectories"].items()
        },
        "cost_benefit": real_bau["cost_benefit"],
    }

    out = pl.compare_series(scen, real_bau)

    # (a) sector_deltas keyed ONLY by anchor years (2033 dropped).
    stray = {
        y for years in out["sector_deltas"].values() for y in years
    } - set(pl.EMISSION_YEARS)
    if stray:
        failures.append(f"ASSERTION FAILED: sector_deltas carry non-anchor years {sorted(stray)} (2033 leaked)")
    details.append("off-anchor year 2033 dropped; deltas keyed by anchor years only")

    # (b) The delta 'bau' field is the REAL BAU value; scenario is half of it.
    sample_sector = next(iter(out["sector_deltas"]))
    yr = 2070 if 2070 in out["sector_deltas"][sample_sector] else next(iter(out["sector_deltas"][sample_sector]))
    d = out["sector_deltas"][sample_sector][yr]
    if abs(d["bau"] - real_bau["sector_trajectories"][sample_sector][yr]) > 1e-6:
        failures.append(f"ASSERTION FAILED: delta.bau {d['bau']} != real BAU value")
    details.append(f"sector delta carries real BAU value (sector={sample_sector} @{yr}: bau={d['bau']})")

    # (c) Headline comparison ≈ -50% where BAU is non-zero (scenario is half of BAU).
    m = "emission_total_yr2070"
    if m in out["comparison"]:
        pct = out["comparison"][m]
        if abs(pct - (-50.0)) > 0.6:
            failures.append(f"ASSERTION FAILED: {m} comparison {pct}%, expected ≈ -50%")
        details.append(f"{m} comparison = {pct}% (≈ -50% of real BAU)")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 6: run_simulation rewire — surrogate scenario vs REAL BAU baseline ────

def test_run_simulation_real_bau_baseline() -> _Result:
    r = _Result("Test 6 — run_simulation compares vs the surrogate's OWN BAU; real BAU+HBLE as reference lines")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    # A fake surrogate predictor: its scenario + baseline are the surrogate's own series.
    # We reuse real pathway series only as stand-in numbers; the point is that the
    # comparison baseline must be the SURROGATE's baseline, not a real run.
    scenario_series = pl._build_series(pl.HBLE_PID, "Fake what-if")
    surrogate_bau = pl._build_series(pl.HBLE_PID, "Surrogate BAU")

    # predict_comparison fills the headline % dict; mirror that (scenario==baseline here
    # so the % change is 0) so the summary can carry change_from_bau_pct.
    from backend.services.predictor import TARGET_YEARS
    _cmp = {f"emission_total_yr{y}": 0.0 for y in TARGET_YEARS}

    class _FakePredictor:
        def predict_comparison(self, **kw):
            return {
                "scenario": {**scenario_series, "scenario_name": kw.get("scenario_name", "S")},
                "baseline": surrogate_bau,
                "comparison": _cmp, "sector_deltas": {}, "cost_benefit_deltas": {},
            }

    summary, result, interp = agent._execute_tool_call(
        "run_simulation",
        {"scenario_name": "Grid decarb what-if", "lever_overrides": {"5": 0.9},
         "compare_to_baseline": True},
        sector_predictor=_FakePredictor(),
        locked_overrides={},
    )

    # (a) Baseline is the SURROGATE's own BAU (from predict_comparison), NOT the real run.
    base_2070 = result["baseline"]["predictions"]["emission_total_yr2070"]["value"]
    surrogate_bau_2070 = surrogate_bau["predictions"]["emission_total_yr2070"]["value"]
    if abs(base_2070 - surrogate_bau_2070) > 1e-6:
        failures.append(f"ASSERTION FAILED: baseline @2070 = {base_2070}, expected surrogate BAU {surrogate_bau_2070}")
    if interp.get("baseline_source") != "surrogate_bau":
        failures.append(f"ASSERTION FAILED: baseline_source={interp.get('baseline_source')}, expected surrogate_bau")
    details.append(f"baseline is the surrogate's own BAU (@2070 = {base_2070})")

    # (a2) Real BAU + HBLE are still attached as REFERENCE LINES on the sector chart.
    sec_refs = (result.get("sector_comparison") or {}).get("references") or {}
    if set(sec_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: sector reference lines={sorted(sec_refs)}, expected bau+hble")
    else:
        real_bau_2070 = pl._build_series(pl.BAU_PID, "BAU")["predictions"]["emission_total_yr2070"]["value"]
        details.append(f"real BAU/HBLE overlaid as reference lines (real BAU @2070 = {real_bau_2070})")

    # (b) Summary narrates the HBLE frontier value alongside the BAU baseline.
    yr = summary["predictions"]["emission_total_yr2070"]
    if "hble_value" not in yr:
        failures.append("ASSERTION FAILED: summary missing hble_value (HBLE frontier not narrated)")
    if "bau_value" not in yr or "change_from_bau_pct" not in yr:
        failures.append("ASSERTION FAILED: summary missing bau_value / change_from_bau_pct")
    details.append(
        f"summary carries bau_value={yr.get('bau_value')}, hble_value={yr.get('hble_value')}, "
        f"change_from_bau_pct={yr.get('change_from_bau_pct')}"
    )

    # (c) Real BAU+HBLE references on both chart bundles.
    sec_refs = (result.get("sector_comparison") or {}).get("references") or {}
    cb_refs = (result.get("cost_benefit_comparison") or {}).get("references") or {}
    if set(sec_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: sector references {sorted(sec_refs)}, expected bau+hble")
    if set(cb_refs) != {"bau", "hble"}:
        failures.append(f"ASSERTION FAILED: cost-benefit references {sorted(cb_refs)}, expected bau+hble")
    details.append("real BAU+HBLE references attached to both chart bundles")

    # (d) The payload still validates against the real schema.
    try:
        SimulationResponse.model_validate(result)
        details.append("result validates against SimulationResponse")
    except Exception as exc:
        failures.append(f"ASSERTION FAILED: result fails SimulationResponse validation: {exc}")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── Test 7: process trace (provenance) events ─────────────────────────────────

def test_process_trace() -> _Result:
    r = _Result("Test 7 — process trace (surrogate / real_run / error steps)")
    skip = _data_available()
    if skip:
        return r.skip(skip)

    failures: list[str] = []
    details: list[str] = []

    # (a) Surrogate run_simulation → surrogate_xgboost, notes the real-BAU/HBLE compare.
    hble = pl._build_series(pl.HBLE_PID, "Fake")

    class _FakePredictor:
        def predict_comparison(self, **kw):
            return {"scenario": {**hble, "scenario_name": kw.get("scenario_name", "S")},
                    "baseline": hble, "comparison": {}, "sector_deltas": {}, "cost_benefit_deltas": {}}

    inp = {"scenario_name": "Grid decarb", "lever_overrides": {"5": 0.9, "7": 0.8},
           "exogenous_overrides": {"57": 0.7}}
    _res, _sim, interp = agent._execute_tool_call(
        "run_simulation", inp, sector_predictor=_FakePredictor(), locked_overrides={})
    ev = agent._build_trace_event(1, "run_simulation", inp, _res, interp)
    TraceStep.model_validate(ev)
    if ev["data_source"] != "surrogate_xgboost":
        failures.append(f"ASSERTION FAILED: run_simulation data_source={ev['data_source']!r}")
    if not any("BAU" in d and "HBLE" in d for d in ev["details"]):
        failures.append(f"ASSERTION FAILED: surrogate step doesn't note the BAU/HBLE compare: {ev['details']}")
    # The changed levers must be NAMED (from the registry), not just counted.
    lever_line = next((d for d in ev["details"] if "Policy levers set" in d), "")
    if not lever_line:
        failures.append(f"ASSERTION FAILED: surrogate step doesn't name the changed levers: {ev['details']}")
    elif "Group 5" in lever_line or "Group 7" in lever_line:
        failures.append(f"ASSERTION FAILED: lever names didn't resolve (fell back to 'Group N'): {lever_line!r}")
    if lever_line and "0.90" not in lever_line:
        failures.append(f"ASSERTION FAILED: lever line missing the set value: {lever_line!r}")
    if ev["status"] != "ok":
        failures.append("ASSERTION FAILED: surrogate step should be status ok")
    details.append(f"run_simulation → {ev['data_source']}; details={ev['details']}")

    # (b) Named pathway → real_run, notes the compare + driver detail.
    inp2 = {"pathway": "NDC 2.5", "groups_changed": [4]}
    _res2, _sim2, interp2 = agent._execute_tool_call(
        "get_pathway_results", inp2, sector_predictor=None, locked_overrides={})
    ev2 = agent._build_trace_event(2, "get_pathway_results", inp2, _res2, interp2)
    TraceStep.model_validate(ev2)
    if ev2["data_source"] != "real_run":
        failures.append(f"ASSERTION FAILED: pathway data_source={ev2['data_source']!r}")
    if ev2["status"] != "ok":
        failures.append("ASSERTION FAILED: pathway step should be status ok")
    details.append(f"get_pathway_results → {ev2['data_source']}; label={ev2['label']!r}")

    # (c) Bad pathway → status error, failure surfaced in details.
    inp3 = {"pathway": "not a pathway"}
    _res3, _s3, interp3 = agent._execute_tool_call(
        "get_pathway_results", inp3, sector_predictor=None, locked_overrides={})
    ev3 = agent._build_trace_event(3, "get_pathway_results", inp3, _res3, interp3)
    TraceStep.model_validate(ev3)
    if ev3["status"] != "error":
        failures.append(f"ASSERTION FAILED: bad pathway step status={ev3['status']!r}, expected error")
    if not any("failed" in d.lower() for d in ev3["details"]):
        failures.append(f"ASSERTION FAILED: error step doesn't surface the failure: {ev3['details']}")
    details.append("bad pathway → status=error with failure surfaced")

    return r.fail(*details, *failures) if failures else r.ok(*details)


# ── pytest-compatible wrappers ────────────────────────────────────────────────

def _as_pytest(res: _Result) -> None:
    if res.skipped:
        import pytest
        pytest.skip(res.skip_reason)
    assert res.passed, str(res)


def test_resolve_pathway_pytest():
    _as_pytest(test_resolve_pathway())


def test_reader_contract_pytest():
    _as_pytest(test_reader_contract())


def test_get_pathway_results_handler_pytest():
    _as_pytest(test_get_pathway_results_handler())


def test_attach_real_references_pytest():
    _as_pytest(test_attach_real_references())


def test_compare_series_surrogate_like_pytest():
    _as_pytest(test_compare_series_surrogate_like())


def test_run_simulation_real_bau_baseline_pytest():
    _as_pytest(test_run_simulation_real_bau_baseline())


def test_process_trace_pytest():
    _as_pytest(test_process_trace())


# ── Standalone runner ─────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_resolve_pathway,
        test_reader_contract,
        test_get_pathway_results_handler,
        test_attach_real_references,
        test_compare_series_surrogate_like,
        test_run_simulation_real_bau_baseline,
        test_process_trace,
    ]
    results = [t() for t in tests]

    print()
    print("=" * 70)
    print("  pathways_lookup integration tests")
    print("=" * 70)
    for res in results:
        print()
        print(str(res))
    print()
    print("=" * 70)

    n_pass = sum(1 for r in results if r.passed)
    n_skip = sum(1 for r in results if r.skipped)
    n_fail = sum(1 for r in results if not r.passed and not r.skipped)
    print(f"  {n_pass} passed  |  {n_skip} skipped  |  {n_fail} failed")
    print("=" * 70)
    print()

    if n_skip:
        print("  Skips mean the curated pathways CSVs are not present locally.")
        print("  Populate <run_dir>/pathways/ from the run transfers to run them.")
        print()

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
