"""
build_lever_response_map.py
---------------------------
What each input of the surrogate moves among the surrogate's outputs, and by how
much, with EVERY other input varying at the same time.

This is the response-side counterpart of Object 1 (build_lever_digest.py, removed 2026-10-30:
nothing read its output; the agent gets a lever's inputs from model_network). Object 1
says which SISEPUEDE input fields a lever sets; this map says which surrogate outputs
(sector emissions, costs, benefits, GDP) respond when the lever moves, and how
strongly. It covers the 13 X groups too, which Object 1 cannot: an X group has no
fields to map, but it does have outputs it moves.

Why nothing is held fixed. The agent's job is exploratory analysis over the joint
L x X space, so a lever's effect "with everything else at BAU" answers a question
nobody asks: the agent never evaluates a policy in one future with the other levers
off. Every statistic here is therefore marginal over the other 66 inputs, drawn
jointly from their sampled range. The training hypercube's inputs are independent
and uniform on [0, 1] (max |corr| 0.0095, every std 0.2887), so drawing uniformly
stays inside the space the surrogate was fitted on.

Two measures per (input, output) pair, answering two different questions:

  swing   How much does the output change when this input goes from 0 to 1?
          For each of N_SWING base points taken from the real hypercube trials, the
          input is set to 0, 0.25, 0.5, 0.75 and 1 while the other 66 keep that
          trial's values; the paired difference Y(1) - Y(0) is summarised by its
          median and p10/p90 across trials. In the output's own units (Mt CO2e,
          billion USD), so it can be read as a magnitude. `sign_agreement` is the
          share of trials whose difference has the median's sign: 1.0 means the
          direction never depends on the rest of the configuration.

  share   How much of the output's variation across the explored space is due to
          this input? Sobol total-order index S_T (Jansen estimator) and first-order
          index S_1 (Saltelli 2010), from a scrambled Sobol design of N_SOBOL x
          (d + 2) runs. S_T - S_1 is the part that exists only through interaction
          with other inputs. Bootstrap 90% interval on S_T.

The two can disagree, and the disagreement is informative: a lever can have a large
swing on an output whose variance is dominated by an X (large swing, small share), or
be the only driver of an output that barely moves (small swing, share near 1).

Outputs (both regenerated from scratch by one run; nothing here depends on a
particular surrogate version beyond the model path):
  lever_response_map_full.csv  one row per (input, output), every statistic
  lever_response_map.json      compact per-input and per-output summaries

Run from chatbot_deploy/ (needs xgboost; the app's own env does not ship it):
  /opt/miniconda3/envs/uganda_metamodel_env/bin/python -m backend.scripts.build_lever_response_map
  ... --summary-only     re-summarise the existing CSV (after changing the rule)
  ... --model PATH       map a different surrogate (e.g. the retrained one)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import qmc

from backend.services.predictor import COST_BENEFIT_LABELS

_BACKEND = Path(__file__).resolve().parent.parent
_METAMODEL = _BACKEND.parent.parent
_RUN = "2026-05-30t21;35;56.244639"
_MODEL = _METAMODEL / "surrogate_model_sector" / "trained_models" / f"xgb_pipeline_sector_independent_{_RUN}.pkl"
_TRAINING = _METAMODEL / "data" / "training" / f"training_data_sector_{_RUN}.parquet"
_METRICS = _METAMODEL / "surrogate_model_sector" / "trained_models" / f"metrics_{_RUN}.csv"
_REGISTRY = _BACKEND / "feature_registry.json"
_TARGETS = _BACKEND / "target_distributions.json"
_SECTORS = _BACKEND / "sector_categories.json"

N_SWING = 2000          # base trials for the swing curves
N_SOBOL = 4096          # Sobol base sample (power of 2)
N_BOOT = 200            # bootstrap resamples for the S_T interval
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
# 2025 is excluded: six years after the 2019 base the transformations have barely
# ramped, the targets are near-constant (median std 2e-14) and every index is noise.
YEARS = (2035, 2040, 2050, 2060, 2070)
SEED = 20260929

# Derived outputs the agent actually talks about, built from the raw targets the same
# way predictor.predict() builds them.
DERIVED = ("emission_total", "benefit_total", "cost_total", "net_total")


# ── Inputs and outputs ──────────────────────────────────────────────────────────

def _load_inputs(model) -> pd.DataFrame:
    """One row per surrogate input: group id, L/X, display name, sector."""
    reg = json.loads(_REGISTRY.read_text())
    rows = []
    for kind, block in (("L", reg["lever_features"]), ("X", reg["exogenous_features"])):
        for gid, meta in block.items():
            rows.append({
                "group_id": int(gid), "kind": kind, "column": meta["training_column"],
                "display_name": meta["display_name"], "input_sector": meta["sector"],
            })
    inputs = pd.DataFrame(rows).set_index("column")
    cols = [str(c) for c in model.feature_names_in_]
    missing = set(cols) - set(inputs.index)
    if missing:
        raise ValueError(f"model features absent from the registry: {sorted(missing)}")
    return inputs.loc[cols].reset_index()


def _output_meta(raw_targets: list[str]) -> pd.DataFrame:
    """One row per analysed output (raw targets for YEARS + derived totals)."""
    sectors = json.loads(_SECTORS.read_text())
    rows = []
    for t in raw_targets:
        stem, yr = t.rsplit("_yr", 1)
        yr = int(yr)
        if yr not in YEARS:
            continue
        if stem.startswith("emission_"):
            slug = stem[len("emission_"):]
            rows.append((t, "emissions", slug, sectors[slug]["display"], yr, "Mt CO2e"))
        elif stem.startswith("benefit_"):
            typ = stem[len("benefit_"):]
            rows.append((t, "benefits", typ, f"Benefit: {COST_BENEFIT_LABELS.get(typ, typ)}", yr, "bn USD"))
        elif stem.startswith("cost_"):
            typ = stem[len("cost_"):]
            rows.append((t, "costs", typ, f"Cost: {COST_BENEFIT_LABELS.get(typ, typ)}", yr, "bn USD"))
        elif stem.startswith("gdp_"):
            rows.append((t, "gdp", "gdp", "GDP", yr, "bn USD"))
    for d in DERIVED:
        fam = {"emission_total": "emissions", "benefit_total": "benefits",
               "cost_total": "costs", "net_total": "net"}[d]
        label = {"emission_total": "Total net emissions", "benefit_total": "Total benefits",
                 "cost_total": "Total costs", "net_total": "Net benefit (benefits + costs)"}[d]
        unit = "Mt CO2e" if d == "emission_total" else "bn USD"
        for yr in YEARS:
            rows.append((f"{d}_yr{yr}", fam, "total", label, yr, unit))
    return pd.DataFrame(rows, columns=["output", "family", "category", "label", "year", "unit"])


def _predict(model, X: np.ndarray, feature_cols: list[str], raw_targets: list[str],
             outputs: list[str]) -> np.ndarray:
    """Surrogate predictions for the analysed outputs, derived totals included."""
    y = model.predict(pd.DataFrame(X, columns=feature_cols))
    raw = pd.DataFrame(y, columns=raw_targets)
    for yr in YEARS:
        s = f"_yr{yr}"
        raw[f"emission_total{s}"] = raw[[c for c in raw_targets if c.startswith("emission_") and c.endswith(s)]].sum(axis=1)
        raw[f"benefit_total{s}"] = raw[[c for c in raw_targets if c.startswith("benefit_") and c.endswith(s)]].sum(axis=1)
        raw[f"cost_total{s}"] = raw[[c for c in raw_targets if c.startswith("cost_") and c.endswith(s)]].sum(axis=1)
        raw[f"net_total{s}"] = raw[f"benefit_total{s}"] + raw[f"cost_total{s}"]
    return raw[outputs].to_numpy()


# ── The two measures ────────────────────────────────────────────────────────────

def swing(model, base: np.ndarray, feature_cols, raw_targets, outputs) -> dict[str, np.ndarray]:
    """Paired 0 -> 1 swing and the 5-level median curve, per (input, output)."""
    n, d = base.shape
    k = len(outputs)
    out = {name: np.empty((d, k)) for name in
           ("swing_median", "swing_p10", "swing_p90", "sign_agreement",
            *[f"curve_{v:g}" for v in LEVELS[1:]])}
    for i in range(d):
        stacked = np.repeat(base[None, :, :], len(LEVELS), axis=0)
        for j, v in enumerate(LEVELS):
            stacked[j, :, i] = v
        y = _predict(model, stacked.reshape(-1, d), feature_cols, raw_targets, outputs)
        y = y.reshape(len(LEVELS), n, k)
        delta = y[-1] - y[0]
        med = np.median(delta, axis=0)
        out["swing_median"][i] = med
        out["swing_p10"][i] = np.quantile(delta, 0.10, axis=0)
        out["swing_p90"][i] = np.quantile(delta, 0.90, axis=0)
        out["sign_agreement"][i] = (np.sign(delta) == np.sign(med)).mean(axis=0)
        for j, v in enumerate(LEVELS[1:], start=1):
            out[f"curve_{v:g}"][i] = np.median(y[j] - y[0], axis=0)
    return out


def sobol(model, d: int, feature_cols, raw_targets, outputs, rng) -> dict[str, np.ndarray]:
    """First- and total-order Sobol indices with a bootstrap interval on S_T."""
    ab = qmc.Sobol(d=2 * d, scramble=True, seed=rng).random(N_SOBOL)
    A, B = ab[:, :d], ab[:, d:]
    fA = _predict(model, A, feature_cols, raw_targets, outputs)
    fB = _predict(model, B, feature_cols, raw_targets, outputs)
    var = np.var(np.vstack([fA, fB]), axis=0)
    safe = np.where(var > 0, var, np.nan)

    k = len(outputs)
    S1, ST = np.empty((d, k)), np.empty((d, k))
    ST_lo, ST_hi = np.empty((d, k)), np.empty((d, k))
    # Bootstrap as resample counts: (N_BOOT x N) @ (N x k) avoids materialising
    # N_BOOT copies of the squared differences.
    idx = rng.integers(0, N_SOBOL, size=(N_BOOT, N_SOBOL))
    counts = np.stack([np.bincount(r, minlength=N_SOBOL) for r in idx]) / N_SOBOL
    for i in range(d):
        ABi = A.copy()
        ABi[:, i] = B[:, i]
        fABi = _predict(model, ABi, feature_cols, raw_targets, outputs)
        sq = (fA - fABi) ** 2
        S1[i] = np.mean(fB * (fABi - fA), axis=0) / safe
        ST[i] = 0.5 * np.mean(sq, axis=0) / safe
        bs = 0.5 * (counts @ sq) / safe                   # (N_BOOT, k)
        ST_lo[i], ST_hi[i] = np.quantile(bs, [0.05, 0.95], axis=0)
    return {"S1": S1, "ST": ST, "ST_lo": ST_lo, "ST_hi": ST_hi,
            "output_std": np.broadcast_to(np.sqrt(var), (d, k))}


# ── Assembly ────────────────────────────────────────────────────────────────────

def build(model_path: Path, n_swing: int) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    model = joblib.load(model_path)
    feature_cols = [str(c) for c in model.feature_names_in_]
    raw_targets = json.loads(_TARGETS.read_text())["target_columns"]
    inputs = _load_inputs(model)
    meta = _output_meta(raw_targets)
    outputs = meta["output"].tolist()

    # Swing base points are real hypercube trials, so "everything else" is exactly a
    # configuration the design explored.
    trials = pd.read_parquet(_TRAINING, columns=feature_cols)
    base = trials.sample(n_swing, random_state=SEED).to_numpy()
    level_y = _predict(model, base, feature_cols, raw_targets, outputs)

    t = time.time()
    sw = swing(model, base, feature_cols, raw_targets, outputs)
    print(f"swing: {time.time() - t:.0f}s")
    t = time.time()
    sb = sobol(model, len(feature_cols), feature_cols, raw_targets, outputs, rng)
    print(f"sobol: {time.time() - t:.0f}s")

    d, k = len(feature_cols), len(outputs)
    df = pd.DataFrame({
        "input_column": np.repeat(feature_cols, k),
        "output": np.tile(outputs, d),
        **{name: arr.ravel() for name, arr in {**sw, **sb}.items()},
    })
    df = df.merge(inputs.rename(columns={"column": "input_column"}), on="input_column")
    df = df.merge(meta, on="output")
    q = pd.DataFrame({"output": outputs,
                      "output_median": np.median(level_y, axis=0),
                      "output_p10": np.quantile(level_y, 0.10, axis=0),
                      "output_p90": np.quantile(level_y, 0.90, axis=0)})
    df = df.merge(q, on="output")
    fit = pd.read_csv(_METRICS)[["target", "r2", "smape"]].rename(
        columns={"target": "output", "r2": "surrogate_r2", "smape": "surrogate_smape"})
    df = df.merge(fit, on="output", how="left")
    df["S_interaction"] = df["ST"] - df["S1"]
    lead = ["group_id", "kind", "display_name", "input_sector", "output", "family",
            "category", "label", "year", "unit"]
    return df[lead + [c for c in df.columns if c not in lead]]


# ── Compact summary (what a tool can return) ────────────────────────────────────
#
# An (input, output) pair counts as MOVED when the direction is stable and the effect
# is not negligible:
#   sign_agreement >= MIN_SIGN_AGREEMENT, and either
#   S_T >= MIN_SHARE (the lever is a real driver of that output, however small the
#   output: leak reduction explains 47-88% of fugitive emissions, ~0.02 Mt), or
#   |swing| >= MIN_REL_SWING of the output's median level AND clears an absolute
#   floor (so a 2% change of a near-zero output does not count).
# The sign test is what separates signal from the surrogate's noise: inputs the model
# ignores still produce small non-zero swings, but in both directions (agreement
# 0.6-0.75 for e.g. the hydrogen lever), whereas every real effect found sits above
# 0.95. Both reported horizons follow the charter's 2050 threshold and the model end.
MIN_SIGN_AGREEMENT = 0.9
MIN_SHARE = 0.01
MIN_REL_SWING = 0.02
ABS_FLOOR = {"Mt CO2e": 0.05, "bn USD": 0.01}
REPORT_YEARS = (2050, 2070)
TOP_DRIVERS = 8
WEAK_FIT_R2, WEAK_FIT_SMAPE = 0.8, 25.0


def _sig(x: float, n: int = 3) -> float:
    return float(f"{x:.{n}g}") if np.isfinite(x) else None


def _shape(row) -> str:
    """How the median effect accrues along the lever's range (0 -> 1)."""
    half = row["curve_0.5"] / row["swing_median"] if row["swing_median"] else np.nan
    if not np.isfinite(half):
        return "flat"
    if half >= 0.65:
        return "front-loaded (most of the effect by 0.5)"
    if half <= 0.35:
        return "back-loaded (most of the effect above 0.5)"
    return "roughly linear"


