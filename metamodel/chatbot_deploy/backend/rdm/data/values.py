"""
The values table: how a lever's outputs look across its levels, when an uncertainty is low or high.

For each lever, the outputs are
  * the inventory **categories** whose emission fields the lever moves — as whole-category totals,
    the scale the surrogate reports (decision D9), and
  * the **in-between variables**: model_output variables the lever moves (lever → output mapping)
    that drive one of those categories (backend/rdm/links/drivers.py: per emission source, the 1–2
    variables that create it, or its group, at the last run year; listed once per category).

Cells: lever level low / mid / high (0–⅓, ⅓–⅔, ⅔–1) × uncertainty any / low (0–⅓) / high (⅔–1),
for each of the 13 uncertainties, at every anchor year. Each cell holds n, p10, median, p90 over
the runs in it, every other lever and uncertainty varying (values are marginal).

    python -m backend.rdm.data.values      → backend/rdm/data/tables/<run>_values.parquet

Built from the cached sample (4,989 runs) for development; the same code runs on the full store.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.runs import Run
from backend.rdm.tools import information as I

TABLES = Path(__file__).parent / "tables"
LINKS = Path(__file__).parents[1] / "links"
L_BINS = {"low": (0.0, 1 / 3), "mid": (1 / 3, 2 / 3), "high": (2 / 3, 1.0)}
X_BINS = {"low": (0.0, 1 / 3), "high": (2 / 3, 1.0)}
QUANTILES = [0.10, 0.50, 0.90]


def _in(v: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (v >= lo) & ((v < hi) if hi < 1 else (v <= hi))


def driver_categories(run: Run) -> dict:
    """variable → set of category slugs it drives (backend/rdm/links/drivers.py, the expert review file)."""
    d = pd.read_csv(LINKS / f"{run.name}_drivers_by_category.csv")
    return d.assign(slug=d.metric.str[len("emissions_"):]).groupby("variable").slug.apply(set).to_dict()


CHANNEL_ITEMS = 2      # the lever's own strongest variables (a family of siblings counts as one item)


def lever_channel(g: pd.DataFrame, year: int) -> list:
    """The variables this lever moves most (|Spearman ρ| at the last run year), so the agent sees how the lever
    acts even when those variables are not drivers of an emission source (e.g. the light-duty fuel split for
    lever 35, the landfill gas recovered for lever 50). Siblings that differ only in their last word
    (…_road_light_<fuel>) form one item and are kept together."""
    v = g[g.output_kind == "variable"].assign(a=lambda d: d[f"rho_{year}"].abs()).dropna(subset=["a"])
    if v.empty:
        return []
    v = v.assign(family=v.output_field.str.rsplit("_", n=1).str[0])
    size = v.groupby("family").output_field.transform("size")
    v = v.assign(item=v.family.where(size >= 2, v.output_field))
    top = v.groupby("item").a.max().sort_values(ascending=False).head(CHANNEL_ITEMS).index
    return sorted(v[v.item.isin(top)].output_field)


def lever_outputs(run: Run) -> dict:
    """lever id → {"categories": [slug…], "variables": [field…], "channel": [field…]}: what the values table
    covers. variables = drivers of the lever's categories (links/drivers.py) ∪ the lever's own channel."""
    m = I.links(run)
    var_cats = driver_categories(run)
    last = max(run.years)
    out = {}
    for lid, g in m[m.group_kind == "L"].groupby("group_id"):
        cats = sorted(set(g[g.output_kind == "emission"].category.dropna()))
        drivers = {f for f in g[g.output_kind == "variable"].output_field if var_cats.get(f, set()) & set(cats)}
        channel = lever_channel(g, last)
        out[int(lid)] = {"categories": cats, "variables": sorted(drivers | set(channel)), "channel": channel}
    return out


def build(run: Run, store: Store) -> pd.DataFrame:
    cover = lever_outputs(run)
    cw = I.crosswalk(run)
    design = store.design
    x_ids = [int(c[2:]) for c in design.columns if c.startswith("X_")]
    rows = []
    for y in run.years:
        cat_series = {c: store.total(cw[c]["fields"], y) for c in {c for v in cover.values() for c in v["categories"]}}
        for lid, cv in cover.items():
            outputs = [("category", c, cat_series[c]) for c in cv["categories"]] + \
                      [("variable", f, store.values(f, y)) for f in cv["variables"]]
            if not outputs:
                continue
            Y = pd.concat([s.rename(name) for _, name, s in outputs], axis=1)
            idx = Y.index.intersection(design.index)
            Y, D = Y.loc[idx].to_numpy(dtype=float), design.loc[idx]
            L = D[f"L_{lid}"].to_numpy()
            kinds = [k for k, _, _ in outputs]
            names = [n for _, n, _ in outputs]
            cells = [(0, "any", np.ones(len(idx), bool))]
            for x in x_ids:
                xv = D[f"X_{x}"].to_numpy()
                cells += [(x, b, _in(xv, *rng)) for b, rng in X_BINS.items()]
            for x, xb, xmask in cells:
                for lb, rng in L_BINS.items():
                    mask = xmask & _in(L, *rng)
                    sub = Y[mask]
                    n = (~np.isnan(sub)).sum(axis=0)
                    q = np.nanquantile(sub, QUANTILES, axis=0) if len(sub) else np.full((3, len(names)), np.nan)
                    for j, name in enumerate(names):
                        rows.append((lid, y, x, xb, lb, kinds[j], name, int(n[j]), q[0, j], q[1, j], q[2, j]))
    return pd.DataFrame(rows, columns=["lever_id", "year", "x_id", "x_bin", "lever_level", "kind", "output",
                                       "n", "p10", "median", "p90"])


def write(run: Run, store: Store) -> Path:
    TABLES.mkdir(exist_ok=True)
    path = TABLES / f"{run.name}_values.parquet"
    build(run, store).to_parquet(path, index=False)
    return path


def load(run: Run) -> pd.DataFrame:
    path = TABLES / f"{run.name}_values.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No values table {path.name}; run python -m backend.rdm.data.values")
    return pd.read_parquet(path)


if __name__ == "__main__":
    import time

    from backend.rdm.runs import get_run
    r = get_run()
    t = time.time()
    p = write(r, Store(r))
    df = pd.read_parquet(p)
    print(f"{p.name}: {len(df):,} rows in {time.time() - t:.0f}s")
