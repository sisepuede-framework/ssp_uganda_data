"""
Node ranges for the network filter: for each lever, the values of every field it reaches in the network,
by lever level and by each uncertainty that also reaches the field, low, middle or high.

  lever level   low / mid / high = 0–⅓ / ⅓–⅔ / ⅔–1 of the lever's 0–1 range
  x filter      any (x_id 0), or one uncertainty in its bottom (low), middle (mid) or top (high) third. Only for the
                uncertainties with a path to the field in the network: one with no path does not move it, so
                the viewer shows the "any" values for it.
  cell          n, p10, median, p90 over the sampled runs in it, in the field's own units; every other lever
                and uncertainty varies (values are marginal)
  lever 0       no lever split (lever_level "all"): every field on the network, for a variable asked about
                without a lever
  categories    each XGBoost category also as a field, emissions_<slug>: the sum of its emission fields per run

The lever's own input fields are exact (a straight line in the lever level) and come from the lever inputs
table, not from here. Values come from the local sample (4,989 runs), with the input fields no lever sets read
by other_inputs.py (the constant ones have one value and are not here).

    python -m backend.rdm.network.ranges [--years 2050 2070]   (default: every anchor year)
                                                                → network/out/<run>_ranges.parquet
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data import sample
from backend.rdm.data.store import Store
from backend.rdm.network.assemble import reach
from backend.rdm.runs import get_run
from backend.rdm.tools.information import crosswalk

OUT = Path(__file__).parent / "out"
L_BINS = {"low": (0.0, 1 / 3), "mid": (1 / 3, 2 / 3), "high": (2 / 3, 1.0)}
X_BINS = {"low": (0.0, 1 / 3), "mid": (1 / 3, 2 / 3), "high": (2 / 3, 1.0)}     # every run falls in one


def _in(v: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (v >= lo) & ((v < hi) if hi < 1 else (v <= hi))


def values(run) -> pd.DataFrame:
    """Every cached field, one column each, index (primary_id, year)."""
    emissions, variables = sample.load_sample(run, 5000, 0)
    d = sample.sample_dir(run, 5000, 0)
    inputs = pd.read_parquet(d / "inputs.parquet")
    other = pd.read_parquet(d / "other_inputs_x.parquet")     # set by uncertainties, or varying (other_inputs.py)
    other = other[[c for c in other.columns if c not in inputs.columns]]
    return pd.concat([emissions, variables, inputs, other], axis=1)


def build(run, years: list) -> pd.DataFrame:
    edges = pd.read_csv(OUT / f"{run.name}_edges.csv")
    fields = pd.read_csv(OUT / f"{run.name}_fields.csv")
    fwd = reach(edges)
    store = Store(run)
    design = store.design
    vals = values(run)
    vals = vals[~vals.index.get_level_values("primary_id").isin(store.broken_runs)]
    cats = {f"emissions_{slug}": vals[[f for f in c["fields"] if f in vals.columns]].sum(axis=1, min_count=1)
            for slug, c in crosswalk(run).items()}
    vals = pd.concat([vals, pd.DataFrame(cats)], axis=1)
    by_var = fields[fields.field.isin(vals.columns)].groupby("variable").field.apply(list).to_dict()
    by_var.update({f"C:{c[len('emissions_'):]}": [c] for c in cats})
    groups = set(edges[edges.type == "sets"].source)
    levers = sorted((g for g in groups if g[0] == "L"), key=lambda s: int(s[1:]))
    xs = sorted((g for g in groups if g[0] == "X"), key=lambda s: int(s[1:]))
    x_reach = {x: fwd(x) for x in xs}

    rows = []
    for y in years:
        vy = vals.xs(y, level="year")
        idx = vy.index.intersection(design.index)
        vy, d = vy.loc[idx], design.loc[idx]
        everything = (0, None, [v for v in by_var], {"all": np.ones(len(idx), bool)})
        for lever in [everything] + levers:
            if lever is everything:
                lid, _, reached, levels = everything
            else:
                lid = int(lever[1:])
                own = set(edges[(edges.source == lever) & (edges.type == "sets")].target)
                reached = [v for v in fwd(lever) if v in by_var and v not in own]
                L = d[f"L_{lid}"].to_numpy()
                levels = {lb: _in(L, *r) for lb, r in L_BINS.items()}
            if not reached:
                continue
            for v in reached:
                cols = by_var[v]
                Y = vy[cols].to_numpy(dtype=float)
                cells = [(0, "any", np.ones(len(idx), bool))]
                for x in xs:
                    if v in x_reach[x]:
                        xv = d[f"X_{x[1:]}"].to_numpy()
                        cells += [(int(x[1:]), b, _in(xv, *r)) for b, r in X_BINS.items()]
                for xid, xb, xm in cells:
                    for lb, lm in levels.items():
                        sub = Y[xm & lm]
                        if not len(sub):
                            continue
                        q = np.nanquantile(sub, [0.1, 0.5, 0.9], axis=0)
                        n = (~np.isnan(sub)).sum(axis=0)
                        rows += [(lid, y, xid, xb, lb, c, int(n[j]), q[0, j], q[1, j], q[2, j])
                                 for j, c in enumerate(cols)]
    df = pd.DataFrame(rows, columns=["lever_id", "year", "x_id", "x_bin", "lever_level", "field", "n",
                                     "p10", "median", "p90"])
    for c in ("x_bin", "lever_level", "field"):
        df[c] = df[c].astype("category")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+")
    a = ap.parse_args()
    run = get_run()
    df = build(run, a.years or list(run.years))
    p = OUT / f"{run.name}_ranges.parquet"
    df.to_parquet(p, index=False)
    print(f"{p.name}: {len(df):,} rows · {df.field.nunique()} fields · {df.lever_id.nunique()} levers · "
          f"{p.stat().st_size / 1e6:.1f} MB")
    print("runs per cell (any X): median", int(df[df.x_id == 0].n.median()),
          "· with one X low, mid or high: median", int(df[df.x_id > 0].n.median()), "· min", int(df.n.min()))
