"""
evaluate_sector_model.py
------------------------
Scores the DEPLOYED surrogate .pkl on the held-out test split and SAVES the
per-target metrics. It does not train anything.

Why this exists separately from retrain_sector.py: that script re-fits the model
and overwrites the .pkl, and it only PRINTS its metrics. Running it to obtain
numbers for the paper would therefore report on an artefact that is no longer the
one being served, and would break the frozen commit the trials cite. This script
loads the artefact as it stands and measures it.

The split is reproduced exactly as training built it -- same cleaning (retrain_sector.clean,
no outlier filter since 2026-10-16), same test_size, same random_state -- so the rows scored
here are the rows the model was held out from.

Run:  python evaluate_sector_model.py
Out:  trained_models/metrics_<RUN_ID>.csv        per-target MAE / RMSE / R2 / SMAPE
      trained_models/metrics_<RUN_ID>_summary.md per-family table for the paper
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from retrain_sector import clean
from utils.ml_utils_v2 import XGBMultiOutputPipeline

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_CONFIG = os.path.join(SCRIPT_DIR, "config", "ml_training_workflow_config.yaml")


def _load_run_id() -> str:
    with open(WORKFLOW_CONFIG) as f:
        return str(yaml.safe_load(f)["run_id"])


RUN_ID = _load_run_id()
TRAINING_DATA_PATH = os.path.join(
    SCRIPT_DIR, "..", "data", "training", f"training_data_sector_{RUN_ID}.parquet"
)
TRAINED_MODELS_DIR = os.path.join(SCRIPT_DIR, "trained_models")
MODEL_PATH = os.path.join(TRAINED_MODELS_DIR, f"xgb_pipeline_sector_independent_{RUN_ID}.pkl")
METRICS_CSV = os.path.join(TRAINED_MODELS_DIR, f"metrics_{RUN_ID}.csv")
SUMMARY_MD = os.path.join(TRAINED_MODELS_DIR, f"metrics_{RUN_ID}_summary.md")

# Target families, in the order the paper reports them. The gdp test is exact
# because "gdp_" would also catch nothing else, but keep it explicit anyway.
FAMILIES = [
    ("Emissions", lambda t: t.startswith("emission_")),
    ("Benefits",  lambda t: t.startswith("benefit_")),
    ("Costs",     lambda t: t.startswith("cost_")),
    ("GDP",       lambda t: t.startswith("gdp_mmm_usd_yr")),
]


def _smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Symmetric MAPE, matching XGBMultiOutputPipeline._metrics.

    The zero-denominator guard matters here: several _yr2025 targets are
    effectively constant at ~0, where the ratio is undefined rather than large.
    """
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    ratio = np.divide(np.abs(y_true - y_pred), denom, out=np.zeros_like(denom), where=denom != 0)
    return float(np.mean(ratio) * 100)


