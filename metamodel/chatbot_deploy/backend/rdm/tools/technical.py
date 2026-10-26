"""
Technical tools: run on the XGBoost surrogate, identical in v0 and v1.

  exploratory_modeling    RDM 1 · run policies across many futures (BAU added, same futures)
  vulnerability_analysis  RDM 2 · label each future pass / fail against the user's threshold
  scenario_discovery      RDM 2 · the two uncertainties that best explain the failures
  trade_off_analysis      RDM 3 · emissions vs costs across the same futures

Every result is an ensemble: no tool returns one number from one future. The uncertainties are
reported as positions in their sampled range (0 = low end, 1 = high end) until their real units
are compiled (open item in docs/archive/rdm_tools_design.md).
"""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from backend.rdm.data.lhc import lever_bounds
from backend.rdm.harness.state import Ensemble, State
from backend.rdm.surrogate import Surrogate
from backend.rdm.tools.common import ToolError, group_id, groups, num, spread

DEFAULT_FUTURES = 500
MAX_FUTURES = 5000
BAU = "BAU"
X_SCALE_NOTE = "Uncertainties are positions in their sampled range: 0 = low end, 0.5 = central, 1 = high end."
MONEY = ("cost", "benefit", "net")       # metric prefixes reported only as change vs BAU
MONEY_NOTE = ("Costs and benefits are shown only as changes against BAU on the same futures: their levels are "
              "differences against one fixed reference run, not a policy's money. Every cost_* is money spent "
              "(positive = more spending); benefit_* and net_benefit are good for the country (positive = better). "
              "cost_pct_gdp changes are in percentage points of GDP. What the cost types hold: cost_technical is "
              "spending on the transformations; cost_system is transport system costs (negative = savings from "
              "fewer vehicle-km); cost_fuel holds only biogas and waste-to-energy revenue (negative = more revenue). "
              "Fuel spending is in benefit_sector_specific and operating savings in benefit_technical_savings. Costs "
              "and benefits that do not depend on a lever's level (for example the health value of diets) cancel "
              "out and do not show.")


# ── exploratory_modeling ─────────────────────────────────────────────────────

def exploratory_modeling(state: State, sur: Surrogate, policies: list, x_ranges: dict | None = None,
                         n_futures: int = DEFAULT_FUTURES, seed: int = 0, metrics: list | None = None,
                         years: list | None = None) -> dict:
    run = sur.run
    if not policies:
        raise ToolError("NO_POLICY", "Give at least one policy: [{'name': …, 'levers': {lever_id: level}}]")
    if not 50 <= int(n_futures) <= MAX_FUTURES:
        raise ToolError("BAD_N_FUTURES", f"n_futures must be between 50 and {MAX_FUTURES}")
    n_futures = int(n_futures)

    named = {}
    for p in policies:
        name = str(p.get("name", "")).strip()
        if not name or name.upper() == BAU or name in named:
            raise ToolError("BAD_POLICY_NAME", f"Each policy needs a unique name other than {BAU!r} (got {name!r})")
        levers = {}
        for k, v in (p.get("levers") or {}).items():
            gid = group_id(run, k, "L")
            v = float(v)
            lo, hi = lever_bounds(run)[gid]
            if not lo <= v <= hi:
                raise ToolError("LEVEL_OUT_OF_RANGE", f"Lever {gid} level {v} is outside the range explored in the model runs "
                                f"[{lo}, {hi}]; the surrogate cannot be tested beyond it")
            levers[gid] = v
        if not levers:
            raise ToolError("EMPTY_POLICY", f"Policy {name!r} sets no lever")
        named[name] = levers

    ranges = {x: (0.0, 1.0) for x in sur.x_ids}
    for k, rng in (x_ranges or {}).items():
        gid = group_id(run, k, "X")
        lo, hi = (float(rng[0]), float(rng[1]))
        if not 0.0 <= lo < hi <= 1.0:
            raise ToolError("X_FIXED" if lo == hi else "BAD_X_RANGE", f"Range for uncertainty {gid} must satisfy 0 ≤ low < high ≤ 1 "
                            f"(an uncertainty is never fixed at one value); got {rng}")
        ranges[gid] = (lo, hi)

    metrics = metrics or ["emissions_total", "cost_total"]
    years = [int(y) for y in (years or sur.years)]
    for m in metrics:
        for y in years:
            try:
                sur.column(m, y)
            except ValueError as e:
                raise ToolError("BAD_METRIC", str(e))

    u = qmc.LatinHypercube(d=len(sur.x_ids), seed=seed).random(n_futures)
    futures = pd.DataFrame({f"X_{x}": ranges[x][0] + u[:, i] * (ranges[x][1] - ranges[x][0])
                            for i, x in enumerate(sur.x_ids)})
    all_policies = {BAU: {}, **named}
    preds = {}
    for name, levers in all_policies.items():
        design = futures.copy()
        for lid in sur.lever_ids:
            design[f"L_{lid}"] = levers.get(lid, 0.0)
        preds[name] = sur.predict(design)

    ens = state.add(Ensemble(id=state.new_id("E"), futures=futures, x_ranges=ranges,
                             policies=all_policies, predictions=preds, seed=seed))

    g = groups(run)
    results = {}
    for m in metrics:
        by_year = {}
        for y in years:
            col = sur.column(m, y)
            bau = preds[BAU][col]
            money = m.startswith(MONEY)
            row = {} if money else {BAU: {"value": spread(bau)}}
            for name in named:
                v = preds[name][col]
                entry = {"change_vs_bau": spread(v - bau)} if money else {"value": spread(v), "change_vs_bau": spread(v - bau)}
                if m.startswith("emissions"):
                    entry["change_vs_bau_pct"] = spread(100 * (v - bau) / bau.abs().where(bau.abs() > 1e-6), 1)
                row[name] = entry
            by_year[str(y)] = row
        results[m] = {"unit": "percentage points of GDP" if m == "cost_pct_gdp" else sur.unit(m), "by_year": by_year}

    return {
        "ensemble_id": ens.id,
        "n_futures": n_futures,
        "seed": seed,
        "policies": {n: {str(l): {"name": g[l]["name"], "level": v} for l, v in lv.items()} for n, lv in named.items()},
        "bau": "All levers at 0 on the same futures; every change is paired future by future.",
        "uncertainties_sampled": {str(x): {"name": g[x]["name"], "range": list(ranges[x])} for x in sur.x_ids},
        "note": X_SCALE_NOTE + (" " + MONEY_NOTE if any(m.startswith(MONEY) for m in metrics) else ""),
        "results": results,
    }


