"""
rdm_fitness.py (2026-11-16)
---------------------------
Is the deployed surrogate fit for the RDM questions the agent asks? R2 says the surrogate predicts each target well on
average; RDM uses the predictions to classify futures as pass / fail, to compute failure shares, to find the
conditions under which a policy fails, and to compare policies. This script checks those four uses on the held-out
runs (the same 19,918 rows as evaluate_sector_model.py), true model vs surrogate. It trains nothing.

  A. Pass / fail at a threshold   total emissions and total cost, 2035 / 2050 / 2070, thresholds at the 10th–90th
                                  percentile of the true values: agreement, false pass, false fail, and how many
                                  errors lie within 2% of the threshold.
  B. Failure share in a region    for every lever and uncertainty, runs in its bottom and top third: share failing
                                  (2050 total emissions above the median), true vs surrogate.
  C. Scenario discovery           the tool's algorithm (backend/rdm/tools/technical.py: CART, depth 2, the pair of
                                  uncertainties that best separates pass from fail) run on true and on surrogate labels.
  D. Ordering                     random pairs of runs: does the surrogate order them like the model? Also for pairs
                                  within 2% of each other.

Not checked here: a threshold relative to BAU in the same future (the paper's "5% below BAU"). The held-out runs have
no paired BAU run, because every run has its own future. That needs paired model runs (see the summary).

Run:  /opt/miniconda3/envs/uganda_metamodel_env/bin/python rdm_fitness.py
Out:  trained_models/rdm_fitness_<RUN_ID>.csv and trained_models/rdm_fitness_<RUN_ID>_summary.md
"""
import os
from itertools import combinations

os.environ.setdefault("MPLBACKEND", "Agg")

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from evaluate_sector_model import MODEL_PATH, RUN_ID, TRAINED_MODELS_DIR, TRAINING_DATA_PATH
from retrain_sector import clean
from utils.ml_utils_v2 import XGBMultiOutputPipeline

OUT_CSV = os.path.join(TRAINED_MODELS_DIR, f"rdm_fitness_{RUN_ID}.csv")
OUT_MD = os.path.join(TRAINED_MODELS_DIR, f"rdm_fitness_{RUN_ID}_summary.md")
YEARS = (2035, 2050, 2070)
QUANTILES = (10, 25, 50, 75, 90)
SEED = 20261116


def totals(y: pd.DataFrame) -> pd.DataFrame:
    """Total emissions (sum of the 23 categories) and total cost, as the tools compute them."""
    out = {}
    for yr in YEARS:
        out[f"emissions_total_{yr}"] = y[[c for c in y if c.startswith("emission_") and c.endswith(f"_yr{yr}")]].sum(1)
        out[f"cost_total_{yr}"] = -y[[c for c in y if c.startswith("cost_") and c.endswith(f"_yr{yr}")]].sum(1)
    return pd.DataFrame(out, index=y.index)


