"""
The input fields no lever sets, read once from model_input (AWS_PROFILE=alexa), so every input node on the
network has values.

  x      the fields the uncertainties set (VARIABLE_TRAJECTORY_GROUPS_X): every sampled run, anchor years
  fixed  every other input field on the network: a few sampled runs, to confirm they do not vary across runs and
         keep their value

    python -m backend.rdm.network.other_inputs
writes, next to the cached sample:
    other_inputs_x.parquet       index (primary_id, year), one column per field
    other_inputs_fixed.parquet   index (primary_id, year), one column per field (FIXED_RUNS runs)
"""

from pathlib import Path

import pandas as pd

from backend.rdm.data import athena, groups, sample
from backend.rdm.data.inputs import BASE_YEAR, ensure_table
from backend.rdm.runs import get_run

OUT = Path(__file__).parent / "out"
FIXED_RUNS = 5


def fields(run) -> tuple:
    aws = pd.read_csv(OUT / f"{run.name}_aws_columns.csv")
    edges = pd.read_csv(OUT / f"{run.name}_edges.csv")
    f = pd.read_csv(OUT / f"{run.name}_fields.csv")
    on_net = set(edges.source) | set(edges.target)
    lever = set(groups.lever_groups(run).variable_field)
    x = set(pd.read_csv(run.local("groups_x")).variable)
    inputs = set(aws[(aws.table == "model_input")].field)
    wanted = set(f[f.variable.isin(on_net)].field) & inputs - lever
    return sorted(wanted & x), sorted(wanted - x)


def query(run, cols: list, ids: list, label: str) -> pd.DataFrame:
    tps = ", ".join(str(y - BASE_YEAR) for y in run.years)
    sql = (f"SELECT primary_id, time_period, {', '.join(cols)} FROM {run.table('inputs')} "
           f"WHERE region = '{run.region}' AND time_period IN ({tps}) "
           f"AND primary_id IN ({', '.join(str(i) for i in ids)})")
    df = athena.query(run, sql, label)
    return df.assign(year=df.time_period + BASE_YEAR).drop(columns="time_period").set_index(["primary_id", "year"]).sort_index()


if __name__ == "__main__":
    run = get_run()
    cols = set(ensure_table(run))
    x, fixed = fields(run)
    x, fixed = [c for c in x if c in cols], [c for c in fixed if c in cols]
    ids = sample.sample_ids(run, 5000, 0)
    d = sample.sample_dir(run, 5000, 0)
    print(f"fields: {len(x)} set by uncertainties, {len(fixed)} fixed")
    q = query(run, x + fixed, ids[:FIXED_RUNS], "network_fixed_inputs")
    varying = [c for c in fixed if q[c].groupby(level="year").nunique().max() > 1]
    q[fixed].to_parquet(d / "other_inputs_fixed.parquet")
    print(f"fixed fields that vary across the {FIXED_RUNS} runs: {len(varying)} {varying[:8]}")
    qx = query(run, x + varying, ids, "network_x_inputs")
    qx.to_parquet(d / "other_inputs_x.parquet")
    print(f"x inputs cached: {qx.shape}")