# ── vulnerability_analysis ───────────────────────────────────────────────────

THRESHOLD_TYPES = ("absolute", "reduction_vs_bau_pct", "change_vs_bau")


def _values(ens: Ensemble, sur: Surrogate, policy: str, metric: str, year: int, threshold_type: str) -> pd.Series:
    if policy not in ens.policies or policy == BAU:
        raise ToolError("UNKNOWN_POLICY", f"Policy {policy!r} is not in ensemble {ens.id}; policies: "
                        f"{[p for p in ens.policies if p != BAU]}")
    try:
        col = sur.column(metric, int(year))
    except ValueError as e:
        raise ToolError("BAD_METRIC", str(e))
    v = ens.predictions[policy][col]
    if threshold_type == "absolute":
        return v
    bau = ens.predictions[BAU][col]
    if threshold_type == "change_vs_bau":
        return v - bau
    return 100 * (bau - v) / bau.abs().where(bau.abs() > 1e-6)


def vulnerability_analysis(state: State, sur: Surrogate, ensemble_id: str, policy: str, metric: str,
                           year: int, threshold: float | None = None, threshold_type: str | None = None,
                           pass_if: str | None = None) -> dict:
    ens = state.get(ensemble_id)
    money = metric.startswith(MONEY)
    threshold_type = threshold_type or ("change_vs_bau" if money else "absolute")
    if threshold_type not in THRESHOLD_TYPES:
        raise ToolError("BAD_THRESHOLD_TYPE", f"threshold_type must be one of {THRESHOLD_TYPES}")
    if money and threshold_type != "change_vs_bau":
        raise ToolError("MONEY_NEEDS_CHANGE_VS_BAU", f"{metric} can only be judged as a change against BAU (threshold_type 'change_vs_bau'): its "
                        f"level is a difference against a fixed reference run, not the policy's money")
    unit = {"reduction_vs_bau_pct": "% reduction vs BAU",
            "change_vs_bau": ("percentage points of GDP" if metric == "cost_pct_gdp" else sur.unit(metric)) + " change vs BAU",
            }.get(threshold_type, sur.unit(metric))
    values = _values(ens, sur, policy, metric, year, threshold_type)

    if threshold is None:
        return {
            "status": "needs_threshold",
            "ask_the_user": (f"Which value of {metric} in {year} counts as failure for {policy!r}? "
                             f"Give it in {unit}."),
            "to_help_choose": {"metric": metric, "year": int(year), "unit": unit, "distribution": spread(values)},
        }

    if pass_if is None:
        # Less is better for emissions and money spent (cost_*); more is better for a reduction, benefits and net benefit.
        pass_if = "above" if threshold_type == "reduction_vs_bau_pct" or metric.startswith(("benefit", "net")) else "below"
    if pass_if not in ("above", "below"):
        raise ToolError("BAD_PASS_IF", "pass_if must be 'above' or 'below'")
    ok = values >= threshold if pass_if == "above" else values <= threshold
    fail = ~ok | values.isna()
    label_id = state.new_id("V")
    ens.labels[label_id] = {"policy": policy, "metric": metric, "year": int(year), "threshold": float(threshold),
                            "threshold_type": threshold_type, "pass_if": pass_if, "fail": fail}
    n_fail = int(fail.sum())
    return {
        "label_id": label_id,
        "ensemble_id": ens.id,
        "criterion": f"{policy} passes when {metric} in {year} is {pass_if} {threshold} {unit}",
        "n_futures": int(len(fail)),
        "n_fail": n_fail,
        "share_fail": num(n_fail / len(fail)),
        "value_in_failing_futures": spread(values[fail]),
        "value_in_passing_futures": spread(values[~fail]),
        "unit": unit,
        "next": ("scenario_discovery can explain the failures" if 0 < n_fail < len(fail)
                 else "no mix of pass and fail: nothing for scenario_discovery to explain"),
    }


