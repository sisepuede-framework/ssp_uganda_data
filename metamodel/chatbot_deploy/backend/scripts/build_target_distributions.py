"""
Generate backend/target_distributions.json from the sector training parquet.

This sidecar replaces the runtime parquet load. It stores:
  - target_columns: the full ordered list of model output columns (parquet order,
    which matches the model's output order). Used to map raw predictions →
    sector×year trajectories and the disaggregated cost/benefit/GDP targets.
    This is the only load-bearing field.
  - target_distributions: per-aggregate-metric training value lists + min/max range,
    used for `percentile_in_training` / `training_range` in the UI. Keyed by the
    entries in `predictor.TARGET_METADATA` — which is EMPTY in this run (there are no
    dedicated aggregate-emission targets), so this map comes out empty too.

Re-run this after any retrain of the sector model:
    python -m backend.scripts.build_target_distributions
The training parquet is resolved from settings.s3_run_id, so a new run id needs no
edit here (just keep config's run id in sync with the retrained model/parquet).
"""

import json
import logging
from pathlib import Path

import pandas as pd

from backend.config import settings
from backend.services.predictor import TARGET_METADATA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Source parquet still lives at the historical training path. We read it ONCE
# here at build time so the server never has to. The filename embeds the run id; we
# derive it from settings.s3_run_id (the same single source of truth the server uses)
# so a retrain needs no edit here AND stale parquets from older runs are ignored.
# Normalisation mirrors s3_lookup.py: lowercase 't', ':' → ';', drop the prefix.
_TRAINING_DIR = settings.model_sector_path.parent.parent.parent / "data" / "training"
_RUN_KEY = settings.s3_run_id.lower().replace(":", ";").removeprefix("sisepuede_run_")
_TRAINING_PARQUET = _TRAINING_DIR / f"training_data_sector_{_RUN_KEY}.parquet"

_OUT_PATH = Path(__file__).parent.parent / "target_distributions.json"


def main() -> None:
    if not _TRAINING_PARQUET.exists():
        raise FileNotFoundError(
            f"Sector training parquet for run {_RUN_KEY!r} not found at {_TRAINING_PARQUET}. "
            "Check settings.s3_run_id matches the retrained parquet."
        )
    parquet = _TRAINING_PARQUET
    df = pd.read_parquet(parquet)
    id_cols = {"future_id", "primary_id", "strategy_id", "design_id"}
    feature_cols = [c for c in df.columns if c.startswith("group_")]
    target_cols = [c for c in df.columns if c not in feature_cols and c not in id_cols]

    distributions: dict[str, dict] = {}
    for col in TARGET_METADATA:
        if col not in df.columns:
            raise KeyError(f"Aggregate target {col!r} missing from training parquet")
        vals = df[col].dropna().tolist()
        distributions[col] = {
            "values": [round(float(v), 4) for v in vals],
            "range": {"min": round(min(vals), 4), "max": round(max(vals), 4)},
        }

    payload = {
        "target_columns": target_cols,
        "target_distributions": distributions,
    }

    with open(_OUT_PATH, "w") as fh:
        json.dump(payload, fh)

    logger.info(
        "Wrote %s from %s: %d target columns, %d aggregate distributions",
        _OUT_PATH.name,
        parquet.name,
        len(target_cols),
        len(distributions),
    )


if __name__ == "__main__":
    main()
