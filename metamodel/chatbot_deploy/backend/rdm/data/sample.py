"""
A random sample of runs with every emission and variable at the anchor years, cached locally.

Used to measure which outputs each lever and uncertainty actually moves (mapping step 0.3)
and to develop the tools before the full run-level store exists. Emissions come from the
run's ``emissions`` table (decomposed_emissions); variables from its ``variables`` table
(model_output). Both are cached as Parquet in the run's cache_dir:

    sample_<n>_seed<seed>/emissions.parquet   index (primary_id, year)
    sample_<n>_seed<seed>/variables.parquet   index (primary_id, year)
"""

import json

import numpy as np
import pandas as pd

from backend.rdm.data import athena, lhc
from backend.rdm.runs import Run

BASE_YEAR = 2015          # SISEPUEDE: year = time_period + 2015
_ID_COLS = {"primary_id", "time_period", "region", "region_data", "future_id"}


def sample_dir(run: Run, n: int, seed: int):
    return run.cache_dir / f"sample_{n}_seed{seed}"


def sample_ids(run: Run, n: int, seed: int) -> list:
    ids = lhc.load_design(run).index.to_numpy()
    return sorted(np.random.default_rng(seed).choice(ids, size=n, replace=False).tolist())


def _shape(df: pd.DataFrame, role: str) -> pd.DataFrame:
    """Index (primary_id, year); keep emission fields for emissions, non-emission fields for variables."""
    df = df.assign(year=df.time_period + BASE_YEAR).set_index(["primary_id", "year"]).sort_index()
    if role == "emissions":
        keep = [c for c in df.columns if c.startswith("emission_co2e_")]
    else:
        keep = [c for c in df.columns if c not in _ID_COLS and not c.startswith("emission")]
    return df[keep]


def _sql(run: Run, role: str, ids: list) -> str:
    tps = ", ".join(str(y - BASE_YEAR) for y in run.years)
    id_list = ", ".join(str(i) for i in ids)
    return (f"SELECT * FROM {run.table(role)} "
            f"WHERE region = '{run.region}' AND time_period IN ({tps}) AND primary_id IN ({id_list})")


def build_sample(run: Run, n: int = 5000, seed: int = 0, result_uris: dict | None = None) -> None:
    """Query Athena once per table and cache the sample (one scan of each table).

    ``result_uris`` maps a role to the s3:// CSV of an earlier Athena run of the same query,
    to rebuild the cache without paying for the scan again.
    """
    out = sample_dir(run, n, seed)
    out.mkdir(parents=True, exist_ok=True)
    ids = sample_ids(run, n, seed)
    frames = {}
    for role in ("emissions", "variables"):
        uri = (result_uris or {}).get(role)
        raw = athena.read_csv_uri(uri) if uri else athena.query(run, _sql(run, role, ids), f"sample_{role}")
        frames[role] = _shape(raw, role)

    # Some futures may be missing from a table (failed runs): keep the runs present in both,
    # complete at every year, and record the rest instead of failing.
    complete = None
    for df in frames.values():
        counts = df.groupby(level="primary_id").size()
        ok = set(counts[counts == len(run.years)].index)
        complete = ok if complete is None else complete & ok
    report = {"requested": len(ids), "kept": len(complete),
              "missing": {role: sorted(int(i) for i in set(ids) - set(df.index.get_level_values(0)))
                          for role, df in frames.items()}}
    for role, df in frames.items():
        df[df.index.get_level_values("primary_id").isin(complete)].to_parquet(out / f"{role}.parquet")
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(f"[sample] kept {len(complete)} of {len(ids)} runs; missing: "
          f"{ {r: len(m) for r, m in report['missing'].items()} }")


def load_sample(run: Run, n: int = 5000, seed: int = 0) -> tuple:
    """(emissions, variables): DataFrames indexed (primary_id, year), original units."""
    d = sample_dir(run, n, seed)
    if not (d / "emissions.parquet").exists():
        raise FileNotFoundError(f"No cached sample in {d}; run build_sample(run, {n}, {seed}) first")
    return pd.read_parquet(d / "emissions.parquet"), pd.read_parquet(d / "variables.parquet")


if __name__ == "__main__":
    import argparse

    from backend.rdm.runs import get_run

    p = argparse.ArgumentParser(description="Build the cached run sample from Athena")
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    r = get_run()
    build_sample(r, a.n, a.seed)
    e, v = load_sample(r, a.n, a.seed)
    print(f"sample cached in {sample_dir(r, a.n, a.seed)}: emissions {e.shape}, variables {v.shape}")
