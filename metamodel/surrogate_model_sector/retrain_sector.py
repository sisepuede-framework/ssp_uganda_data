"""
retrain_sector.py
-----------------
Retrains the sector XGBoost pipeline on the (now disaggregated) training parquet
and overwrites trained_models/xgb_pipeline_sector_independent_<RUN>.pkl.

Replicates the training cells of model_training_sector.ipynb (tune=False → XGBoost
defaults, z-score outlier removal at 3.0), but runs headless without plotting/CV.

Run:  python retrain_sector.py
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import r2_score

from utils.eda_utils import DataCleaningUtils
from utils.ml_utils_v2 import XGBMultiOutputPipeline

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Single source of truth for the run id: the same YAML the Athena pipeline uses.
# We read just `run_id` directly (rather than athena.config.load_config) so retrain
# stays offline -- it has no need for the AWS profile that load_config requires.
WORKFLOW_CONFIG = os.path.join(SCRIPT_DIR, "config", "ml_training_workflow_config.yaml")


def _load_run_id() -> str:
    with open(WORKFLOW_CONFIG) as f:
        return str(yaml.safe_load(f)["run_id"])


RUN_ID = _load_run_id()
TRAINING_DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "training", f"training_data_sector_{RUN_ID}.parquet")
TRAINED_MODELS_DIR = os.path.join(SCRIPT_DIR, "trained_models")
MODEL_PATH = os.path.join(TRAINED_MODELS_DIR, f"xgb_pipeline_sector_independent_{RUN_ID}.pkl")


def main():
    print("Loading training parquet ...", flush=True)
    df = pd.read_parquet(TRAINING_DATA_PATH).drop(columns=["primary_id", "future_id"])
    target_col = [c for c in df.columns if not c.startswith("group_")]
    print(f"  rows={len(df)}  features={df.shape[1]-len(target_col)}  targets={len(target_col)}", flush=True)

    print("Removing z-score outliers (thresh=3.0) ...", flush=True)
    dcu = DataCleaningUtils()
    df_clean = dcu.remove_outliers(df, method="zscore", z_thresh=3.0)
    print(f"  before={df.shape}  after={df_clean.shape}  removed={len(df)-len(df_clean)}", flush=True)

    print("Training MultiOutputRegressor(XGBRegressor) ...", flush=True)
    mulp = XGBMultiOutputPipeline(df=df_clean, targets=target_col)
    mulp.preprocess()
    mulp.train(log_transform=False)

    # Per-target R² on the held-out test split.
    y_pred = mulp.pipeline.predict(mulp.X_test)
    y_true = mulp.y_test.values
    rows = []
    for i, tgt in enumerate(target_col):
        rows.append((tgt, r2_score(y_true[:, i], y_pred[:, i])))
    r2s = np.array([r for _, r in rows])
    print(f"\nMean R² (all {len(rows)} targets): {r2s.mean():.4f}  | median: {np.median(r2s):.4f}  | min: {r2s.min():.4f}", flush=True)

    def group(pred):
        sel = [r for t, r in rows if pred(t)]
        return (np.mean(sel), np.min(sel), len(sel)) if sel else (float("nan"),) * 3
    for label, pred in [("benefit_", lambda t: t.startswith("benefit_")),
                        ("cost_", lambda t: t.startswith("cost_")),
                        ("gdp_", lambda t: t.startswith("gdp_mmm_usd_yr")),
                        ("emission_", lambda t: t.startswith("emission_"))]:
        m, mn, n = group(pred)
        print(f"  {label:11s} n={n:3d}  meanR²={m:.4f}  minR²={mn:.4f}", flush=True)

    weak = [(t, r) for t, r in rows if r < 0.8]
    print(f"\nTargets with R² < 0.8: {len(weak)}", flush=True)
    for t, r in sorted(weak, key=lambda x: x[1])[:20]:
        print(f"    {t:40s} R²={r:.3f}", flush=True)

    os.makedirs(TRAINED_MODELS_DIR, exist_ok=True)
    joblib.dump(mulp.pipeline, MODEL_PATH)
    print(f"\nSaved: {MODEL_PATH}", flush=True)
    print(f"feature_names_in_ count: {len(mulp.pipeline.feature_names_in_)}", flush=True)


if __name__ == "__main__":
    main()