# ── scenario_discovery ───────────────────────────────────────────────────────

def _tree(X: pd.DataFrame, y: pd.Series, depth: int) -> tuple:
    clf = DecisionTreeClassifier(max_depth=depth, class_weight="balanced",
                                 min_samples_leaf=max(10, len(y) // 20), random_state=0)
    clf.fit(X, y)
    return clf, balanced_accuracy_score(y, clf.predict(X))


def _leaves(clf: DecisionTreeClassifier, cols: list, ranges: dict) -> list:
    """Every leaf of a fitted tree as (node id, {feature: (low, high)})."""
    t = clf.tree_

    def walk(node, bounds):
        if t.children_left[node] == -1:
            return [(node, bounds)]
        f, thr = cols[t.feature[node]], t.threshold[node]
        lo, hi = bounds[f]
        return (walk(t.children_left[node], {**bounds, f: (lo, min(hi, thr))})
                + walk(t.children_right[node], {**bounds, f: (max(lo, thr), hi)}))

    return walk(0, {c: ranges[c] for c in cols})


def scenario_discovery(state: State, sur: Surrogate, ensemble_id: str, label_id: str | None = None,
                       pair: list | None = None, n_bins: int = 4) -> dict:
    run = sur.run
    ens = state.get(ensemble_id)
    if not ens.labels:
        raise ToolError("NO_LABELS", "No pass / fail labels on this ensemble yet: run vulnerability_analysis first")
    label_id = label_id or list(ens.labels)[-1]
    if label_id not in ens.labels:
        raise ToolError("UNKNOWN_LABEL", f"No label {label_id!r} on ensemble {ens.id}; labels: {list(ens.labels)}")
    lab = ens.labels[label_id]
    fail = lab["fail"].astype(int)
    n, n_fail = len(fail), int(fail.sum())
    if n_fail == 0 or n_fail == n:
        return {"status": "nothing_to_discover", "share_fail": num(n_fail / n),
                "explanation": "Every future passes or every future fails: no condition separates them."}

    g = groups(run)
    xcols = [f"X_{x}" for x in sur.x_ids if ens.x_ranges[x][1] > ens.x_ranges[x][0]]
    X = ens.futures[xcols]

    single = sorted(((c, _tree(X[[c]], fail, 1)[1]) for c in xcols), key=lambda t: -t[1])
    _, score_all = _tree(X, fail, 3)

    if pair:
        pcols = [f"X_{group_id(run, p, 'X')}" for p in pair]
        if len(set(pcols)) != 2:
            raise ToolError("BAD_PAIR", "pair must name two different uncertainties")
        clf, score_pair = _tree(X[pcols], fail, 2)
        chosen_by = "user"
    else:
        best = max(((list(p), *_tree(X[list(p)], fail, 2)) for p in combinations(xcols, 2)), key=lambda t: t[2])
        pcols, clf, score_pair = best
        chosen_by = "best separation of pass and fail (CART, depth 2)"

    # Boxes: leaves of the pair tree where failures concentrate.
    ranges = {c: ens.x_ranges[int(c[2:])] for c in pcols}
    leaf_ids = clf.apply(X[pcols])
    base = n_fail / n
    boxes = []
    for node, bounds in _leaves(clf, pcols, ranges):
        inside = leaf_ids == node
        k = int(inside.sum())
        kf = int(fail[inside].sum())
        if k and kf / k > base:
            boxes.append({
                "conditions": {g[int(c[2:])]["name"]: [num(lo, 2), num(hi, 2)] for c, (lo, hi) in bounds.items()},
                "density": num(kf / k),           # share of futures in the box that fail
                "coverage": num(kf / n_fail),     # share of all failures inside the box
                "n_futures": k,
            })
    boxes.sort(key=lambda b: -b["density"])

    # Pass-rate map over the pair.
    edges = {c: np.linspace(*ranges[c], n_bins + 1) for c in pcols}
    bx = {c: np.clip(np.digitize(X[c], edges[c][1:-1]), 0, n_bins - 1) for c in pcols}
    grid = []
    for i in range(n_bins):
        row = []
        for j in range(n_bins):
            cell = (bx[pcols[0]] == i) & (bx[pcols[1]] == j)
            k = int(cell.sum())
            row.append(num(1 - fail[cell].mean(), 2) if k else None)
        grid.append(row)

    return {
        "label_id": label_id,
        "criterion": f"{lab['policy']}: {lab['metric']} {lab['year']} {lab['pass_if']} {lab['threshold']} "
                     f"({lab['threshold_type']})",
        "share_fail": num(base),
        "pair": [{"id": int(c[2:]), "name": g[int(c[2:])]["name"]} for c in pcols],
        "pair_chosen_by": chosen_by,
        "failure_boxes": boxes[:2],
        "pass_rate_map": {
            "rows": {"uncertainty": g[int(pcols[0][2:])]["name"], "bin_edges": [num(e, 2) for e in edges[pcols[0]]]},
            "columns": {"uncertainty": g[int(pcols[1][2:])]["name"], "bin_edges": [num(e, 2) for e in edges[pcols[1]]]},
            "pass_rate": grid,
        },
        "how_well_explained": {
            "pair": num(score_pair),
            "all_uncertainties": num(score_all),
            "note": "Balanced accuracy of a small tree separating pass from fail (0.5 = no better than chance). "
                    "The gap between the two is what the other uncertainties add.",
        },
        "uncertainty_ranking": [{"name": g[int(c[2:])]["name"], "id": int(c[2:]), "score": num(s)}
                                for c, s in single[:5]],
        "note": X_SCALE_NOTE,
    }


# ── trade_off_analysis ───────────────────────────────────────────────────────

def trade_off_analysis(state: State, sur: Surrogate, ensemble_id: str, year: int = 2050,
                       policies: list | None = None) -> dict:
    ens = state.get(ensemble_id)
    names = policies or [p for p in ens.policies if p != BAU]
    unknown = [p for p in names if p not in ens.policies or p == BAU]
    if unknown or not names:
        raise ToolError("UNKNOWN_POLICY", f"Unknown policies {unknown}; ensemble {ens.id} has {[p for p in ens.policies if p != BAU]}")
    try:
        ce, cc = sur.column("emissions_total", int(year)), sur.column("cost_total", int(year))
        cn, cg = sur.column("net_benefit", int(year)), sur.column("cost_pct_gdp", int(year))
    except ValueError as e:
        raise ToolError("BAD_METRIC", str(e))
    P = ens.predictions
    e_bau, c_bau = P[BAU][ce], P[BAU][cc]

    per_policy = {}
    med = {}
    for p in names:
        de, dc = P[p][ce] - e_bau, P[p][cc] - c_bau
        abated = -de
        usd_per_t = (1000 * dc / abated).where(abated > 0.1)     # bn USD / Mt = 1,000 USD per t
        dn = P[p][cn] - P[BAU][cn]
        dg = P[p][cg] - P[BAU][cg]
        per_policy[p] = {
            "emissions": spread(P[p][ce]), "emissions_change_vs_bau": spread(de),
            "cost_change_vs_bau": spread(dc), "cost_change_vs_bau_pct_points_of_gdp": spread(dg, 3),
            "net_benefit_change_vs_bau": spread(dn),
            "cost_per_tonne_abated_usd": spread(usd_per_t, 1),
        }
        med[p] = (float(de.median()), float(dc.median()))

    pairwise = []
    for a, b in combinations(names, 2):
        le = P[a][ce] < P[b][ce]
        lc = P[a][cc] < P[b][cc]
        pairwise.append({"a": a, "b": b,
                         "share_a_lower_emissions": num(le.mean()), "share_a_lower_cost": num(lc.mean()),
                         "share_a_lower_both": num((le & lc).mean()),
                         "share_b_lower_both": num((~le & ~lc).mean())})

    dominated = [p for p in names
                 if any(q != p and med[q][0] <= med[p][0] and med[q][1] <= med[p][1] and med[q] != med[p]
                        for q in names)]
    return {
        "ensemble_id": ens.id,
        "year": int(year),
        "units": {"emissions": "Mt CO₂e", "cost and net benefit": "billion USD", "cost_per_tonne_abated": "USD per t CO₂e"},
        "policies": per_policy,
        "pairwise": pairwise,
        "dominated_on_medians": dominated,
        "note": ("Changes are against BAU in the same futures. Cost is the sum of the technical, system and fuel cost "
                 "types (money spent, positive = more spending); net benefit adds every benefit and subtracts the cost "
                 "(positive = better for the country). Cost per tonne counts only the cost types, not the operating "
                 "savings or fuel spending in the benefit types. " + MONEY_NOTE),
    }
