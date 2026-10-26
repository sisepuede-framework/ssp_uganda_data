"""
Tests for model_network (backend/rdm/tools/network.py): navigating the SISEPUEDE network, v0 and v1.

Test 1 — the arms: v0 carries no values (no input values, field values, category values or lever effects); both
         arms have the same nodes and links; v1 adds the lever's input values and the values of variables and
         categories.
Test 2 — navigation: every name a reply lists resolves as a node, and stepping forward then back returns to it;
         a lever reaches the categories it sets off; a category is computed from its emission variables.
Test 3 — known answers: lever 35 moves the electric share from 0.50 (BAU) to 0.72 (top of the range) in 2050;
         electric light-duty vehicle-km rise from lever low to high; transport emissions fall with lever 35 and
         are higher with GDP high than low.
Test 4 — the filters: a lever or an uncertainty that does not reach the node is said, and the values fall back;
         uncertainty needs a third; every year of the run answers.
Test 5 — edges: lever 12 (its input is never read in the traced run) says so; unknown nodes, an uncertainty
         asked as a lever and unknown years are refused; "L35", "35" and "lever 35" are the same node.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.runs import get_run  # noqa: E402
from backend.rdm.tools import network as N  # noqa: E402
from backend.rdm.tools.common import ToolError  # noqa: E402

LIGHT_DUTY, GDP, CLINKER = 35, 57, 12
EV_VKM = "vehicle_distance_traveled_trns_road_light_electricity"
VALUES = {"input_values", "values", "category_values", "lever_effects", "values_note"}


@pytest.fixture(scope="module")
def run():
    r = get_run()
    if not (N.NET / f"{r.name}_ranges.parquet").exists():
        pytest.skip("network files not built (backend/rdm/network)")
    return r


def keys(obj) -> set:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(keys(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(set(), *(keys(v) for v in obj))
    return set()


def links(reply) -> set:
    return {(k, d["node"]) for k in ("sets", "computed_from", "used_to_compute") if k in reply
            for d in reply[k]["nodes"]}


def test_arms(run):
    for node in (f"L{LIGHT_DUTY}", "emissions_transportation", EV_VKM):
        r = {a: N.model_network(run, node, 2050, a) for a in N.VERSIONS}
        assert not keys(r["v0"]) & VALUES
        assert len({frozenset(links(x)) for x in r.values()}) == 1
    lv = {a: N.model_network(run, f"L{LIGHT_DUTY}", 2050, a) for a in N.VERSIONS}
    assert {"input_values", "category_values"} <= set(lv["v1"])


def test_navigation(run):
    lever = N.model_network(run, f"L{LIGHT_DUTY}", 2050, "v0")
    assert "emissions_transportation" in lever["reaches"]["emission_categories"]
    first = lever["sets"]["nodes"][0]["node"]
    step = N.model_network(run, first, 2050, "v0")
    assert f"L{LIGHT_DUTY}" in step["levers_that_reach_it"]
    for d in step["used_to_compute"]["nodes"][:10]:
        nxt = N.model_network(run, d["node"], 2050, "v0")
        assert first in {x["node"] for x in nxt["computed_from"]["nodes"]}
    cat = N.model_network(run, "emissions_transportation", 2050, "v0")
    assert cat["kind"] == "category" and all(d["kind"] == "emission" for d in cat["computed_from"]["nodes"])


def test_known_answers(run):
    lv = N.model_network(run, f"L{LIGHT_DUTY}", 2050, "v1")
    ev = next(f for f in lv["input_values"]["fields"] if f["field"] == "frac_trns_fuelmix_road_light_electricity")
    assert ev["bau"] == pytest.approx(0.50, abs=0.005) and ev["top_of_range"] == pytest.approx(0.72, abs=0.005)
    v = N.model_network(run, EV_VKM, 2050, "v1", lever=LIGHT_DUTY)["fields"][0]["values"]
    assert v["low"]["median"] < v["high"]["median"]
    t = lv["category_values"]["emissions_transportation"]
    assert t["high"]["median"] < t["low"]["median"]
    lo = N.model_network(run, "emissions_transportation", 2050, "v1", uncertainty=GDP, third="low")
    hi = N.model_network(run, "emissions_transportation", 2050, "v1", uncertainty=GDP, third="high")
    assert lo["fields"][0]["values"]["all"]["median"] < hi["fields"][0]["values"]["all"]["median"]
    effects = {d["lever"]: d["change"] for d in N.model_network(run, "emissions_transportation", 2050, "v1")["lever_effects"]}
    assert effects[f"L{LIGHT_DUTY}"] < 0


def test_filters(run):
    far = N.model_network(run, "emissions_livestock", 2050, "v1", lever=LIGHT_DUTY)
    assert f"L{LIGHT_DUTY} does not reach this variable" in far["values_note"]
    assert "all" in far["fields"][0]["values"]
    with pytest.raises(ToolError):
        N.model_network(run, EV_VKM, 2050, "v1", uncertainty=GDP)
    for y in run.years:
        assert N.model_network(run, "emissions_transportation", y, "v1")["fields"][0]["values"]


def test_edges(run):
    c = N.model_network(run, f"L{CLINKER}", 2050, "v1")
    assert "not used to compute anything" in c["note"] and c["input_values"]["fields"]
    a, b, d = (N.model_network(run, n, 2050, "v0") for n in ("L35", "35", "lever 35"))
    assert a == b == d
    for bad, kw in (("not_a_node", {}), ("lever 57", {}), ("L35", {"lever": 57})):
        with pytest.raises(ToolError):
            N.model_network(run, bad, 2050, "v0", **kw)
    with pytest.raises(ToolError):
        N.model_network(run, "L35", 2030, "v0")
    assert json.dumps(N.model_network(run, "X57", 2035, "v1"), ensure_ascii=False)


def test_gdp_units_match_the_other_tools(run):
    from backend.rdm.surrogate import UNITS
    for arm in N.VERSIONS:
        assert N.model_network(run, "GDP", 2050, arm)["units"] == UNITS["gdp"]
