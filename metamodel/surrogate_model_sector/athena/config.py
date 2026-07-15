"""
config.py
---------
Single source of truth for the Athena training-data pipeline.

Reads the two YAML config files and derives every name / path the rest of the
pipeline needs (S3 locations, the per-run Glue database name, local output
paths). Import `load_config()` from any script so they all agree.

Two config files (see README):
  * config/ml_training_workflow_config.yaml  -- run_id, region, bucket (in git)
  * config/aws_config.yaml                    -- AWS profile/region (git-ignored)
"""

import os
import re
from dataclasses import dataclass, field
from typing import List

import yaml

# ── repo layout ────────────────────────────────────────────────────────────
ATHENA_DIR = os.path.dirname(os.path.abspath(__file__))            # .../surrogate_model_sector/athena
SECTOR_DIR = os.path.dirname(ATHENA_DIR)                            # .../surrogate_model_sector
METAMODEL_DIR = os.path.dirname(SECTOR_DIR)                         # .../metamodel
CONFIG_DIR = os.path.join(SECTOR_DIR, "config")
QUERIES_DIR = os.path.join(ATHENA_DIR, "queries")

WORKFLOW_CONFIG = os.path.join(CONFIG_DIR, "ml_training_workflow_config.yaml")
AWS_CONFIG = os.path.join(CONFIG_DIR, "aws_config.yaml")

# Target years (and their SISEPUEDE time_period = year - 2015).
TARGET_YEARS = [2025, 2035, 2040, 2050, 2060, 2070]
TARGET_TPS = [y - 2015 for y in TARGET_YEARS]                      # [10, 20, 25, 35, 45, 55]


def _sanitize_db_name(name: str) -> str:
    """Glue/Athena identifiers allow only [a-z0-9_]. Lowercase + replace the rest."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


@dataclass
class PipelineConfig:
    # raw inputs
    run_id: str
    region: str
    bucket: str
    profile_name: str
    aws_region: str

    # derived
    run_dir_name: str = field(init=False)        # sisepuede_run_<run_id> (real S3 key, keeps ';')
    database: str = field(init=False)            # Glue database, sanitized
    transfers_prefix: str = field(init=False)    # S3 key prefix for ATTRIBUTE_* / LHC files
    query_output_prefix: str = field(init=False) # s3://.../queries/<run>/

    def __post_init__(self):
        self.run_dir_name = f"sisepuede_run_{self.run_id}"
        self.database = _sanitize_db_name(self.run_dir_name)
        self.transfers_prefix = f"transfers/{self.run_dir_name}/"
        self.query_output_prefix = f"s3://{self.bucket}/queries/{self.run_dir_name}/"

    # ── S3 table locations (parent of the region=<x>/ partition dirs) ───────
    def table_location(self, table: str) -> str:
        return f"s3://{self.bucket}/run_database/{self.run_dir_name}/{table}/"

    def query_output(self, name: str) -> str:
        """Where Athena writes a query's <exec-id>.csv result."""
        return f"{self.query_output_prefix}{name}/"

    # ── local paths ─────────────────────────────────────────────────────────
    @property
    def ssp_dir(self) -> str:
        """Local mirror of transfers/<run>/ (ATTRIBUTE_* + LHC CSVs)."""
        return os.path.join(METAMODEL_DIR, "data", "ssp", self.run_dir_name)

    @property
    def training_dir(self) -> str:
        return os.path.join(METAMODEL_DIR, "data", "training")

    @property
    def training_parquet(self) -> str:
        return os.path.join(self.training_dir, f"training_data_sector_{self.run_id}.parquet")

    @property
    def query_csv_dir(self) -> str:
        """Local dir for downloaded Athena result CSVs."""
        return os.path.join(METAMODEL_DIR, "data", "athena", self.run_dir_name)


def load_config() -> PipelineConfig:
    with open(WORKFLOW_CONFIG) as f:
        wf = yaml.safe_load(f)
    if not os.path.exists(AWS_CONFIG):
        raise FileNotFoundError(
            f"Missing {AWS_CONFIG}. Copy aws_config.yaml.example and set your AWS "
            f"profile_name / region_name (see README)."
        )
    with open(AWS_CONFIG) as f:
        aws = yaml.safe_load(f)

    return PipelineConfig(
        run_id=str(wf["run_id"]),
        region=str(wf.get("region", "uganda")),
        bucket=str(wf["bucket_name"]),
        profile_name=str(aws["profile_name"]),
        aws_region=str(aws.get("region_name", "us-east-1")),
    )
