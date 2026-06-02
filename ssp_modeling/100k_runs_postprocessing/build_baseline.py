#!/usr/bin/env python3
"""
build_baseline.py
-----------------
Genera el archivo baseline `tmp/uganda_0.csv` que el postprocesamiento
(100k_run_postprocessing_parallel.py) exige como precondición.

El baseline es el merge input+output para primary_id == 0, idéntico al merge
que hace el script principal para los primary_id no-baseline (líneas 611-613):
    pd.merge(output, input, on=["primary_id", "region", "time_period"], how="left")

Config (perfil, bucket, run_id) se lee de config/aws_credentials_config.yaml.
El run_id puede sobreescribirse con --run-id.

Uso:
    python build_baseline.py
    python build_baseline.py --run-id "sisepuede_run_2026-05-30t21;35;56.244639"
"""
import os
import argparse
from io import StringIO

import pandas as pd
import yaml
import boto3

# RUN_ID por defecto — debe coincidir con la línea 576 de
# 100k_run_postprocessing_parallel.py
DEFAULT_RUN_ID = "sisepuede_run_2026-05-30t21;35;56.244639"
REGION = "uganda"
PRIMARY_ID_BASE = 0
MERGE_KEYS = ["primary_id", "region", "time_period"]


def fetch_csv_from_s3(s3_resource, bucket, key):
    body = s3_resource.Object(bucket, key).get()["Body"].read().decode("utf-8")
    return pd.read_csv(StringIO(body))


def main():
    parser = argparse.ArgumentParser(description="Genera tmp/uganda_0.csv (baseline primary_id=0)")
    parser.add_argument("--run-id", default=None, help="Sobreescribe el RUN_ID (default: valor del script / YAML)")
    parser.add_argument("--profile", default=None, help="Perfil AWS (sobreescribe el YAML)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir, "config")
    tmp_dir = os.path.join(script_dir, "tmp")

    with open(os.path.join(config_dir, "aws_credentials_config.yaml"), "r") as f:
        aws_config = yaml.safe_load(f)

    profile = args.profile or aws_config["profile_name"]
    bucket = aws_config["bucket_name"]
    run_id = args.run_id or aws_config.get("run_id") or DEFAULT_RUN_ID

    print(f"profile = {profile} | bucket = {bucket}")
    print(f"run_id  = {run_id}")

    s3 = boto3.Session(profile_name=profile).resource("s3")

    base = f"run_database/{run_id}"
    out_key = f"{base}/model_output/region={REGION}/model_output_{PRIMARY_ID_BASE}/data.csv"
    inp_key = f"{base}/model_input/region={REGION}/model_input_{PRIMARY_ID_BASE}/data.csv"

    print(f"Descargando output: s3://{bucket}/{out_key}")
    out = fetch_csv_from_s3(s3, bucket, out_key)
    print(f"Descargando input : s3://{bucket}/{inp_key}")
    inp = fetch_csv_from_s3(s3, bucket, inp_key)

    out0 = out[out["primary_id"] == PRIMARY_ID_BASE].copy()
    inp0 = inp[inp["primary_id"] == PRIMARY_ID_BASE].copy()
    merged = pd.merge(out0, inp0, on=MERGE_KEYS, how="left")

    os.makedirs(tmp_dir, exist_ok=True)
    dest = os.path.join(tmp_dir, "uganda_0.csv")
    merged.to_csv(dest, index=False)
    print(f"[OK] Escrito {dest} -> shape {merged.shape}")


if __name__ == "__main__":
    main()