def _moved(df: pd.DataFrame) -> pd.Series:
    rel = df["swing_median"].abs() / df["output_median"].abs().replace(0, np.nan)
    floor = df["unit"].map(ABS_FLOOR)
    return ((df["sign_agreement"] >= MIN_SIGN_AGREEMENT)
            & ((df["ST"] >= MIN_SHARE)
               | ((rel >= MIN_REL_SWING) & (df["swing_median"].abs() >= floor)))
            & (df["output_std"] > 0))


def _effect(r) -> dict:
    rel = r["swing_median"] / abs(r["output_median"]) if r["output_median"] else np.nan
    return {
        "change_0_to_1": _sig(r["swing_median"]),
        "range_p10_p90": [_sig(r["swing_p10"]), _sig(r["swing_p90"])],
        "pct_of_typical_level": _sig(100 * rel, 2),
        "share_of_variance": _sig(r["ST"], 2),
    }


def summarise(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["moved"] = _moved(df)
    weak = (df["surrogate_r2"] < WEAK_FIT_R2) | (df["surrogate_smape"] > WEAK_FIT_SMAPE)
    df["weak_fit"] = weak.fillna(False)
    df["key"] = df["family"] + ":" + df["category"]

    inputs: dict[str, dict] = {}
    for gid, g in df.groupby("group_id", sort=True):
        head = g.iloc[0]
        moved_keys = g.loc[g["moved"], "key"].unique()
        entries = []
        for key in moved_keys:
            rows = g[g["key"] == key].set_index("year")
            strongest = rows.loc[rows["swing_median"].abs().idxmax()]
            entries.append({
                "output": strongest["label"],
                "family": strongest["family"],
                "unit": strongest["unit"],
                "direction": "increases" if strongest["swing_median"] > 0 else "decreases",
                "by_year": {str(y): _effect(rows.loc[y]) for y in REPORT_YEARS if y in rows.index},
                "shape": _shape(strongest),
                "depends_on_other_inputs": _sig(max(0.0, strongest["ST"] - strongest["S1"]), 2),
                **({"surrogate_fit_weak": True} if rows["weak_fit"].any() else {}),
                "_rank": abs(strongest["ST"]),
            })
        entries.sort(key=lambda e: -e.pop("_rank"))
        # A lever that moves nothing still gets its largest direction-stable effect,
        # so "negligible" is shown with its size rather than asserted.
        largest = None
        if not entries:
            stable = g[(g["sign_agreement"] >= MIN_SIGN_AGREEMENT) & (g["output_std"] > 0)
                       & (g["category"] != "total") & (g["swing_median"] != 0)]
            if len(stable):
                r = stable.loc[(stable["swing_median"].abs()
                                / stable["output_median"].abs().replace(0, np.nan)).idxmax()]
                largest = {"output": r["label"], "year": int(r["year"]), "unit": r["unit"], **_effect(r)}
            else:
                largest = {"note": "no direction-stable effect on any output: the surrogate's "
                                   "response to this input is indistinguishable from noise"}
        totals = g[g["category"] == "total"].set_index(["family", "year"])
        inputs[str(gid)] = {
            "group_id": int(gid),
            "kind": head["kind"],
            "name": head["display_name"],
            "sector": head["input_sector"],
            "n_outputs_moved": len(entries),
            "totals": {
                fam: {str(y): _effect(totals.loc[(fam, y)]) for y in REPORT_YEARS}
                for fam in ("emissions", "costs", "benefits")
            },
            "moves": entries,
            **({"largest_effect_below_threshold": largest} if largest else {}),
        }

    # Inverse index: for each output category at the reported horizons, which inputs
    # account for its variation. This is what an outcome-space question needs
    # ("cut transport emissions 30%" -> which levers can, and what else decides it).
    outputs: dict[str, dict] = {}
    for (key, year), g in df[df["year"].isin(REPORT_YEARS)].groupby(["key", "year"]):
        head = g.iloc[0]
        if head["output_std"] <= 0:
            continue
        top = g[g["moved"]].sort_values("ST", ascending=False).head(TOP_DRIVERS)
        o = outputs.setdefault(key, {"output": head["label"], "family": head["family"],
                                      "unit": head["unit"], "by_year": {}})
        o["by_year"][str(year)] = {
            "typical_level": _sig(head["output_median"]),
            "range_p10_p90": [_sig(head["output_p10"]), _sig(head["output_p90"])],
            "variance_explained_by_levers": _sig(g.loc[g["kind"] == "L", "S1"].clip(lower=0).sum(), 2),
            "variance_explained_by_uncertainties": _sig(g.loc[g["kind"] == "X", "S1"].clip(lower=0).sum(), 2),
            "drivers": [{"group_id": int(r["group_id"]), "kind": r["kind"], "name": r["display_name"],
                         "sector": r["input_sector"], "share_of_variance": _sig(r["ST"], 2),
                         "change_0_to_1": _sig(r["swing_median"])} for _, r in top.iterrows()],
            **({"surrogate_fit_weak": True} if bool(g["weak_fit"].any()) else {}),
        }
    constant = sorted(df.loc[df["output_std"] <= 0, "label"].unique())

    return {
        "_metadata": {
            "object": "lever -> surrogate-output response map (everything varies jointly)",
            "surrogate_run": _RUN,
            "method": (
                "Every statistic is marginal over the other 66 inputs, drawn jointly over "
                "their sampled range [0,1]; nothing is held at BAU. change_0_to_1: median "
                "paired change when the input moves 0 -> 1, over 2,000 real hypercube "
                "trials, with p10/p90. share_of_variance: Sobol total-order index (share "
                "of the output's variation across the explored space attributable to the "
                "input, interactions included). depends_on_other_inputs: S_T - S_1, the "
                "part of that share that exists only in combination with other inputs."
            ),
            "moved_rule": {
                "min_sign_agreement": MIN_SIGN_AGREEMENT, "min_share": MIN_SHARE,
                "min_rel_swing": MIN_REL_SWING, "abs_floor": ABS_FLOOR,
            },
            "report_years": list(REPORT_YEARS),
            "constant_outputs": constant,
        },
        "inputs": inputs,
        "outputs": outputs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=_MODEL)
    ap.add_argument("--n-swing", type=int, default=N_SWING)
    ap.add_argument("--out-dir", type=Path, default=_BACKEND)
    ap.add_argument("--summary-only", action="store_true",
                    help="re-summarise an existing full CSV without re-running the surrogate")
    args = ap.parse_args()
    full = args.out_dir / "lever_response_map_full.csv"
    if args.summary_only:
        df = pd.read_csv(full)
    else:
        df = build(args.model, args.n_swing)
        df.to_csv(full, index=False, float_format="%.6g")
        print(f"wrote {full} ({len(df):,} rows)")
    summary = summarise(df)
    path = args.out_dir / "lever_response_map.json"
    path.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    ins = summary["inputs"].values()
    none = [f'{i["group_id"]} {i["name"]}' for i in ins if i["kind"] == "L" and not i["n_outputs_moved"]]
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB); "
          f"levers moving nothing: {len(none)} {none}")


if __name__ == "__main__":
    main()
