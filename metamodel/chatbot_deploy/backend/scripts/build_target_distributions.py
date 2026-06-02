"""
Generate backend/target_distributions.json from the sector training parquet.

This sidecar replaces the runtime parquet load. It stores:
  - target_columns: the full ordered list of model output columns (parquet order,
    which matches the model's output order). Used to map raw predictions →
    aggregate metrics and sector×year trajectories.
  - target_distributions: for each of the 11 aggregate metrics, the training-set
    value list + min/max range, used to compute `percentile_in_training` and the
    `training_range` shown in the UI.

Re-run this after any retrain of the sector model:
    python -m backend.scripts.build_target_distributions
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
# here at build time so the server never has to.
_TRAINING_PARQUET = (
    settings.model_sector_path.parent.parent.parent
    / "data"
    / "training"
    / "training_data_sector_2025-11-12t22;19;28.194097.parquet"
)

_OUT_PATH = Path(__file__).parent.parent / "target_distributions.json"


def main() -> None:
    if not _TRAINING_PARQUET.exists():
        raise FileNotFoundError(f"Sector training parquet not found at {_TRAINING_PARQUET}")

    df = pd.read_parquet(_TRAINING_PARQUET)
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
        "Wrote %s: %d target columns, %d aggregate distributions",
        _OUT_PATH.name,
        len(target_cols),
        len(distributions),
    )


if __name__ == "__main__":
    main()
