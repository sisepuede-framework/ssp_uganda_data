"""
Tests for backend/rdm/surrogate.py: the XGBoost pipeline read through the run manifest, batched.

Test 1 — wiring: every surrogate feature maps to a registry group; 258 targets; the 23 emission
         categories are exactly the crosswalk's.
Test 2 — derived totals: emissions_total is the sum of the 23 categories; cost_total flips the sign
         of the 3 cost types; the same design gives the same predictions.
Test 3 — direction: every lever at 1 gives lower total emissions than every lever at 0, in every future.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.runs import get_run  # noqa: E402
from backend.rdm.surrogate import get_surrogate  # noqa: E402


@pytest.fixture(scope="module")
def sur():
    try:
        return get_surrogate(get_run())
    except FileNotFoundError as e:
        pytest.skip(str(e))


def design(sur, lever_level, n=200, seed=0):
    rng = np.random.default_rng(seed)
    d = {f"X_{x}": rng.random(n) for x in sur.x_ids}
    d.update({f"L_{l}": np.full(n, lever_level) for l in sur.lever_ids})
    return pd.DataFrame(d)


def test_wiring(sur):
    assert len(sur.features) == len(sur.lever_ids) + len(sur.x_ids) == 67
    assert len(sur.targets) == 258
    assert sur.categories == sorted(json.loads(sur.run.crosswalk.read_text()))
    assert len(sur.categories) == 23 and sur.years == list(sur.run.years)


def test_derived_totals(sur):
    d = design(sur, 0.5)
    p = sur.predict(d)
    cats = p[[f"emission_{c}_yr2050" for c in sur.categories]].sum(axis=1)
    assert np.allclose(p["emissions_total_yr2050"], cats, rtol=1e-5)
    costs = p[[f"cost_{c}_yr2050" for c in sur.cost_types]].sum(axis=1)
    assert np.allclose(p["cost_total_yr2050"], costs, rtol=1e-5)     # cost types already flipped: money spent > 0
    raw = sur.model.predict(pd.DataFrame(d[sur._design_col].to_numpy(dtype=float), columns=sur.features))
    i = sur.targets.index("cost_technical_yr2050")
    assert np.allclose(p["cost_technical_yr2050"], -raw[:, i], rtol=1e-5)
    assert p.equals(sur.predict(d))


def test_direction(sur):
    low, high = sur.predict(design(sur, 0.0)), sur.predict(design(sur, 1.0))
    assert (high["emissions_total_yr2050"] < low["emissions_total_yr2050"]).all()
