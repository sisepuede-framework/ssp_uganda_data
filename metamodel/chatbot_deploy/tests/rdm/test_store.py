"""
Tests for backend/rdm/data/store.py: the (L_i, X_j) object over the cached sample.

Test 1 — fields: emissions and variables are told apart; an unknown field or year is rejected.
Test 2 — curve: bins cover [0, 1], every run lands in one bin, quantiles are ordered.
Test 3 — pair: a 5 × 5 grid whose cells add up to the runs with that output.
Test 4 — direction (checked by hand on 2026-10-06): electric light-duty vehicle-km in 2050
         rises with lever 35, and transport emissions fall with it.

Skipped when the cached sample has not been built (python -m backend.rdm.data.sample).
"""

import sys
from pathlib import Path

import pytest

_CHATBOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_CHATBOT_DIR))

from backend.rdm.data.store import Store  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402

EV_VKM = "vehicle_distance_traveled_trns_road_light_electricity"
TRNS = "emission_co2e_subsector_total_trns"


@pytest.fixture(scope="module")
def store():
    try:
        return Store(get_run())
    except FileNotFoundError as e:
        pytest.skip(str(e))


def test_fields_and_years(store):
    assert store.kind(TRNS) == "emission" and store.kind(EV_VKM) == "variable"
    with pytest.raises(KeyError):
        store.kind("not_a_field")
    with pytest.raises(ValueError):
        store.values(EV_VKM, 2030)


def test_curve_covers_the_range(store):
    c = store.curve(35, EV_VKM, 2050)
    assert c["from"].iloc[0] == 0.0 and c["to"].iloc[-1] == 1.0
    assert c.n.sum() == len(store.values(EV_VKM, 2050))
    assert (c.p10 <= c["median"]).all() and (c["median"] <= c.p90).all()


def test_pair_grid_adds_up(store):
    p = store.pair(35, 57, EV_VKM, 2050)
    assert len(p) == 25
    assert p.n.sum() == len(store.values(EV_VKM, 2050))


def test_lever_35_direction(store):
    ev = store.curve(35, EV_VKM, 2050)["median"]
    em = store.curve(35, TRNS, 2050)["median"]
    assert ev.is_monotonic_increasing and ev.iloc[-1] > ev.iloc[0] * 1.2
    assert em.iloc[-1] < em.iloc[0]
