"""
Tests for the lever input values (backend/rdm/data/lever_inputs.py).

Test 1 — the rule: in every sampled run, each stored lever input equals BASE + L × (HBLE − BASE) at
         2050 and 2070 (error < 1% of the BASE–HBLE range). Skipped without the cached inputs
         (python -m backend.rdm.data.inputs, one Athena scan of model_input).
Test 2 — the table: every lever input field (527) has a row per year; at_0.5 lies between at_0 and at_1.
Test 3 — the ends of each lever's range are read from the run, not from constants.
Test 4 — the table (fitted on the experiment's runs) matches the fixed pathway runs within 1% of the range.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.data import groups, lhc  # noqa: E402
from backend.rdm.data.inputs import load_inputs  # noqa: E402
from backend.rdm.data.lever_inputs import build, pathway_values  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402


@pytest.fixture(scope="module")
def run():
    return get_run()


def test_rule_matches_model_input(run):
    try:
        inp = load_inputs(run)
    except FileNotFoundError as e:
        pytest.skip(str(e))
    design = lhc.load_design(run)
    # A field can be listed under several transformations of one lever (lever 15), never under two levers.
    owner = groups.lever_groups(run).assign(f=lambda d: d.variable_field.str.lower()).drop_duplicates("f").set_index("f").group_id
    vals = pathway_values(run, list(inp.columns))
    checked = 0
    for f in inp.columns:
        for y in (2050, 2070):
            b, h = vals.loc[(f, y)]
            if abs(h - b) <= 1e-12 * max(1, abs(b)):
                continue
            obs = inp.xs(y, level="year")[f]
            pred = b + design.loc[obs.index, f"L_{owner[f]}"] * (h - b)
            assert np.max(np.abs(obs - pred)) < 0.01 * abs(h - b), (f, y)
            checked += 1
    assert inp.shape[1] == 527 and checked > 950


def test_table(run):
    t = build(run)
    assert t.field.nunique() == 527 and set(t.year) == {2050, 2070}
    lo, hi = t[["at_0", "at_1"]].min(axis=1), t[["at_0", "at_1"]].max(axis=1)
    assert ((t["at_0.5"] >= lo - 1e-9) & (t["at_0.5"] <= hi + 1e-9)).all()


def test_experiment_read_from_run(run):
    """The two ends of every lever come from the run's files, not from constants."""
    base, full, name = lhc.experiment_strategies(run)
    assert (base, full, name) == (0, 6007, "HBLE")
    bounds = lhc.lever_bounds(run)
    assert len(bounds) == 54 and set(bounds.values()) == {(0.0, 1.0)}


def test_experiment_table_matches_fixed_runs(run):
    """What the agent sees comes from the experiment's runs; the fixed pathway runs only confirm it."""
    t = build(run)
    t = t[t.field.isin(load_inputs(run).columns)]
    pv = pathway_values(run, sorted(t.field.unique()))
    for r in t.itertuples():
        b, h = pv.loc[(r.field, r.year)]
        rng = max(abs(h - b), 1e-9)
        assert abs(r.at_0 - b) < 0.01 * rng + 1e-9 and abs(r.at_1 - h) < 0.01 * rng + 1e-9, (r.field, r.year)
