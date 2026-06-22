"""
athena_client.py
----------------
Minimal boto3 helpers for running Athena queries and reading S3.

We deliberately do NOT construct sisepuede_cloud_manager's AWSManager (it needs a
full SISEPUEDE object + shell templates + a namespaced config we don't have here).
The only Athena calls we need are thin wrappers over boto3 -- functionally the
same as AWSManager.exec_query / .get_query_state -- so we reimplement them here.

Auth: an AWS *profile* (see config/aws_config.yaml). No raw keys in the repo.
"""

import time

import boto3


def make_session(cfg) -> boto3.Session:
    """boto3 Session from the configured AWS profile + region."""
    return boto3.Session(profile_name=cfg.profile_name, region_name=cfg.aws_region)


# ── Athena ──────────────────────────────────────────────────────────────────
def run_query(session, sql: str, output_location: str, database: str = None) -> str:
    """Submit a query (async) and return its QueryExecutionId.

    `database` sets the catalog context so the SQL can say `FROM model_output`
    without qualifying it. DDL statements (CREATE DATABASE, etc.) pass it too.
    """
    athena = session.client("athena")
    kwargs = {
        "QueryString": sql,
        "ResultConfiguration": {"OutputLocation": output_location},
    }
    if database:
        kwargs["QueryExecutionContext"] = {"Database": database}
    resp = athena.start_query_execution(**kwargs)
    return resp["QueryExecutionId"]


def wait_for_query(session, execution_id: str, poll_seconds: float = 2.0) -> dict:
    """Block until the query reaches a terminal state. Raise on FAILED/CANCELLED.

    Returns the QueryExecution dict (has Status, ResultConfiguration, Statistics
    -- including DataScannedInBytes for cost reporting).
    """
    athena = session.client("athena")
    terminal = {"SUCCEEDED", "FAILED", "CANCELLED"}
    while True:
        qe = athena.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]
        state = qe["Status"]["State"]
        if state in terminal:
            if state != "SUCCEEDED":
                reason = qe["Status"].get("StateChangeReason", "(no reason given)")
                raise RuntimeError(f"Athena query {execution_id} {state}: {reason}")
            return qe
        time.sleep(poll_seconds)


def result_s3_uri(query_execution: dict) -> str:
    """The s3://.../<exec-id>.csv path Athena wrote the result to."""
    return query_execution["ResultConfiguration"]["OutputLocation"]


def bytes_scanned(query_execution: dict) -> int:
    return query_execution.get("Statistics", {}).get("DataScannedInBytes", 0)


def download_s3_uri(session, s3_uri: str, local_path: str) -> None:
    """Download an s3://bucket/key object to a local file."""
    assert s3_uri.startswith("s3://"), s3_uri
    bucket, key = s3_uri[len("s3://"):].split("/", 1)
    session.client("s3").download_file(bucket, key, local_path)


# ── S3 (for DDL header sniffing + feature downloads) ──────────────────────────
def first_data_csv_key(session, bucket: str, prefix: str) -> str:
    """Return the key of the first `data.csv` found under an S3 prefix.

    Used to read a representative header for DDL generation. All batch CSVs in a
    run share the same column order, so any one is representative.
    """
    s3 = session.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("data.csv"):
                return obj["Key"]
    raise FileNotFoundError(f"No data.csv found under s3://{bucket}/{prefix}")


def read_csv_header(session, bucket: str, key: str, max_bytes: int = 1 << 20) -> list:
    """Read just the first line of an S3 CSV and return the column names."""
    s3 = session.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}")
    raw = obj["Body"].read().decode("utf-8", errors="replace")
    header_line = raw.split("\n", 1)[0].strip("\r")
    return header_line.split(",")
