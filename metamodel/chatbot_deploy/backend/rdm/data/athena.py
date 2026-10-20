"""
Thin Athena helper: run SQL against the run's Glue database, return a DataFrame, report cost.

Credentials come from the default boto3 chain; set AWS_PROFILE (e.g. ``alexa`` for SSO) when
running locally. Region defaults to us-west-2, where the sisepuede-data bucket lives.
"""

import os
import tempfile
import time

import boto3
import pandas as pd

from backend.rdm.runs import Run

USD_PER_TB = 5.0


def _session() -> boto3.Session:
    return boto3.Session(region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))


def query(run: Run, sql: str, label: str = "query", poll_seconds: float = 3.0) -> pd.DataFrame:
    """Run ``sql`` in the run's Glue database and return the result as a DataFrame."""
    return read_csv_uri(execute(run, sql, label, poll_seconds))


def execute(run: Run, sql: str, label: str = "query", poll_seconds: float = 3.0) -> str:
    """Run ``sql`` (a query or DDL) and return the s3:// location of its result; reports the cost."""
    session = _session()
    athena = session.client("athena")
    qid = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": run.glue_database},
        ResultConfiguration={"OutputLocation": run.query_output_uri() + label + "/"},
    )["QueryExecutionId"]

    while True:
        qe = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = qe["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(poll_seconds)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena {label} {state}: {qe['Status'].get('StateChangeReason', '')}")

    scanned = qe.get("Statistics", {}).get("DataScannedInBytes", 0)
    print(f"[athena] {label}: scanned {scanned / 1e9:.1f} GB ≈ ${scanned / 1e12 * USD_PER_TB:.2f}")

    return qe["ResultConfiguration"]["OutputLocation"]


def read_csv_uri(uri: str) -> pd.DataFrame:
    """Download an s3:// CSV (e.g. a past Athena result) and read it, without re-running a query."""
    bucket, key = uri[len("s3://"):].split("/", 1)
    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        _session().client("s3").download_file(bucket, key, tmp.name)
        return pd.read_csv(tmp.name)
