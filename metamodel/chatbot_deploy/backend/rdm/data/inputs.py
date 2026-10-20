"""
Lever input values: what each lever sets in SISEPUEDE's inputs (model_input), per run.

The 54 lever groups set 527 input fields (VARIABLE_TRAJECTORY_GROUPS_L). Their values say what a
lever level means in real terms (e.g. the electric share of light-duty vehicles in 2050 when lever
35 is at 0.6). They are read from the run's ``model_input`` table for the cached sample's runs, at
the years in INPUT_YEARS, and cached next to the sample:

    sample_<n>_seed<seed>/inputs.parquet   index (primary_id, year), one column per input field

``model_input`` was not registered in Athena with the other tables; ``ensure_table`` registers it
(CREATE EXTERNAL TABLE from the CSV header, same layout as surrogate_model_sector/athena/ddl.py).

    python -m backend.rdm.data.inputs        (≈ one full scan of model_input, ~145 GB ≈ $0.70)
"""

import io

import pandas as pd

from backend.rdm.data import athena, groups, sample
from backend.rdm.runs import Run

INPUT_YEARS = (2050, 2070)
BASE_YEAR = sample.BASE_YEAR


def _header(run: Run) -> list:
    """Column names from the first model_input CSV, read in 256 kB chunks until the first line ends.

    The header is ~113 kB (2,444 columns). Until 2026-10-19 only the first 64 kB were read, which cut
    it at column 1,449 and made 236 lever input fields look missing from model_input.
    """
    s3 = athena._session().client("s3")
    prefix = f"{run.run_prefix}{run.table('inputs')}/region={run.region}/"
    key = s3.list_objects_v2(Bucket=run.bucket, Prefix=prefix, MaxKeys=1)["Contents"][0]["Key"]
    head, start, step = b"", 0, 262144
    while b"\n" not in head:
        chunk = s3.get_object(Bucket=run.bucket, Key=key, Range=f"bytes={start}-{start + step - 1}")["Body"].read()
        if not chunk:
            break
        head, start = head + chunk, start + step
    return head.split(b"\n")[0].decode().strip().split(",")


def create_table_sql(run: Run, header: list) -> str:
    def typ(c):
        return "bigint" if c == "primary_id" else "int" if c == "time_period" else "string" if c == "region" else "double"
    cols = ",\n".join(f"  `{c + '_data' if c == 'region' else c}` {typ(c)}" for c in header)
    return (f"CREATE EXTERNAL TABLE IF NOT EXISTS `{run.table('inputs')}` (\n{cols}\n)\n"
            f"PARTITIONED BY (`region` string)\n"
            f"ROW FORMAT DELIMITED FIELDS TERMINATED BY ','\nSTORED AS TEXTFILE\n"
            f"LOCATION '{run.s3_table_uri('inputs')}'\n"
            f"TBLPROPERTIES ('skip.header.line.count'='1');")


def ensure_table(run: Run) -> list:
    """Register model_input in the run's Glue database if it is missing. Returns its columns."""
    glue = athena._session().client("glue")
    try:
        t = glue.get_table(DatabaseName=run.glue_database, Name=run.table("inputs"))["Table"]
        return [c["Name"] for c in t["StorageDescriptor"]["Columns"]]
    except glue.exceptions.EntityNotFoundException:
        header = _header(run)
        athena.execute(run, create_table_sql(run, header), "ddl_model_input")
        athena.execute(run, f"MSCK REPAIR TABLE `{run.table('inputs')}`", "ddl_model_input_repair")
        return [c + "_data" if c == "region" else c for c in header]


def input_fields(run: Run) -> list:
    return sorted(groups.lever_groups(run).variable_field.str.lower().unique())


def build_inputs(run: Run, n: int = 5000, seed: int = 0, years=INPUT_YEARS) -> pd.DataFrame:
    cols = set(ensure_table(run))
    fields = [f for f in input_fields(run) if f in cols]
    missing = sorted(set(input_fields(run)) - cols)
    ids = sample.sample_ids(run, n, seed)
    tps = ", ".join(str(y - BASE_YEAR) for y in years)
    sql = (f"SELECT primary_id, time_period, {', '.join(fields)} FROM {run.table('inputs')} "
           f"WHERE region = '{run.region}' AND time_period IN ({tps}) "
           f"AND primary_id IN ({', '.join(str(i) for i in ids)})")
    df = athena.query(run, sql, "sample_inputs")
    df = df.assign(year=df.time_period + BASE_YEAR).drop(columns="time_period").set_index(["primary_id", "year"]).sort_index()
    out = sample.sample_dir(run, n, seed)
    df.to_parquet(out / "inputs.parquet")
    (out / "inputs_report.txt").write_text(f"fields queried: {len(fields)}\nfields not in model_input: {missing}\n"
                                           f"runs: {df.index.get_level_values(0).nunique()}\n")
    print(f"[inputs] {df.shape} cached; {len(missing)} lever input fields not in model_input: {missing[:5]}")
    return df


def load_inputs(run: Run, n: int = 5000, seed: int = 0) -> pd.DataFrame:
    path = sample.sample_dir(run, n, seed) / "inputs.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No cached inputs in {path.parent}; run python -m backend.rdm.data.inputs")
    return pd.read_parquet(path)


if __name__ == "__main__":
    from backend.rdm.runs import get_run
    build_inputs(get_run())
