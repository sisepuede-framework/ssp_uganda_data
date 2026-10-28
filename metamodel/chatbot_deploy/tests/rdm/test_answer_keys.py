"""The answer keys of the policy questions (check 03) recomputed from the lever-inputs table: a lever level moves each
input on a straight line, so the key is (user's target − value at 0) / (value at 1 − value at 0), in 2050.
A target beyond the top of the range has key 1.0; one already met at 0 has key 0.0. Review 2026-10-28."""
from pathlib import Path

import pandas as pd
import pytest

from backend.rdm.eval.questions import BANK_SPECS

TABLE = next((Path(__file__).parents[2] / "backend/rdm/data/tables").glob("*_lever_inputs.csv"), None)
# question → (lever, input field the user's words refer to, the user's target in that field's units)
TARGETS = {
    "P50i": (50, "frac_waso_landfill_gas_recovered", 0.40),
    "P12i": (12, "frac_ippu_cement_clinker", 0.65),
    "AG1": (3, "frac_agrc_no_till_cereals", 0.30),
    "H1": (22, "frac_lvst_mm_chickens_anaerobic_digester", 0.25),
    "WW1": (46, "frac_wali_ww_domestic_rural_treatment_path_septic", 0.50),
    "D3b": (25, "frac_gnrl_eating_red_meat", 0.70),
    "BLD1": (27, "scalar_scoe_heat_energy_demand_residential", 0.75),
    "B6": (35, "frac_trns_fuelmix_road_light_electricity", 0.45),
    "LV1": (20, "frac_lvst_mm_cattle_dairy_anaerobic_digester", 0.40),
    "H2": (26, "frac_ippu_production_with_co2_capture_cement", 0.50),
    "H3": (48, "factor_waso_waste_per_capita_scalar_food", 0.80),
}


@pytest.mark.skipif(TABLE is None, reason="lever-inputs table not built")
@pytest.mark.parametrize("qid", sorted(TARGETS))
def test_key_recomputed(qid):
    lever, field, target = TARGETS[qid]
    t = pd.read_csv(TABLE)
    r = t[(t.lever_id == lever) & (t.field == field) & (t.year == 2050)].iloc[0]
    level = (target - r.at_0) / (r.at_1 - r.at_0)
    key = min(max(level, 0.0), 1.0)
    assert abs(key - BANK_SPECS[qid]["key_level"]) <= 0.005, (qid, round(level, 3))


# Keys read from the runs (model_network's values table: 4,989 sampled runs, 2050). Not in git (187 MB): skipped
# when the table is not built. (question, field, lever, x id, cell, statistic, value in the spec comment, rel. tol.)
RANGES = next((Path(__file__).parents[2] / "backend/rdm/network/out").glob("*_ranges.parquet"), None)
RUN_KEYS = [
    ("S50 p10", "gasrecovered_waso_biogas_landfills_tonne", 50, 0, ("high", "any"), "p10", 120_000, 0.05),
    ("S50 p90", "gasrecovered_waso_biogas_landfills_tonne", 50, 0, ("high", "any"), "p90", 1.4e6, 0.05),
    ("S3 p10", "area_lndu_improved_croplands", 3, 0, ("high", "any"), "p10", 2.2e6, 0.05),
    ("S3 p90", "area_lndu_improved_croplands", 3, 0, ("high", "any"), "p90", 3.1e6, 0.05),
    ("S35 p10", "vehicle_distance_traveled_trns_road_light_electricity", 35, 0, ("high", "any"), "p10", 18e9, 0.05),
    ("S35 p90", "vehicle_distance_traveled_trns_road_light_electricity", 35, 0, ("high", "any"), "p90", 28e9, 0.05),
    ("HD1 low", "energy_consumption_electricity_trns_total", 35, 0, ("low", "any"), "median", 56.0, 0.01),
    ("HD1 high", "energy_consumption_electricity_trns_total", 35, 0, ("high", "any"), "median", 59.9, 0.01),
    ("HC1 low", "gdp_mmm_usd", 0, 57, ("all", "low"), "median", 444, 0.01),
    ("HC1 mid", "gdp_mmm_usd", 0, 57, ("all", "mid"), "median", 540, 0.01),
    ("HC1 high", "gdp_mmm_usd", 0, 57, ("all", "high"), "median", 632, 0.01),
]


@pytest.mark.skipif(RANGES is None, reason="network ranges table not built")
@pytest.mark.parametrize("key", RUN_KEYS, ids=[k[0] for k in RUN_KEYS])
def test_run_key(key):
    _, field, lever, x, (lv, xb), stat, want, tol = key
    r = pd.read_parquet(RANGES, filters=[("field", "==", field), ("year", "==", 2050), ("lever_id", "==", lever),
                                         ("x_id", "==", x)])
    got = float(r[(r.lever_level == lv) & (r.x_bin == xb)][stat].iloc[0])
    assert abs(got - want) <= tol * abs(want), (key[0], got)


def test_x2_key_surrogate():
    """X2 (2035 vs BAU, 1,000 futures): the smallest package at the top −26.1%, every lever at the top −31.0%."""
    from backend.rdm.harness.registry import Harness
    try:
        out = Harness("v1").call("exploratory_modeling", {
            "policies": [{"name": "pkg", "levers": {"30": 1, "29": 1, "9": 1, "15": 1, "23": 1}},
                         {"name": "all", "levers": {str(i): 1 for i in range(1, 55)}}],
            "metrics": ["emissions_total"], "years": [2035], "n_futures": 1000})
    except FileNotFoundError as e:
        pytest.skip(str(e))
    y = out["results"]["emissions_total"]["by_year"]["2035"]
    assert y["pkg"]["change_vs_bau_pct"]["median"] == pytest.approx(-26.1, abs=0.2)
    assert y["all"]["change_vs_bau_pct"]["median"] == pytest.approx(-31.0, abs=0.2)
