"""
outlier_filter_ablation.py
--------------------------
Does the z-score outlier filter on the training TARGETS help or hurt?

Measured motivation (see paper1 next_steps.md 3b): the filter removes 24.0% of rows,
none of them on account of a feature -- LHC samples are uniform on [0,1], so their
largest possible |z| is sqrt(3) ~ 1.732 and the 3.0 threshold can never fire in input
space. Every deletion is therefore driven by the target values, which is selection on
the dependent variable.

THE COMPARISON HAS TO BE BUILT CAREFULLY. In the original pipeline the filter runs
BEFORE the split, so the test set is truncated exactly like the training set and the
reported metrics are blind to what was cut. Scoring an unfiltered model against the
deployed one would also leak: rows in an untruncated test set that survived the old
filter are in the deployed model's training data.

So the split is defined ONCE on the full frame and the filter becomes a training-time
step applied only to the training portion:

    full  --split(0.2, seed 42)-->  TRAIN_full        TEST_common (untruncated, unseen)
                                     |
                      control:  filter(TRAIN_full) --> fit
                    treatment:         TRAIN_full  --> fit

Both models are then scored on the same TEST_common. The only difference between them
is the filter, which is what an ablation has to guarantee.

Neither artefact overwrites the deployed .pkl.

Run:  python experiments/outlier_filter_ablation.py
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import sys
import time

import joblib
import numpy as np
import pandas as pd
import yaml
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PKG_DIR)

WORKFLOW_CONFIG = os.path.join(PKG_DIR, "config", "ml_training_workflow_config.yaml")
with open(WORKFLOW_CONFIG) as f:
    RUN_ID = str(yaml.safe_load(f)["run_id"])

TRAINING_DATA_PATH = os.path.join(PKG_DIR, "..", "data", "training",
                                  f"training_data_sector_{RUN_ID}.parquet")
OUT_DIR = os.path.join(PKG_DIR, "trained_models")
CTRL_PKL = os.path.join(OUT_DIR, f"ablation_filtered_{RUN_ID}.pkl")
TRT_PKL = os.path.join(OUT_DIR, f"ablation_nofilter_{RUN_ID}.pkl")
METRICS_CSV = os.path.join(OUT_DIR, f"ablation_outlier_filter_{RUN_ID}.csv")
SUMMARY_MD = os.path.join(OUT_DIR, f"ablation_outlier_filter_{RUN_ID}_summary.md")

SEED, TEST_SIZE, Z_THRESH = 42, 0.2, 3.0


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def zscore_any_mask(A: np.ndarray) -> np.ndarray:
    """Rows where ANY column exceeds |z| > Z_THRESH, matching DataCleaningUtils.

    A column with zero spread cannot flag anything; one with near-zero spread very much
    can, which is the failure mode this experiment exists to price.
    """
    mu, sd = np.nanmean(A, 0), np.nanstd(A, 0)
    sd = np.where(sd == 0, np.inf, sd)
    z = np.nan_to_num(np.abs((A - mu) / sd), nan=0.0)
    return (z > Z_THRESH).any(1)


def fit(X, y):
    base = xgb.XGBRegressor(random_state=SEED, tree_method="hist", n_jobs=-1)
    pipe = Pipeline([("model", MultiOutputRegressor(base))])
    pipe.fit(X, y)
    return pipe


def smape(y_true, y_pred):
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    ratio = np.divide(np.abs(y_true - y_pred), denom, out=np.zeros_like(denom), where=denom != 0)
    return float(np.mean(ratio) * 100)


def score(pipe, X_test, y_test, targets, label):
    pred = pipe.predict(X_test)
    true = y_test.values
    out = []
    for i, t in enumerate(targets):
        yt, yp = true[:, i], pred[:, i]
        out.append({"target": t, "arm": label,
                    "mae": mean_absolute_error(yt, yp),
                    "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
                    "r2": r2_score(yt, yp),
                    "smape": smape(yt, yp)})
    return pd.DataFrame(out)


def corner_totals(pipe, feat_cols, targets):
    """Total 2070 emissions at the corners of the input space.

    The point of interest is the ceiling: the official BAU run reaches 286.8 Mt at 2070
    and the deployed surrogate cannot get near it. If truncating the top of the training
    range contributed, lifting the filter should raise this number.
    """
    lev = [c for c in feat_cols if "_L_" in c]
    exo = [c for c in feat_cols if "_X_" in c]
    em70 = [t for t in targets if t.startswith("emission_") and t.endswith("_yr2070")]
    idx = [targets.index(t) for t in em70]
    rows, names = [], []
    for lname, lval in (("L=0.0", 0.0), ("L=1.0", 1.0)):
        for xname, xval in (("X=0.5", 0.5), ("X=1.0", 1.0)):
            r = pd.Series(0.0, index=feat_cols)
            r[lev], r[exo] = lval, xval
            rows.append(r); names.append(f"{lname}, {xname}")
    P = pipe.predict(pd.DataFrame(rows, columns=feat_cols))
    return {n: float(P[i, idx].sum()) for i, n in enumerate(names)}


def main():
    log("loading parquet")
    df = pd.read_parquet(TRAINING_DATA_PATH).drop(columns=["primary_id", "future_id"])
    feat_cols = [c for c in df.columns if c.startswith("group_")]
    targets = [c for c in df.columns if not c.startswith("group_")]
    X, y = df[feat_cols], df[targets]
    log(f"  rows={len(df)}  features={len(feat_cols)}  targets={len(targets)}")

    # ONE split on the full frame: the test set is untruncated and unseen by both arms.
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, random_state=SEED)
    log(f"  TRAIN_full={len(X_tr):,}   TEST_common={len(X_te):,} (untruncated)")

    keep = ~zscore_any_mask(y_tr.to_numpy(dtype=np.float64))
    log(f"  control keeps {int(keep.sum()):,} of {len(X_tr):,} training rows "
        f"({keep.mean()*100:.1f}%) -- filter drops {int((~keep).sum()):,}")

    log("fitting CONTROL (filter applied to the training rows)")
    t0 = time.time()
    ctrl = fit(X_tr[keep], y_tr[keep])
    log(f"  done in {time.time()-t0:.0f}s")
    m_ctrl = score(ctrl, X_te, y_te, targets, "filtered")
    corners_ctrl = corner_totals(ctrl, feat_cols, targets)
    joblib.dump(ctrl, CTRL_PKL)
    del ctrl

    log("fitting TREATMENT (no filter)")
    t0 = time.time()
    trt = fit(X_tr, y_tr)
    log(f"  done in {time.time()-t0:.0f}s")
    m_trt = score(trt, X_te, y_te, targets, "nofilter")
    corners_trt = corner_totals(trt, feat_cols, targets)
    joblib.dump(trt, TRT_PKL)
    del trt

    m = pd.concat([m_ctrl, m_trt], ignore_index=True)
    m["year"] = m["target"].str.rsplit("_yr", n=1).str[1].astype(int)
    m["family"] = np.select(
        [m["target"].str.startswith("emission_"), m["target"].str.startswith("benefit_"),
         m["target"].str.startswith("cost_"), m["target"].str.startswith("gdp_mmm_usd_yr")],
        ["Emissions", "Benefits", "Costs", "GDP"], default="other")
    m.to_csv(METRICS_CSV, index=False)
    log(f"saved {METRICS_CSV}")

    later = m[m["year"] != 2025]
    piv = later.pivot_table(index="family", columns="arm",
                            values=["r2", "mae", "smape"], aggfunc="median")

    L = []
    L.append("# Ablation: the z-score outlier filter on training targets\n")
    L.append(f"Run `{RUN_ID}`. One split on the full frame (seed {SEED}, test_size {TEST_SIZE}): "
             f"{len(X_tr):,} training rows, **{len(X_te):,} untruncated test rows unseen by both arms**. "
             f"The control drops {int((~keep).sum()):,} of its training rows to the filter "
             f"({(~keep).mean()*100:.1f}%); the treatment keeps all of them. Nothing else differs.\n")
    L.append("\n## Accuracy on the common test set (2035-2070)\n")
    L.append("| Family | n | median R2 filtered | median R2 no-filter | median SMAPE filtered | median SMAPE no-filter |")
    L.append("|---|---|---|---|---|---|")
    for fam in ["Emissions", "Benefits", "Costs", "GDP"]:
        if fam not in piv.index:
            continue
        n = len(later[(later["family"] == fam) & (later["arm"] == "nofilter")])
        L.append(f"| {fam} | {n} | {piv.loc[fam,('r2','filtered')]:.4f} | {piv.loc[fam,('r2','nofilter')]:.4f} | "
                 f"{piv.loc[fam,('smape','filtered')]:.2f} | {piv.loc[fam,('smape','nofilter')]:.2f} |")
    for arm in ["filtered", "nofilter"]:
        sub = later[later["arm"] == arm]
        L.append(f"\n- **{arm}**: median R2 {sub['r2'].median():.4f}, mean {sub['r2'].mean():.4f}, "
                 f"min {sub['r2'].min():.4f}, median SMAPE {sub['smape'].median():.2f}%, "
                 f"{int((sub['r2'] < 0.8).sum())} targets below R2 0.8")

    L.append("\n## Reachable ceiling: total 2070 emissions at the corners of the input space\n")
    L.append("| Corner | filtered | no-filter | change |")
    L.append("|---|---|---|---|")
    for k in corners_ctrl:
        a, b = corners_ctrl[k], corners_trt[k]
        L.append(f"| {k} | {a:.1f} | {b:.1f} | {b-a:+.1f} |")
    L.append(f"\nThe official BAU run reaches **286.8 Mt** at 2070. Maximum-emission corner: "
             f"filtered {corners_ctrl['L=0.0, X=1.0']:.1f} Mt "
             f"({corners_ctrl['L=0.0, X=1.0']/286.8*100-100:+.1f}% vs official), "
             f"no-filter {corners_trt['L=0.0, X=1.0']:.1f} Mt "
             f"({corners_trt['L=0.0, X=1.0']/286.8*100-100:+.1f}%).\n")

    worse = later.pivot_table(index="target", columns="arm", values="r2")
    worse["delta"] = worse["nofilter"] - worse["filtered"]
    L.append("\n## Targets most changed by lifting the filter\n")
    L.append("| Target | R2 filtered | R2 no-filter | delta |")
    L.append("|---|---|---|---|")
    for _, r in worse.nlargest(6, "delta").iterrows():
        L.append(f"| `{r.name}` | {r['filtered']:.4f} | {r['nofilter']:.4f} | {r['delta']:+.4f} |")
    for _, r in worse.nsmallest(4, "delta").iterrows():
        L.append(f"| `{r.name}` | {r['filtered']:.4f} | {r['nofilter']:.4f} | {r['delta']:+.4f} |")

    with open(SUMMARY_MD, "w") as fh:
        fh.write("\n".join(L) + "\n")
    log(f"saved {SUMMARY_MD}")
    print("\n" + "\n".join(L), flush=True)


if __name__ == "__main__":
    main()
