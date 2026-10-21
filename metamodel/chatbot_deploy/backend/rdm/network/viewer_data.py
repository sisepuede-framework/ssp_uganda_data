"""
Data for the network map (one year): the network with node attributes, and one file of ranges per lever.

    python -m backend.rdm.network.viewer_data [--year 2050] [--out DIR]
writes into DIR (default network/out/viewer/):
    network.json   nodes (attributes, fields), edges, what each lever and uncertainty reaches, each lever's own
                   inputs (exact: BAU, middle, top of the range run), constant inputs (one value), inputs set by
                   uncertainties (p10–median–p90, any / low / high)
    L<id>.json     the lever's ranges: per field, per uncertainty filter ("0:any", "<x>:low", "<x>:high"), per
                   lever level (low, mid, high): [p10, median, p90]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data import sample
from backend.rdm.data.store import Store
from backend.rdm.network.assemble import reach
from backend.rdm.runs import get_run
from backend.rdm.tools.common import groups

OUT = Path(__file__).parent / "out"
NEMOMOD = "NemoMod (electricity optimisation)"


def sig(x, n=4):
    return None if x is None or pd.isna(x) else float(f"{float(x):.{n}g}")


def build(run, year: int, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    p = lambda s: OUT / f"{run.name}_{s}"
    edges = pd.read_csv(p("edges.csv"))
    attrs = pd.read_csv(p("node_attributes.csv")).set_index("variable")
    fattrs = pd.read_csv(p("field_attributes.csv"))
    nodes_csv = pd.read_csv(p("nodes.csv")).set_index("id")
    g = groups(run)
    fwd = reach(edges)

    # nodes: every variable on the network, NemoMod and the 23 categories
    code = edges[edges.type != "sets"]
    ids = sorted(set(code.source) | set(code.target))
    index = {n: i for i, n in enumerate(ids)}
    fields_of = fattrs.groupby("variable")
    nodes = []
    for n in ids:
        if n == NEMOMOD:
            nodes.append({"id": n, "name": "NemoMod electricity optimisation", "kind": "box", "sector": "Energy",
                          "subsector": "Energy Technology"})
        elif n.startswith("C:"):
            nodes.append({"id": n, "name": nodes_csv.loc[n, "information"], "kind": "category"})
        else:
            a = attrs.loc[n] if n in attrs.index else None
            row = nodes_csv.loc[n] if n in nodes_csv.index else None
            d = {"id": n, "name": a["name"] if a is not None else n,
                 "kind": ("emission" if row is not None and row.get("is_emission") is True else
                          str(row["type"]).lower() if row is not None else "variable")}
            if a is not None:
                d.update({k: (None if pd.isna(a[k]) else a[k]) for k in
                          ("type", "sector", "subsector", "gas", "units", "xgboost_categories", "information")})
            if n in fields_of.groups:
                ff = fields_of.get_group(n)
                d["fields"] = [{"f": r.field, "cat": None if pd.isna(r.category) else r.category,
                                "unit": r.unit, "unit_source": r.unit_source,
                                "gas": None if pd.isna(r.gas) else r.gas,
                                "xgb": None if pd.isna(r.xgboost_category) else r.xgboost_category}
                               for r in ff.itertuples()]
            nodes.append(d)
    links = [[index[s], index[t]] for s, t in code[["source", "target"]].drop_duplicates().itertuples(index=False)]

    # what each lever and uncertainty sets and reaches
    sets = edges[edges.type == "sets"]
    lever_inputs = pd.read_csv(Path(__file__).parents[1] / "data" / "tables" / f"{run.name}_lever_inputs.csv")
    li = lever_inputs[(lever_inputs.year == year) & lever_inputs.changes]
    levers, xs = {}, {}
    for gid, info in sorted(g.items()):
        key = f"{info['kind']}{gid}"
        reached = sorted(index[v] for v in fwd(key) if v in index)
        own = sorted(index[v] for v in sets[sets.source == key].target if v in index)
        d = {"name": info["name"], "sector": info["sector"], "sets": own, "reach": reached}
        if info["kind"] == "L":
            d["own_inputs"] = [{"f": r.field, "unit": r.unit, "bau": sig(r.at_0), "mid": sig(r["at_0.5"]),
                                "top": sig(r.at_1), "level_top": r.level_high} for _, r in li[li.lever_id == gid].iterrows()]
            levers[gid] = d
        else:
            xs[gid] = d

    # inputs no lever sets: constants (one value) and those set by uncertainties (ranges by their own X)
    sd = sample.sample_dir(run, 5000, 0)
    fixed = pd.read_parquet(sd / "other_inputs_fixed.parquet").xs(year, level="year")
    constants = {c: sig(fixed[c].median()) for c in fixed.columns if fixed[c].nunique() <= 1}
    xin = pd.read_parquet(sd / "other_inputs_x.parquet").xs(year, level="year")
    design = Store(run).design
    xg = pd.read_csv(run.local("groups_x"))
    x_of = dict(zip(xg.variable, xg.variable_trajectory_group))
    x_inputs = {}
    for c in xin.columns:
        if c not in x_of:
            continue
        v = xin[c].dropna()
        xv = design.loc[v.index.intersection(design.index), f"X_{x_of[c]}"]
        v = v.loc[xv.index]
        q = lambda s: [sig(s.quantile(.1)), sig(s.median()), sig(s.quantile(.9))]
        x_inputs[c] = {"x": int(x_of[c]), "any": q(v), "low": q(v[xv < 1 / 3]),
                         "mid": q(v[(xv >= 1 / 3) & (xv < 2 / 3)]), "high": q(v[xv >= 2 / 3])}

    (out / "network.json").write_text(json.dumps(
        {"run": run.name, "year": year, "nodes": nodes, "links": links, "levers": levers, "uncertainties": xs,
         "constants": constants, "x_inputs": x_inputs}, ensure_ascii=False, separators=(",", ":")))

    # ranges, one file per lever
    r = pd.read_parquet(p("ranges.parquet"))
    r = r[(r.year == year) & (r.lever_id > 0)]      # lever 0 (no lever split) is for the agent's tool
    for lid, gl in r.groupby("lever_id", observed=True):
        flds = sorted(gl.field.astype(str).unique())
        pos = {f: i for i, f in enumerate(flds)}
        cells = {}
        for (xid, xb, lv), gc in gl.groupby(["x_id", "x_bin", "lever_level"], observed=True):
            arr = cells.setdefault(f"{xid}:{xb}", {}).setdefault(lv, [None] * len(flds))
            for f, a, b, c in zip(gc.field.astype(str), gc.p10, gc["median"], gc.p90):
                arr[pos[f]] = [sig(a), sig(b), sig(c)]
        (out / f"L{lid}.json").write_text(json.dumps({"fields": flds, "cells": cells}, separators=(",", ":")))

    sizes = sorted((f.stat().st_size for f in out.glob("L*.json")), reverse=True)
    print(f"network.json {(out / 'network.json').stat().st_size / 1e6:.2f} MB · {len(nodes)} nodes · {len(links)} links")
    print(f"{len(sizes)} lever files · largest {sizes[0] / 1e6:.1f} MB · total {sum(sizes) / 1e6:.1f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2050)
    ap.add_argument("--out", type=Path, default=OUT / "viewer")
    a = ap.parse_args()
    build(get_run(), a.year, a.out)
