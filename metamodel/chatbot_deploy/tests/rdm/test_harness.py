"""
Tests for backend/rdm/harness/registry.py: the six tools as the agent sees them.

Test 1 — schemas: six tools, unique names, every required argument declared; one schema set
         serves both versions.
Test 2 — scripted flows, one per question category (A–E), in v0 and v1: every call succeeds,
         the technical replies are identical across versions, the information replies differ.
Test 3 — errors come back to the agent as {"error": …} and are logged with status "error".
Test 4 — the log records tool, arguments, status and reply for every call, and can be written to JSONL.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.harness.registry import TOOL_NAMES, TOOLS, Harness  # noqa: E402

LIGHT_DUTY, DEFOREST, GDP = 35, 15, 57
TECHNICAL = {"exploratory_modeling", "vulnerability_analysis", "scenario_discovery", "trade_off_analysis"}


def flows(h: Harness) -> list:
    """The expected flow per category (docs/archive/rdm_tools_design.md), scripted. Returns [(tool, reply)]."""
    out = []
    call = lambda n, a: out.append((n, h.call(n, a))) or out[-1][1]
    # A · information
    call("model_network", {"node": "transportation", "year": 2050})
    call("model_network", {"node": f"L{LIGHT_DUTY}", "year": 2050})
    call("model_network", {"node": "emissions_transportation", "lever": LIGHT_DUTY, "uncertainty": GDP, "third": "high",
                           "year": 2050})
    # B · evaluate a policy
    e = call("exploratory_modeling", {"policies": [{"name": "light duty", "levers": {LIGHT_DUTY: 0.8}}],
                                      "n_futures": 200})["ensemble_id"]
    call("vulnerability_analysis", {"ensemble_id": e, "policy": "light duty", "metric": "emissions_transportation",
                                    "year": 2050})
    # C / D · reach a target, robustness
    e = call("exploratory_modeling", {"policies": [{"name": "transport mix",
                                                    "levers": {LIGHT_DUTY: 1, 33: 1, 37: 1, 31: 1}}],
                                      "metrics": ["emissions_transportation", "cost_total"], "n_futures": 300})["ensemble_id"]
    call("vulnerability_analysis", {"ensemble_id": e, "policy": "transport mix", "metric": "emissions_transportation",
                                    "year": 2050, "threshold": 30, "threshold_type": "reduction_vs_bau_pct"})
    call("scenario_discovery", {"ensemble_id": e})
    # E · compare
    e = call("exploratory_modeling", {"policies": [{"name": "light duty", "levers": {LIGHT_DUTY: 1}},
                                                   {"name": "forests", "levers": {DEFOREST: 1}}],
                                      "x_ranges": {GDP: [0.7, 1.0]}, "n_futures": 200})["ensemble_id"]
    call("trade_off_analysis", {"ensemble_id": e, "year": 2050})
    return out


@pytest.fixture(scope="module")
def runs():
    try:
        return {v: (h := Harness(v), flows(h)) for v in ("v0", "v1")}
    except FileNotFoundError as e:
        pytest.skip(str(e))


def test_schemas():
    assert len(TOOLS) == 6 and len(set(TOOL_NAMES)) == 6
    for t in TOOLS:
        assert set(t["input_schema"]["required"]) <= set(t["input_schema"]["properties"]), t["name"]


def test_flows(runs):
    (h0, f0), (h1, f1) = runs["v0"], runs["v1"]
    assert all(e["status"] == "ok" for h in (h0, h1) for e in h.log), [e for e in h0.log + h1.log if e["status"] != "ok"]
    for (n0, r0), (n1, r1) in zip(f0, f1):
        assert n0 == n1
        if n0 in TECHNICAL:
            assert r0 == r1, n0
        else:
            assert r0 != r1, n0


def test_errors_are_returned_and_logged():
    h = Harness("v0")
    r = h.call("vulnerability_analysis", {"ensemble_id": "E99", "policy": "x", "metric": "emissions_total", "year": 2050})
    assert "error" in r and h.log[-1]["status"] == "error"
    assert "error" in h.call("no_such_tool", {})


def test_log(tmp_path, runs):
    h, _ = runs["v1"]
    assert [e["tool"] for e in h.log][:4] == ["model_network"] * 3 + ["exploratory_modeling"]
    assert all({"tool", "args", "status", "reply", "reply_chars"} <= set(e) for e in h.log)
    p = tmp_path / "log.jsonl"
    h2 = Harness("v1", log_path=p)
    h2.call("model_network", {"node": "transportation", "year": 2050})
    assert json.loads(p.read_text().splitlines()[0])["tool"] == "model_network"
