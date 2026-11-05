"""
Compare the network's values (computed on the 4,989-run sample) with the same values on every run of the experiment.

Same rules as ranges.py: same fields, cells, thirds and quantiles; a run with a rare 1e10 fill value is dropped whole.
The sample's ranges file defines which cells are computed, so the two tables line up one to one. Nothing the agent
reads is changed: results go to <cache_dir>/full_100k/ and results_analysis/sample_vs_100k.xlsx.

    AWS_PROFILE=alexa python -m backend.rdm.network.compare_full query     # one scan of 3 tables, about $1.46, once
    python -m backend.rdm.network.compare_full compute                     # no AWS
"""

import json
import multiprocessing as mp
import sys
import time

import numpy as np
import pandas as pd

from backend.rdm.data import athena, lhc, sample
from backend.rdm.data.inputs import BASE_YEAR, ensure_table
from backend.rdm.data.store import RARE_SHARE, SENTINEL
from backend.rdm.network.ranges import L_BINS, X_BINS, OUT, _in, crosswalk
from backend.rdm.runs import get_run

_W = {}


def out_dir(run):
    d = run.cache_dir / "full_100k"
    d.mkdir(exist_ok=True)
    return d


def query(run):
    """One Athena query per table. The result location is saved first, so a later failure never pays twice."""
    d = sample.sample_dir(run, 5000, 0)
    tps = ", ".join(str(y - BASE_YEAR) for y in run.years)
    out = out_dir(run)
    uris = json.loads((out / "uris.json").read_text()) if (out / "uris.json").exists() else {}
    inp = list(pd.read_parquet(d / "inputs.parquet").columns)
    oth = list(pd.read_parquet(d / "other_inputs_x.parquet").columns)
    cols = {"emissions": list(pd.read_parquet(d / "emissions.parquet").columns),
            "variables": list(pd.read_parquet(d / "variables.parquet").columns),
            "inputs": sorted(set(inp) | set(oth))}
    ensure_table(run)
    for role, c in cols.items():
        if role not in uris:
            quoted = ", ".join(f'"{x}"' for x in c)
            sql = (f"SELECT primary_id, time_period, {quoted} FROM {run.table(role)} "
                   f"WHERE region = '{run.region}' AND time_period IN ({tps})")
            uris[role] = athena.execute(run, sql, f"full_{role}")
            (out / "uris.json").write_text(json.dumps(uris, indent=1))
        if not all((out / f"{role}_{y}.parquet").exists() for y in run.years):
            t0 = time.time()
            df = athena.read_csv_uri(uris[role])
            df["year"] = df.time_period + BASE_YEAR
            print(f"[{role}] read {df.shape} in {time.time() - t0:.0f} s", flush=True)
            for y, g in df.groupby("year"):
                g.drop(columns=["time_period", "year"]).set_index("primary_id").sort_index().to_parquet(out / f"{role}_{y}.parquet")
            del df


def assemble(run):
    """Per year: one float array of runs x fields, with the same cleaning as the sample. Returns the runs kept."""
    out = out_dir(run)
    design = lhc.load_design(run)
    if (out / "kept.json").exists():
        return json.loads((out / "kept.json").read_text())
    hits, complete, n_seen = {}, None, set()
    for role in ("emissions", "variables"):
        for y in run.years:
            f = pd.read_parquet(out / f"{role}_{y}.parquet")
            f = f[f.index.isin(design.index)]
            n_seen |= set(f.index)
            complete = set(f.index) if complete is None else complete & set(f.index)
            mask = (f == SENTINEL)
            for c in mask.columns[mask.any().to_numpy()]:
                hits.setdefault(c, set()).update(f.index[mask[c].to_numpy()])
            del f, mask
    rare = {c: ids for c, ids in hits.items() if len(ids) < RARE_SHARE * len(n_seen)}
    broken = sorted({int(i) for ids in rare.values() for i in ids})
    keep = sorted(complete - set(broken))
    print(f"runs seen {len(n_seen)}, complete {len(complete)}, broken {len(broken)}, kept {len(keep)}; "
          f"sample dropped: see Store.broken_runs", flush=True)
    cw = crosswalk(run)
    for y in run.years:
        parts = [pd.read_parquet(out / f"{r}_{y}.parquet").reindex(keep) for r in ("emissions", "variables", "inputs")]
        v = pd.concat(parts, axis=1)
        v = v.loc[:, ~v.columns.duplicated()]
        cats = {f"emissions_{slug}": v[[f for f in c["fields"] if f in v.columns]].sum(axis=1, min_count=1) for slug, c in cw.items()}
        v = pd.concat([v, pd.DataFrame(cats)], axis=1)
        np.save(out / f"values_{y}.npy", v.to_numpy(dtype=float))
        (out / f"columns_{y}.json").write_text(json.dumps(list(v.columns)))
        print(f"[assemble] {y} {v.shape}", flush=True)
        del v, parts
    design.loc[keep].to_parquet(out / "design_kept.parquet")
    info = {"seen": len(n_seen), "complete": len(complete), "broken": len(broken), "kept": len(keep)}
    (out / "kept.json").write_text(json.dumps(info))
    return info


def _init(path, cols, design):
    _W["v"] = np.load(path, mmap_mode="r")
    _W["i"] = {c: k for k, c in enumerate(cols)}
    _W["d"] = design


def _cell(args):
    lid, xid, xb, lb, fields = args
    d = _W["d"]
    m = np.ones(len(d), bool)
    if lid:
        m &= _in(d[f"L_{lid}"].to_numpy(), *L_BINS[lb])
    if xid:
        m &= _in(d[f"X_{xid}"].to_numpy(), *X_BINS[xb])
    fields = [f for f in fields if f in _W["i"]]
    if not fields or not m.any():
        return []
    Y = np.asarray(_W["v"][m][:, [_W["i"][f] for f in fields]], dtype=float)
    n = (~np.isnan(Y)).sum(axis=0)
    q = np.full((3, Y.shape[1]), np.nan)
    ok = n > 0
    if ok.any():
        q[:, ok] = np.nanquantile(Y[:, ok], [0.1, 0.5, 0.9], axis=0)
    return [(lid, xid, xb, lb, f, int(n[j]), q[0, j], q[1, j], q[2, j]) for j, f in enumerate(fields)]


def compute(run):
    out = out_dir(run)
    info = assemble(run)
    print(info, flush=True)
    design = pd.read_parquet(out / "design_kept.parquet")
    sam = pd.read_parquet(OUT / f"{run.name}_ranges.parquet")
    for y in run.years:
        target = out / f"full_ranges_{y}.parquet"
        if target.exists():
            continue
        t0 = time.time()
        s = sam[sam.year == y]
        cells = [(int(k[0]), int(k[1]), str(k[2]), str(k[3]), list(g.field.astype(str).unique()))
                 for k, g in s.groupby(["lever_id", "x_id", "x_bin", "lever_level"], observed=True)]
        cols = json.loads((out / f"columns_{y}.json").read_text())
        with mp.get_context("spawn").Pool(7, _init, (out / f"values_{y}.npy", cols, design)) as pool:
            rows = [r for part in pool.imap_unordered(_cell, cells, chunksize=20) for r in part]
        f = pd.DataFrame(rows, columns=["lever_id", "x_id", "x_bin", "lever_level", "field", "n", "p10", "median", "p90"])
        f["year"] = y
        f.to_parquet(target)
        print(f"[compute] {y}: {len(cells)} cells, {len(f)} rows, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    run = get_run()
    {"query": query, "compute": compute}[sys.argv[1]](run)
