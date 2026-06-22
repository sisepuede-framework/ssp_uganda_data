"""
build_s3_dir_index.py
---------------------
Build the chatbot's primary_id -> batch-directory index used by the S3-lookup
tools (s3_lookup.py: get_model_inputs_row / get_model_outputs_row).

How: run an Athena query that returns each primary_id with the S3 file it came
from (the "$path" pseudo-column), then parse model_output_<n>/ -> n.

Cost: this scans the full model_output table once (~103 GB ≈ $0.52). It is a
ONE-TIME, per-run cost; the resulting JSON is cached in the repo. model_input
and model_output share batching, so the same index serves both.

Run:
    python build_s3_dir_index.py
"""

import json
import os
import re

import pandas as pd

from config import load_config, QUERIES_DIR, METAMODEL_DIR
import athena_client as ac

OUTPUT_INDEX = os.path.join(
    METAMODEL_DIR, "chatbot_deploy", "backend", "s3_model_input_index.json"
)
_BATCH_RX = re.compile(r"model_output_(\d+)/")


def main() -> None:
    cfg = load_config()
    session = ac.make_session(cfg)
    sql = open(os.path.join(QUERIES_DIR, "s3_dir_index.sql")).read().format(region=cfg.region)

    print(f"Run:      {cfg.run_dir_name}")
    print(f"Database: {cfg.database}")
    print("Running Athena $path query (scans model_output ~103 GB, ~$0.52) ...")
    qe = ac.wait_for_query(session, ac.run_query(session, sql, cfg.query_output("_index"), cfg.database))
    mb = ac.bytes_scanned(qe) / 1e6
    print(f"  scanned {mb:,.0f} MB  (~${mb / 1e6 * 5:.2f})")

    os.makedirs(cfg.query_csv_dir, exist_ok=True)
    local = os.path.join(cfg.query_csv_dir, "s3_dir_index.csv")
    ac.download_s3_uri(session, ac.result_s3_uri(qe), local)

    df = pd.read_csv(local)
    index: dict[str, int] = {}
    missed = 0
    for pid, path in zip(df["primary_id"], df["path"]):
        m = _BATCH_RX.search(str(path))
        if m:
            index[str(int(pid))] = int(m.group(1))
        else:
            missed += 1

    with open(OUTPUT_INDEX, "w") as f:
        json.dump(index, f)

    print(f"Wrote {OUTPUT_INDEX}")
    print(f"  {len(index)} primary_ids indexed"
          + (f"  ({missed} paths unparsed!)" if missed else ""))
    print(f"  batch range: {min(index.values())}–{max(index.values())}")
    print(f"  primary_id=0 present? {'0' in index}")


if __name__ == "__main__":
    main()
