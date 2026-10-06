"""
Tests for backend/rdm/data: group definitions and the LHC design of the active run.

Test 1 — groups: lever and uncertainty ids are disjoint and come from the run's files;
         lever 35 sets the light-duty fuel shares; lever 15 bundles several transformations.
Test 2 — design: one row per run with LHC values, every L and X column present and in [0, 1];
         runs without an LHC row and LHC columns without a group are reported, not hidden.
Test 3 — design join: a run checked by hand on 2026-10-06 (primary_id 25300452 → future 199,
         L35 ≈ 0.911) comes back with that value.
"""

import sys
from pathlib import Path

_CHATBOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_CHATBOT_DIR))

from backend.rdm.data import groups, lhc  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402

RUN = get_run()


def test_groups_come_from_the_run():
    L, X = groups.lever_ids(RUN), groups.uncertainty_ids(RUN)
    assert L and X and not set(L) & set(X)
    assert groups.group_kind(RUN, L[0]) == "L" and groups.group_kind(RUN, X[0]) == "X"

    fuel_shares = groups.input_variables(RUN, 35)
    assert "frac_trns_fuelmix_road_light_electricity" in fuel_shares
    assert all(v.startswith("frac_trns_fuelmix_road_light_") for v in fuel_shares)
    assert len(groups.transformations(RUN, 15)) > 1


def test_design_has_every_group_in_range():
    design = lhc.load_design(RUN)
    cols = lhc.lever_columns(RUN) + lhc.uncertainty_columns(RUN)
    assert set(cols) <= set(design.columns)
    values = design[cols]
    assert values.notna().all().all()
    assert ((values >= 0) & (values <= 1)).all().all()
    assert design.index.is_unique

    report = lhc.design_report(RUN)
    assert report.n_runs_in_design == len(design)
    assert report.n_runs_in_design + len(report.runs_without_lhc) == report.n_runs_total


def test_design_join_matches_a_hand_checked_run():
    row = lhc.load_design(RUN).loc[25300452]
    assert row.future_id == 199
    assert abs(row.L_35 - 0.911412) < 1e-6