def main():
    print("Loading training parquet ...", flush=True)
    df = pd.read_parquet(TRAINING_DATA_PATH).drop(columns=["primary_id", "future_id"])
    target_col = [c for c in df.columns if not c.startswith("group_")]
    print(f"  rows={len(df)}  features={df.shape[1]-len(target_col)}  targets={len(target_col)}", flush=True)

    df_clean = clean(df)

    # Rebuild the identical split. preprocess() is pure train_test_split, so the
    # same frame + same random_state gives back the same held-out rows.
    mulp = XGBMultiOutputPipeline(df=df_clean, targets=target_col)
    mulp.preprocess()
    print(f"  test rows={len(mulp.X_test)}", flush=True)

    print(f"Loading deployed model: {os.path.basename(MODEL_PATH)}", flush=True)
    pipeline = joblib.load(MODEL_PATH)

    # Guard against a parquet/model mismatch: a silently reordered or renamed
    # feature would produce plausible-looking but meaningless metrics.
    trained_features = list(getattr(pipeline, "feature_names_in_", []))
    if trained_features:
        current = list(mulp.X_test.columns)
        if trained_features != current:
            raise SystemExit(
                "Feature mismatch between the parquet and the deployed model.\n"
                f"  model expects {len(trained_features)}, parquet gives {len(current)}\n"
                f"  first divergence: {next((a, b) for a, b in zip(trained_features, current) if a != b)}"
            )
        print(f"  feature order verified ({len(trained_features)} features)", flush=True)

    print("Predicting on the held-out split ...", flush=True)
    y_pred = pipeline.predict(mulp.X_test)
    y_true = mulp.y_test.values

    rows = []
    for i, tgt in enumerate(target_col):
        yt, yp = y_true[:, i], y_pred[:, i]
        rows.append({
            "target": tgt,
            "family": next((name for name, pred in FAMILIES if pred(tgt)), "other"),
            "year": int(tgt.rsplit("_yr", 1)[1]) if "_yr" in tgt else None,
            "mae": mean_absolute_error(yt, yp),
            "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
            "r2": r2_score(yt, yp),
            "smape": _smape(yt, yp),
            "y_std": float(np.std(yt)),
        })
    m = pd.DataFrame(rows)
    m.to_csv(METRICS_CSV, index=False)
    print(f"\nSaved per-target metrics: {METRICS_CSV}", flush=True)

    # ── Summary for the paper ────────────────────────────────────────────────
    # R2 is reported as MEDIAN first. All _yr2025 targets have near-zero variance
    # across scenarios (levers have barely ramped by 2025), so r2_score divides by
    # ~0 and the MEAN explodes. That is a metric artefact, not a model failure --
    # absolute error on those targets is tiny. The 2025 column is broken out so a
    # reader can see the effect rather than take it on trust.
    is2025 = m["year"] == 2025
    lines = []
    lines.append(f"# Surrogate performance on the held-out split\n")
    lines.append(f"Run `{RUN_ID}` | model `{os.path.basename(MODEL_PATH)}` | "
                 f"{len(mulp.X_test):,} test rows | {len(target_col)} targets\n")
    lines.append("\n## By target family (2035-2070; the 2025 horizon is excluded, see note)\n")
    lines.append("| Family | n | median R2 | mean R2 | min R2 | median MAE | median SMAPE % | R2 < 0.8 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, pred in FAMILIES:
        sub = m[(m["family"] == name) & (~is2025)]
        if sub.empty:
            continue
        lines.append(
            f"| {name} | {len(sub)} | {sub['r2'].median():.4f} | {sub['r2'].mean():.4f} | "
            f"{sub['r2'].min():.4f} | {sub['mae'].median():.4g} | {sub['smape'].median():.2f} | "
            f"{int((sub['r2'] < 0.8).sum())} |"
        )
    allsub = m[~is2025]
    lines.append(
        f"| **All** | {len(allsub)} | {allsub['r2'].median():.4f} | {allsub['r2'].mean():.4f} | "
        f"{allsub['r2'].min():.4f} | {allsub['mae'].median():.4g} | {allsub['smape'].median():.2f} | "
        f"{int((allsub['r2'] < 0.8).sum())} |"
    )

    lines.append("\n## The 2025 horizon, reported separately\n")
    sub25 = m[is2025]
    lines.append(
        f"{len(sub25)} targets. Median R2 {sub25['r2'].median():.4f}, mean {sub25['r2'].mean():.4g}, "
        f"min {sub25['r2'].min():.4g}. Median target standard deviation across scenarios: "
        f"{sub25['y_std'].median():.3g} (vs {allsub['y_std'].median():.3g} for later years), "
        f"and median MAE {sub25['mae'].median():.4g}.\n"
    )
    lines.append(
        "2025 sits only six years after the 2019 base, so the modelled transformations have "
        "barely begun to ramp and the targets are near-constant across scenarios. R2 divides by "
        "that near-zero variance, so it is unstable by construction at this horizon while "
        "absolute error stays small. Read R2 from the later years.\n"
    )

    lines.append("\n## Weakest targets (excluding 2025)\n")
    lines.append("| Target | Family | R2 | MAE | SMAPE % |")
    lines.append("|---|---|---|---|---|")
    for _, r in allsub.nsmallest(12, "r2").iterrows():
        lines.append(f"| `{r['target']}` | {r['family']} | {r['r2']:.4f} | {r['mae']:.4g} | {r['smape']:.2f} |")

    with open(SUMMARY_MD, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Saved summary table:      {SUMMARY_MD}\n", flush=True)
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
