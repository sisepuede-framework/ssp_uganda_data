"""
Step 1a · the fields the run has in AWS, read from the cached sample (no AWS call).

  model_output          every column of the sample's variables table (SELECT * at the anchor years)
  decomposed_emissions  every column of the sample's emissions table
  model_input           the full header (2,444 columns), saved once from S3 in out/<run>_model_input_header.txt
                        (read with AWS_PROFILE=alexa); `cached` marks the 527 lever fields whose values are local

    python -m backend.rdm.network.aws_columns      → network/out/<run>_aws_columns.csv
"""

from pathlib import Path

import pandas as pd

from backend.rdm.data.sample import sample_dir
from backend.rdm.runs import get_run

OUT = Path(__file__).parent / "out"
ID_COLS = {"primary_id", "year", "time_period", "region", "region_data"}


def columns(run) -> pd.DataFrame:
    d = sample_dir(run, 5000, 0)
    rows = []
    for file, table in (("variables.parquet", "model_output"), ("emissions.parquet", "decomposed_emissions")):
        cols = pd.read_parquet(d / file).columns
        rows += [{"field": c, "table": table, "cached": True} for c in cols if c not in ID_COLS]
    cached = set(pd.read_parquet(d / "inputs.parquet").columns)
    header = (OUT / f"{run.name}_model_input_header.txt").read_text().split()
    rows += [{"field": c, "table": "model_input", "cached": c in cached} for c in header if c not in ID_COLS]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    r = get_run()
    OUT.mkdir(exist_ok=True)
    df = columns(r)
    p = OUT / f"{r.name}_aws_columns.csv"
    df.to_csv(p, index=False)
    print(p.name, df.table.value_counts().to_dict())