def tree(X, y, depth):   # as backend/rdm/tools/technical.py::_tree
    clf = DecisionTreeClassifier(max_depth=depth, class_weight="balanced",
                                 min_samples_leaf=max(10, len(y) // 20), random_state=0).fit(X, y)
    return clf, balanced_accuracy_score(y, clf.predict(X))


def best_pair(X, y):
    return max(((p, *tree(X[list(p)], y, 2)) for p in combinations(X.columns, 2)), key=lambda t: t[2])


def main():
    df = pd.read_parquet(TRAINING_DATA_PATH).drop(columns=["primary_id", "future_id"])
    targets = [c for c in df.columns if not c.startswith("group_")]
    mulp = XGBMultiOutputPipeline(df=clean(df), targets=targets)
    mulp.preprocess()
    X = mulp.X_test
    pipe = joblib.load(MODEL_PATH)
    true = totals(mulp.y_test.reset_index(drop=True))
    pred = totals(pd.DataFrame(pipe.predict(X), columns=targets))
    X = X.reset_index(drop=True)
    n = len(X)
    xcols = [c for c in X.columns if "_X_" in c]
    lcols = [c for c in X.columns if c not in xcols]
    rows = []

    # A. pass / fail at a threshold (fail = above the threshold: more emissions, more cost)
    for col in true.columns:
        for q in QUANTILES:
            thr = np.percentile(true[col], q)
            tf, pf = true[col] > thr, pred[col] > thr
            wrong = tf != pf
            near = (np.abs(true[col] - thr) <= 0.02 * abs(thr))
            rows.append({"check": "A threshold", "metric": col, "threshold": f"p{q} = {thr:.4g}",
                         "agreement": 1 - wrong.mean(),
                         "false_pass (true fail, surrogate pass)": (tf & ~pf).sum() / max(tf.sum(), 1),
                         "false_fail (true pass, surrogate fail)": (~tf & pf).sum() / max((~tf).sum(), 1),
                         "errors within 2% of threshold": (wrong & near).sum() / max(wrong.sum(), 1),
                         "share_fail_true": tf.mean(), "share_fail_surrogate": pf.mean()})

    # B. failure share in regions: one input in its bottom or top third, everything else varying
    col = "emissions_total_2050"
    thr = np.median(true[col])
    tf, pf = true[col] > thr, pred[col] > thr
    for c in lcols + xcols:
        for name, m in (("bottom third", X[c] <= 1 / 3), ("top third", X[c] >= 2 / 3)):
            rows.append({"check": "B region", "metric": col, "threshold": f"p50 = {thr:.4g}",
                         "region": f"{c}: {name}", "n_runs": int(m.sum()),
                         "share_fail_true": tf[m].mean(), "share_fail_surrogate": pf[m].mean(),
                         "abs_diff_share": abs(tf[m].mean() - pf[m].mean())})

    # C. scenario discovery on the 13 uncertainties, as the tool does it, on true and on surrogate labels
    for col in ("emissions_total_2050", "cost_total_2050"):
        for q in (50, 75):
            thr = np.percentile(true[col], q)
            yt, yp = (true[col] > thr).astype(int), (pred[col] > thr).astype(int)
            pt, ct, st = best_pair(X[xcols], yt)
            pp, cp, sp = best_pair(X[xcols], yp)
            boxes_agree = (ct.predict(X[list(pt)]) == cp.predict(X[list(pp)])).mean()
            rows.append({"check": "C scenario discovery", "metric": col, "threshold": f"p{q} = {thr:.4g}",
                         "pair_true": " + ".join(pt), "pair_surrogate": " + ".join(pp),
                         "same_pair": set(pt) == set(pp), "bal_acc_true": st, "bal_acc_surrogate": sp,
                         "agreement": boxes_agree})

    # D. ordering of random pairs of runs
    rng = np.random.default_rng(SEED)
    i, j = rng.integers(0, n, 200_000), rng.integers(0, n, 200_000)
    keep = i != j
    i, j = i[keep], j[keep]
    for col in true.columns:
        t, p = true[col].to_numpy(), pred[col].to_numpy()
        same = np.sign(t[i] - t[j]) == np.sign(p[i] - p[j])
        close = np.abs(t[i] - t[j]) <= 0.02 * np.abs(t[i])
        rows.append({"check": "D ordering", "metric": col, "agreement": same.mean(),
                     "agreement_within_2pct": same[close].mean(), "n_pairs_within_2pct": int(close.sum())})

    r = pd.DataFrame(rows)
    r.to_csv(OUT_CSV, index=False)
    summary(r, n)


def summary(r: pd.DataFrame, n: int):
    a, b, c, d = (r[r.check == k] for k in ("A threshold", "B region", "C scenario discovery", "D ordering"))
    L = [f"# Is the surrogate fit for RDM? (held-out runs, true model vs surrogate)\n",
         f"Run `{RUN_ID}` | {n:,} held-out runs | script `rdm_fitness.py` (2026-11-16)\n",
         "## A. Pass / fail at a threshold (fail = above it)\n",
         "| Metric | Threshold | Agreement | False pass | False fail | Errors within 2% of threshold |",
         "|---|---|---|---|---|---|"]
    for _, x in a.iterrows():
        L.append(f"| {x.metric} | {x.threshold} | {x.agreement:.3f} | "
                 f"{x['false_pass (true fail, surrogate pass)']:.3f} | {x['false_fail (true pass, surrogate fail)']:.3f}"
                 f" | {x['errors within 2% of threshold']:.2f} |")
    L += ["\n## B. Failure share by region (2050 total emissions above the median)\n",
          f"{len(b)} regions (each lever and uncertainty, bottom and top third). Absolute difference between the true "
          f"and the surrogate failure share: median {b.abs_diff_share.median():.4f}, 95th percentile "
          f"{b.abs_diff_share.quantile(.95):.4f}, max {b.abs_diff_share.max():.4f} "
          f"({b.loc[b.abs_diff_share.idxmax(), 'region']}).\n",
          "\n## C. Scenario discovery (the tool's CART pair search over the 13 uncertainties)\n",
          "| Metric | Threshold | Pair (true) | Pair (surrogate) | Same pair | Bal. acc. true / surrogate | Box agreement |",
          "|---|---|---|---|---|---|---|"]
    for _, x in c.iterrows():
        L.append(f"| {x.metric} | {x.threshold} | {x.pair_true} | {x.pair_surrogate} | {x.same_pair} | "
                 f"{x.bal_acc_true:.3f} / {x.bal_acc_surrogate:.3f} | {x.agreement:.3f} |")
    L += ["\n## D. Ordering of random pairs of runs\n", "| Metric | Same order | Same order, pairs within 2% |",
          "|---|---|---|"]
    for _, x in d.iterrows():
        L.append(f"| {x.metric} | {x.agreement:.3f} | {x.agreement_within_2pct:.3f} (n = {x.n_pairs_within_2pct:,}) |")
    L += ["\n## Not checked: thresholds relative to BAU in the same future\n",
          "The tools' 'X% below BAU' test compares a policy with BAU in the same future. Every held-out run has its own "
          "future, so there is no true BAU to compare with. Checking it needs paired model runs: for a sample of "
          "futures, BAU and a few policies (for example 200 futures x 3 runs, about 30 hours of model time at about "
          "3 minutes per run)."]
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
