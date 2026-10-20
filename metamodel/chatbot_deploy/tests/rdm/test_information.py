"""
Tests for backend/rdm/tools/information.py: lever_x_profile and output_levers, v0 and v1.

Test 1 — the arms: v0 carries no values (no units, input values, medians, ranges, correlations or
         effects) and its lists are alphabetical / in id order; every arm has the same relations;
         v1_inputs adds only input values, v1_outputs only output values, v1 both.
Test 2 — scope: only the 505 crosswalk emissions; no "structural, output constant in runs" links;
         every category in a reply lists the fields the lever moves in it (the crosswalk).
Test 3 — known answers (checked by hand): lever 35 raises the light-duty electric share from 0.50 to
         0.72 in 2050 and lowers transport emissions; in transport emissions GDP growth raises the output.
Test 4 — edges: lever 6 has no links and says so; a category is found by slug or display name;
         unknown outputs, the 133 non-crosswalk emission fields and unknown years are refused.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.data.store import Store  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402
from backend.rdm.tools import information as I  # noqa: E402
from backend.rdm.tools.common import ToolError  # noqa: E402

LIGHT_DUTY, GDP = 35, 57
EV_VKM = "vehicle_distance_traveled_trns_road_light_electricity"
INPUT_VALUES = {"unit", "range_from_bau"}
OUTPUT_VALUES = {"values", "median_by_lever_level", "median_at_low_end", "median_at_high_end",
                 "effect_low_to_high", "p10_p90_at_high_end", "correlation"}
V1_ONLY = INPUT_VALUES | OUTPUT_VALUES


@pytest.fixture(scope="module")
def ctx():
    run = get_run()
    try:
        return run, Store(run)
    except FileNotFoundError as e:
        pytest.skip(str(e))


def keys(obj) -> set:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(keys(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(set(), *(keys(v) for v in obj))
    return set()


def relations(p) -> set:
    return ({("in", d["field"]) for d in p["inputs"]}
            | {("cat", d["category"], tuple(d["fields_the_lever_moves"]), d["uncertainty_also_moves"])
               for d in p["emission_categories"]}
            | {("var", d["field"], tuple(d["feeds"]), d["uncertainty_also_moves"]) for d in p["in_between_variables"]})


def test_arms(ctx):
    run, store = ctx
    p = {a: I.lever_x_profile(run, store, LIGHT_DUTY, GDP, 2050, a) for a in I.VERSIONS}
    assert not keys(p["v0"]) & V1_ONLY
    assert keys(p["v1_inputs"]) & V1_ONLY == INPUT_VALUES
    assert not keys(p["v1_outputs"]) & {"range_from_bau"} and keys(p["v1_outputs"]) & {"values"}
    assert keys(p["v1"]) >= {"range_from_bau", "values"}
    assert len({frozenset(relations(x)) for x in p.values()}) == 1
    assert [d["field"] for d in p["v0"]["inputs"]] == sorted(d["field"] for d in p["v0"]["inputs"])
    o0 = I.output_levers(run, store, "transportation", 2050, "v0")
    o1 = I.output_levers(run, store, "transportation", 2050, "v1")
    assert not keys(o0) & V1_ONLY
    assert [d["id"] for d in o0["levers"]] == sorted(d["id"] for d in o0["levers"])
    assert {d["id"] for d in o0["levers"]} == {d["id"] for d in o1["levers"]}


def test_scope(ctx):
    run, store = ctx
    cat = I.category_of(run)
    assert len(cat) == 505
    m = I.links(run)
    assert set(m[m.output_kind == "emission"].output_field) <= set(cat)
    assert (m.status != I.EXCLUDED_STATUS).all()
    p = I.lever_x_profile(run, store, LIGHT_DUTY, GDP, 2050, "v0")
    assert p["emission_categories"]
    for c in p["emission_categories"]:
        assert c["fields_the_lever_moves"] and all(cat[f] == c["metric"][len("emissions_"):] for f in c["fields_the_lever_moves"])


def test_known_answers(ctx):
    run, store = ctx
    p = I.lever_x_profile(run, store, LIGHT_DUTY, GDP, 2050, "v1")
    ev = next(d for d in p["inputs"] if d["field"] == "frac_trns_fuelmix_road_light_electricity")["range_from_bau"]["2050"]
    assert ev["bau (lever 0)"] == pytest.approx(0.50, abs=0.005) and ev["top of the range run (lever 1)"] == pytest.approx(0.72, abs=0.005)
    assert ev["direction"] == "up"
    trns = next(c for c in p["emission_categories"] if c["metric"] == "emissions_transportation")["values"]
    assert trns["median_by_lever_level"]["high"] < trns["median_by_lever_level"]["low"]
    o = I.output_levers(run, store, "transportation", 2050, "v1")
    eff = {d["id"]: d["effect_low_to_high"] for d in o["levers"] + o["uncertainties"]}
    assert eff[LIGHT_DUTY] < 0 < eff[GDP]


def test_edges(ctx):
    run, store = ctx
    p6 = I.lever_x_profile(run, store, 6, GDP, 2050, "v1")
    assert p6["emission_categories"] == [] and p6["in_between_variables"] == [] and p6["inputs"]
    a = I.output_levers(run, store, "transportation", 2050, "v0")
    b = I.output_levers(run, store, "Transportation", 2050, "v0")
    assert a == b
    for bad in ("not_an_output", "emission_co2e_c2f6_ippu_production_chemicals"):
        with pytest.raises(ToolError):
            I.output_levers(run, store, bad, 2050, "v0")
    with pytest.raises(ToolError):
        I.lever_x_profile(run, store, LIGHT_DUTY, GDP, 2030, "v0")
    with pytest.raises(ToolError):
        I.lever_x_profile(run, store, GDP, LIGHT_DUTY, 2050, "v0")
