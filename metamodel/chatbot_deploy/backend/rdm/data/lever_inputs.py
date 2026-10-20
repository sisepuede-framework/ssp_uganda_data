"""
What each lever level means in real terms: the values of the input fields a lever sets.

Read from the experiment's own runs (model_input, the cached sample): for each field and year, the value
is a straight line in the lever's level, fitted over the runs. The table gives that line at the bottom
of the range explored in the runs (BAU), its middle and its top — the most ambitious level the
experiment ran. The range comes from the run's design (lhc.lever_bounds), never from a constant.

Cross-check (tests/rdm/test_inputs.py): the line is BASE + L × (HBLE − BASE), with BASE and HBLE the
two fixed pathway runs of the strategy the experiment scales. Exact on all 527 fields, 2050 and 2070
(2026-10-19: worst error 0.4% of the range), with no dependence on X. The fixed runs are only that
check; nothing the agent sees comes from them.

    python -m backend.rdm.data.lever_inputs   → backend/rdm/data/tables/<run>_lever_inputs.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data import groups, lhc
from backend.rdm.runs import Run
from backend.rdm.tools.common import groups as group_names

TABLES = Path(__file__).parent / "tables"
YEARS = (2050, 2070)


def pathway_values(run: Run, fields: list, years=YEARS) -> pd.DataFrame:
    """BASE and HBLE values of the fields in the fixed pathway runs (the cross-check only):
    index (field, year), columns base, full."""
    pp = pd.read_csv(run.run_dir / "pathways/ATTRIBUTE_PRIMARY.csv")
    pid = dict(zip(pp.strategy_id, pp.primary_id))
    path = pd.read_csv(run.run_dir / "pathways/uganda_pathways.csv")
    path.columns = path.columns.str.lower()
    path = path.assign(year=path.time_period + 2015)
    path = path[path.year.isin(years)]
    base_id, full_id, _ = lhc.experiment_strategies(run)     # in the 2026-05-30 run: 0 (BASE) and 6007 (HBLE)
    out = []
    for name, sid in (("base", base_id), ("full", full_id)):
        rows = path[path.primary_id == pid[sid]].set_index("year")[fields]
        out.append(rows.stack().rename(name))
    df = pd.concat(out, axis=1)
    df.index.names = ["year", "field"]
    return df.swaplevel().sort_index()


def experiment_values(run: Run, years=YEARS) -> pd.DataFrame:
    """Each lever input field at the bottom, middle and top of its lever's explored range, from a straight
    line fitted over the experiment's runs: index (field, year), columns low, mid, high."""
    from backend.rdm.data.inputs import load_inputs
    inp, design, bounds = load_inputs(run), lhc.load_design(run), lhc.lever_bounds(run)
    # A field can be listed under several transformations of one lever (lever 15), never under two levers.
    owner = groups.lever_groups(run).assign(f=lambda d: d.variable_field.str.lower()).drop_duplicates("f").set_index("f").group_id
    rows = []
    for y in years:
        x = inp.xs(y, level="year")
        for f in x.columns:
            lid = owner[f]
            slope, icpt = np.polyfit(design.loc[x.index, f"L_{lid}"].to_numpy(), x[f].to_numpy(), 1)
            lo, hi = bounds[lid]
            rows.append({"field": f, "year": y, "low": icpt + slope * lo, "mid": icpt + slope * (lo + hi) / 2,
                         "high": icpt + slope * hi})
    return pd.DataFrame(rows).set_index(["field", "year"]).sort_index()


def build(run: Run, years=YEARS) -> pd.DataFrame:
    g = groups.lever_groups(run).assign(field=lambda d: d.variable_field.str.lower())
    vals = experiment_values(run, years)
    bounds = lhc.lever_bounds(run)
    from backend.rdm.tools.information import unit
    names = group_names(run)
    rows = []
    for r in g.itertuples():
        for y in years:
            lo, mid, hi = vals.loc[(r.field, y)]
            rows.append({"lever_id": r.group_id, "lever": names[r.group_id]["name"], "transformation": r.transformation_code,
                         "field": r.field, "variable": r.variable, "unit": unit(r.field), "year": y,
                         "level_low": bounds[r.group_id][0], "level_high": bounds[r.group_id][1],
                         "at_0": lo, "at_0.5": mid, "at_1": hi,
                         # a fitted line is never exactly flat: fields the lever does not move have |slope| ~ 1e-17
                         "changes": abs(hi - lo) > 1e-9 * max(1, abs(lo))})
    return pd.DataFrame(rows)


def write(run: Run) -> Path:
    TABLES.mkdir(exist_ok=True)
    path = TABLES / f"{run.name}_lever_inputs.csv"
    build(run).to_csv(path, index=False)
    return path


if __name__ == "__main__":
    from backend.rdm.runs import get_run
    print(write(get_run()))
