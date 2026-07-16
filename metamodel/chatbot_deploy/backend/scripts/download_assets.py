"""
download_assets.py
------------------
Boot-time asset fetcher for container deploys (Railway / Docker).

Why this exists: the model (94 MB) and the SISEPUEDE data CSVs (~275 MB) are too
big to ship in the image or git. They live in S3; this script pulls them to the
exact local paths the app reads at runtime, so the image stays small and the data
lives in AWS. Run it BEFORE uvicorn (see entrypoint.sh):

    python -m backend.scripts.download_assets

Auth uses the same credential chain as the rest of the app (AWS_ACCESS_KEY_ID /
AWS_SECRET_ACCESS_KEY env vars on Railway). Read-only S3 access is sufficient.

Idempotent: a file already present locally with the same byte size is skipped, so
restarts don't re-download. A missing *required* asset exits non-zero so the
container fails fast instead of starting a half-broken server.

S3 layout (2026-05-30 run) — keys are built from settings.s3_run_id:
  run_database/<run>/model_pkl/model.pkl                    the surrogate model
  transfers/<run>/ATTRIBUTE_*.csv, VARIABLE_TRAJECTORY_*.csv  attribute tables
  run_database/<run>/decomposed_pathways/*.csv               curated pathways
  run_database/<run>/chatbot_assets/*.csv                     curated crosswalks
"""

import logging
import sys
from pathlib import Path

from backend.config import settings
from backend.services import s3_lookup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("download_assets")

# Run key in S3 form: lowercase 't', semicolons not colons (matches settings).
RUN = settings.s3_run_id.lower().replace(":", ";")
BUCKET = settings.s3_bucket
SSP = Path(settings.ssp_data_dir)          # e.g. /app/data/ssp
RUN_DIR = SSP / RUN                         # per-run subdir the code expects
MODEL_DEST = Path(settings.model_sector_path)  # e.g. /app/model.pkl

# (s3_key, local_destination). Every asset here is required for full functionality.
MANIFEST: list[tuple[str, Path]] = [
    # Model
    (f"run_database/{RUN}/model_pkl/model.pkl", MODEL_DEST),
    # Attribute tables + trajectory groups (already in the transfers/ prefix)
    (f"transfers/{RUN}/ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv",
     RUN_DIR / "ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv"),
    (f"transfers/{RUN}/ATTRIBUTE_PRIMARY.csv", RUN_DIR / "ATTRIBUTE_PRIMARY.csv"),
    (f"transfers/{RUN}/ATTRIBUTE_STRATEGY.csv", RUN_DIR / "ATTRIBUTE_STRATEGY.csv"),
    (f"transfers/{RUN}/VARIABLE_TRAJECTORY_GROUPS_L.csv",
     RUN_DIR / "VARIABLE_TRAJECTORY_GROUPS_L.csv"),
    # Curated crosswalks (uploaded to chatbot_assets/)
    (f"run_database/{RUN}/chatbot_assets/transformation_variable_map.csv",
     SSP / "transformation_variable_map.csv"),
    (f"run_database/{RUN}/chatbot_assets/transformation_output_variable_map.csv",
     SSP / "transformation_output_variable_map.csv"),
    # Curated pathways — tableau_levers_table holds the levers of the 6 named
    # pathways, so it lives with the other pathway files in decomposed_pathways/.
    (f"run_database/{RUN}/decomposed_pathways/uganda_pathways.csv",
     RUN_DIR / "pathways" / "uganda_pathways.csv"),
    (f"run_database/{RUN}/decomposed_pathways/cba_data_air_pollution.csv",
     RUN_DIR / "pathways" / "cba_data_air_pollution.csv"),
    (f"run_database/{RUN}/decomposed_pathways/tableau_levers_table.csv",
     RUN_DIR / "pathways" / "tableau_levers_table.csv"),
]


def _remote_size(s3, key: str) -> int | None:
    """ContentLength of an S3 object, or None if it isn't there / not readable."""
    try:
        return s3.head_object(Bucket=BUCKET, Key=key)["ContentLength"]
    except Exception as exc:  # noqa: BLE001 — any failure means "treat as missing"
        logger.warning("head_object failed for s3://%s/%s: %s", BUCKET, key, exc)
        return None


def main() -> None:
    logger.info("Fetching assets for run %s into %s", RUN, SSP)
    s3 = s3_lookup._get_s3()
    missing: list[str] = []

    for key, dest in MANIFEST:
        remote = _remote_size(s3, key)
        if remote is None:
            missing.append(f"s3://{BUCKET}/{key}")
            continue
        if dest.exists() and dest.stat().st_size == remote:
            logger.info("up-to-date, skipping: %s", dest)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("downloading s3://%s/%s -> %s (%.1f MB)",
                    BUCKET, key, dest, remote / 1e6)
        s3.download_file(BUCKET, key, str(dest))

    if missing:
        logger.error("Missing %d required asset(s) in S3:", len(missing))
        for m in missing:
            logger.error("  - %s", m)
        sys.exit(1)

    logger.info("All %d assets present.", len(MANIFEST))


if __name__ == "__main__":
    main()
