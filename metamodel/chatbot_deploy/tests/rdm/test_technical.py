"""
Tests for backend/rdm/tools/technical.py: the four technical tools on the surrogate.

Test 1 — exploratory_modeling: same seed → same ensemble; BAU is added on the same futures and every
         change is paired; restricted uncertainty ranges are respected.
Test 2 — rules in code: lever out of [0, 1], unknown ids, an uncertainty fixed at one value, a policy
         called BAU and too few futures are refused.
Test 3 — vulnerability_analysis: without a threshold it asks for one; thresholds beyond the range give
         0 or 1 failure; reduction-vs-BAU agrees with the change exploratory_modeling reports.
Test 4 — scenario_discovery: refuses before labels exist; finds a planted failure rule (high GDP
         and high population) with the right pair and a dense box; reports nothing when nothing fails.
Test 5 — trade_off_analysis: shares in [0, 1]; a policy with more emissions and more cost than another
         on the medians is reported dominated.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.harness.registry import Harness  # noqa: E402
from backend.rdm.harness.state import State  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402
from backend.rdm.surrogate import get_surrogate  # noqa: E402
from backend.rdm.tools import technical as T  # noqa: E402
from backend.rdm.tools.common import ToolError  # noqa: E402

GDP, POP = 57, 60


@pytest.fixture(scope="module")
def sur():
    try:
        return get_surrogate(get_run())
    except FileNotFoundError as e:
        pytest.skip(str(e))


def run(sur, state=None, **kw):
    state = state or State()
    kw.setdefault("policies", [{"name": "half", "levers": {i: 0.5 for i in sur.lever_ids}},
                               {"name": "light", "levers": {35: 0.8}}])
    kw.setdefault("n_futures", 200)
    return state, T.exploratory_modeling(state, sur, **kw)


def test_exploratory_modeling(sur):
    s1, a = run(sur)
    _, b = run(sur)
    assert a["results"] == b["results"]
    ens = s1.get(a["ensemble_id"])
    assert set(ens.policies) == {"BAU", "half", "light"}
    col = "emissions_total_yr2050"
    diff = ens.predictions["half"][col] - ens.predictions["BAU"][col]
    assert a["results"]["emissions_total"]["by_year"]["2050"]["half"]["change_vs_bau"]["median"] == round(float(diff.median()), 3)
    s2, c = run(sur, x_ranges={GDP: [0.7, 1.0]})
    xs = s2.get(c["ensemble_id"]).futures[f"X_{GDP}"]
    assert xs.min() >= 0.7 and xs.max() <= 1.0


@pytest.mark.parametrize("kw", [
    {"policies": [{"name": "p", "levers": {35: 1.4}}]},
    {"policies": [{"name": "p", "levers": {999: 0.5}}]},
    {"policies": [{"name": "p", "levers": {GDP: 0.5}}]},
    {"policies": [{"name": "BAU", "levers": {35: 0.5}}]},
    {"x_ranges": {GDP: [0.5, 0.5]}},
    {"x_ranges": {35: [0.1, 0.9]}},
    {"n_futures": 10},
])
def test_rules(sur, kw):
    with pytest.raises(ToolError):
        run(sur, **kw)


def test_vulnerability_analysis(sur):
    st, a = run(sur)
    e = a["ensemble_id"]
    ask = T.vulnerability_analysis(st, sur, e, "half", "emissions_total", 2050)
    assert ask["status"] == "needs_threshold" and "ask_the_user" in ask
    assert T.vulnerability_analysis(st, sur, e, "half", "emissions_total", 2050, threshold=1e6)["share_fail"] == 0
    assert T.vulnerability_analysis(st, sur, e, "half", "emissions_total", 2050, threshold=0)["share_fail"] == 1
    med_pct = -a["results"]["emissions_total"]["by_year"]["2050"]["half"]["change_vs_bau_pct"]["median"]
    v = T.vulnerability_analysis(st, sur, e, "half", "emissions_total", 2050, threshold=med_pct,
                                 threshold_type="reduction_vs_bau_pct")
    assert 0.4 <= v["share_fail"] <= 0.6
    with pytest.raises(ToolError):
        T.vulnerability_analysis(st, sur, e, "nope", "emissions_total", 2050, threshold=1)


def test_scenario_discovery(sur):
    st, a = run(sur, n_futures=1000)
    e = a["ensemble_id"]
    with pytest.raises(ToolError):
        T.scenario_discovery(st, sur, e)
    ens = st.get(e)
    fail = (ens.futures[f"X_{GDP}"] > 0.7) & (ens.futures[f"X_{POP}"] > 0.5)
    ens.labels["planted"] = {"policy": "half", "metric": "emissions_total", "year": 2050, "threshold": 0,
                             "threshold_type": "absolute", "pass_if": "below", "fail": fail}
    d = T.scenario_discovery(st, sur, e, "planted")
    assert {p["id"] for p in d["pair"]} == {GDP, POP}
    assert d["failure_boxes"][0]["density"] > 0.9 and d["how_well_explained"]["pair"] > 0.95
    assert len(d["pass_rate_map"]["pass_rate"]) == 4
    T.vulnerability_analysis(st, sur, e, "half", "emissions_total", 2050, threshold=1e6)
    assert T.scenario_discovery(st, sur, e)["status"] == "nothing_to_discover"


def test_trade_off_analysis(sur):
    st, a = run(sur)
    t = T.trade_off_analysis(st, sur, a["ensemble_id"], 2050)
    for p in t["pairwise"]:
        assert all(0 <= p[k] <= 1 for k in p if k.startswith("share"))
    st.get(a["ensemble_id"]).predictions["worse"] = st.get(a["ensemble_id"]).predictions["half"] + 1.0
    st.get(a["ensemble_id"]).policies["worse"] = {}
    t = T.trade_off_analysis(st, sur, a["ensemble_id"], 2050, ["half", "worse"])
    assert t["dominated_on_medians"] == ["worse"]


def test_money_only_as_change_vs_bau():
    """Costs and benefits: no levels, only changes vs BAU; thresholds only as a change; sensible pass direction."""
    h = Harness("v0")
    r = h.call("exploratory_modeling", {"policies": [{"name": "gas", "levers": {"50": 0.688}}],
                                        "metrics": ["cost_total", "net_benefit", "cost_pct_gdp"], "n_futures": 200,
                                        "years": [2050]})
    row = r["results"]["cost_total"]["by_year"]["2050"]
    assert "BAU" not in row and set(row["gas"]) == {"change_vs_bau"}
    assert r["results"]["cost_pct_gdp"]["unit"] == "percentage points of GDP"
    e = r["ensemble_id"]
    bad = h.call("vulnerability_analysis", {"ensemble_id": e, "policy": "gas", "metric": "cost_total", "year": 2050,
                                            "threshold": 1.0, "threshold_type": "absolute"})
    assert "error" in bad
    ok = h.call("vulnerability_analysis", {"ensemble_id": e, "policy": "gas", "metric": "cost_total", "year": 2050,
                                           "threshold": 0.5})
    assert "below" in ok["criterion"] and "change vs BAU" in ok["unit"]
    nb = h.call("vulnerability_analysis", {"ensemble_id": e, "policy": "gas", "metric": "net_benefit", "year": 2050,
                                           "threshold": 0.0})
    assert "above" in nb["criterion"]
    t = h.call("trade_off_analysis", {"ensemble_id": e, "year": 2050})
    assert "cost" not in t["policies"]["gas"] and "net_benefit_change_vs_bau" in t["policies"]["gas"]
