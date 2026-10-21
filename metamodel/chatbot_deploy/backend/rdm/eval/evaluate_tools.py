"""
Evaluate the six RDM tools on the active run: what works, what does not, and by how much.

    python -m backend.rdm.eval.evaluate_tools        → backend/rdm/eval/results/<run>.json

Checks (each prints a short line and goes into the JSON):
  1 bridge       Do the information tools point the same way as the surrogate? For every
                 (category, lever that reaches it): the runs' marginal effect (model_network v1, other levers
                 random) vs the surrogate's effect in an experiment (lever at 1 vs BAU, others at 0).
  2 payload      Reply size of every model_network call from a lever and from a category, per arm.
  3 coverage     Levers / uncertainties with no links; units known for the linked variables.
  4 stability    share_fail of one vulnerability check as the number of futures grows.
  5 timing       Seconds per technical tool call.
  6 costs        Signs of the surrogate's cost types at BAU and at full ambition.
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.harness.state import State
from backend.rdm.runs import get_run
from backend.rdm.surrogate import get_surrogate
from backend.rdm.tools import information as I
from backend.rdm.tools import technical as T

OUT_DIR = Path(__file__).parent / "results"
YEAR = 2050
GDP = 57


def bridge(run, store, sur) -> dict:
    rows = []
    n = 300
    u = np.random.default_rng(0).random((n, len(sur.x_ids)))
    futures = pd.DataFrame({f"X_{x}": u[:, i] for i, x in enumerate(sur.x_ids)})
    base = futures.assign(**{f"L_{l}": 0.0 for l in sur.lever_ids})
    bau = sur.predict(base)
    cache = {}
    for slug in sur.categories:
        o = I.model_network(run, f"emissions_{slug}", YEAR, "v1")
        col = f"emission_{slug}_yr{YEAR}"
        for d in o.get("lever_effects", []):
            lid = int(d["lever"][1:])
            if lid not in cache:
                cache[lid] = sur.predict(base.assign(**{f"L_{lid}": 1.0}))
            exp = float((cache[lid][col] - bau[col]).median())
            rows.append({"category": slug, "lever": lid, "runs_effect": d["change"], "surrogate_effect": exp})
    df = pd.DataFrame(rows)
    # Only pairs where at least one side is non-trivial (> 0.05 Mt) say anything about direction.
    big = df[(df.runs_effect.abs() > 0.05) | (df.surrogate_effect.abs() > 0.05)]
    agree = np.sign(big.runs_effect) == np.sign(big.surrogate_effect)
    per_cat = {}
    for slug, g in df.groupby("category"):
        if len(g) >= 3:
            per_cat[slug] = round(float(g.runs_effect.rank().corr(g.surrogate_effect.rank())), 2)
    worst = big[~agree].assign(gap=lambda d: (d.runs_effect - d.surrogate_effect).abs()).nlargest(8, "gap")
    ratio = (big.runs_effect / big.surrogate_effect).replace([np.inf, -np.inf], np.nan)
    return {
        "pairs": int(len(df)), "pairs_nontrivial": int(len(big)),
        "sign_agreement": round(float(agree.mean()), 3),
        "rank_correlation_by_category": per_cat,
        "median_ratio_runs_to_surrogate": round(float(ratio[agree].median()), 2),
        "largest_disagreements": worst[["category", "lever", "runs_effect", "surrogate_effect"]].round(3).to_dict("records"),
    }


def payload(run, store) -> dict:
    size = lambda r: len(json.dumps(r, ensure_ascii=False))
    out = {}
    for v in I.VERSIONS:
        lx = [size(I.model_network(run, f"L{l}", YEAR, v)) for l in sorted(I.groups(run))
              if I.groups(run)[l]["kind"] == "L"]
        ol = [size(I.model_network(run, f"emissions_{c}", YEAR, v)) for c in I.crosswalk(run)]
        out[v] = {"lever_node_chars": {"median": int(np.median(lx)), "max": int(max(lx))},
                  "category_node_chars": {"median": int(np.median(ol)), "max": int(max(ol))}}
    return out


def coverage(run) -> dict:
    m = I.links(run)
    g = I.groups(run)
    levers = [i for i, v in g.items() if v["kind"] == "L"]
    xs = [i for i, v in g.items() if v["kind"] == "X"]
    L = m[m.group_kind == "L"]
    no_link = sorted(set(levers) - set(L.group_id))
    no_emission = sorted(set(levers) - set(L[L.output_kind == "emission"].group_id))
    no_x = sorted(set(xs) - set(m[m.group_kind == "X"].group_id))
    var = m[m.output_kind == "variable"].output_field.unique()
    known = [f for f in var if I.unit(f) != "unknown"]
    return {"levers_without_links": no_link, "levers_without_emission_links": no_emission,
            "uncertainties_without_links": no_x,
            "linked_variables": int(len(var)), "variables_with_unit": int(len(known)),
            "unit_examples_missing": sorted(set(var) - set(known))[:8]}


def stability(sur) -> dict:
    out = {}
    pol = [{"name": "half", "levers": {i: 0.5 for i in sur.lever_ids}}]
    for n in (100, 200, 500, 1000, 2000, 5000):
        shares = []
        for seed in range(5):
            st = State()
            e = T.exploratory_modeling(st, sur, pol, n_futures=n, seed=seed, metrics=["emissions_total"], years=[YEAR])
            shares.append(T.vulnerability_analysis(st, sur, e["ensemble_id"], "half", "emissions_total", YEAR,
                                                   threshold=40, threshold_type="reduction_vs_bau_pct")["share_fail"])
        out[n] = {"mean": round(float(np.mean(shares)), 3), "sd_across_seeds": round(float(np.std(shares)), 3)}
    return out


def timing(sur) -> dict:
    st = State()
    pols = [{"name": f"p{k}", "levers": {i: (k + 1) / 4 for i in sur.lever_ids}} for k in range(3)]
    t = {}
    t0 = time.time(); e = T.exploratory_modeling(st, sur, pols, n_futures=500)["ensemble_id"]; t["exploratory_modeling_500x4"] = time.time() - t0
    t0 = time.time(); T.vulnerability_analysis(st, sur, e, "p1", "emissions_total", YEAR, threshold=40,
                                               threshold_type="reduction_vs_bau_pct"); t["vulnerability_analysis"] = time.time() - t0
    t0 = time.time(); T.scenario_discovery(st, sur, e); t["scenario_discovery"] = time.time() - t0
    t0 = time.time(); T.trade_off_analysis(st, sur, e, YEAR); t["trade_off_analysis"] = time.time() - t0
    return {k: round(v, 2) for k, v in t.items()}


def costs(sur) -> dict:
    u = np.random.default_rng(1).random((500, len(sur.x_ids)))
    fut = pd.DataFrame({f"X_{x}": u[:, i] for i, x in enumerate(sur.x_ids)})
    out = {}
    for level in (0.0, 1.0):
        p = sur.predict(fut.assign(**{f"L_{l}": level for l in sur.lever_ids}))
        out[f"levers_at_{level}"] = {c: round(float(p[f"cost_{c}_yr{YEAR}"].median()), 2) for c in sur.cost_types}
        out[f"levers_at_{level}"]["cost_total (sign-flipped sum)"] = round(float(p[f"cost_total_yr{YEAR}"].median()), 2)
    return out


def main():
    run = get_run()
    store, sur = Store(run), get_surrogate(run)
    res = {"run": run.name, "year": YEAR}
    for name, fn in (("coverage", lambda: coverage(run)), ("costs", lambda: costs(sur)), ("timing", lambda: timing(sur)),
                     ("payload", lambda: payload(run, store)), ("bridge", lambda: bridge(run, store, sur)),
                     ("stability", lambda: stability(sur))):
        t0 = time.time()
        res[name] = fn()
        print(f"[{name}] {time.time() - t0:.1f}s  {json.dumps(res[name], default=str)[:400]}")
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{run.name}.json"
    path.write_text(json.dumps(res, indent=1, default=str))
    print("saved", path)


if __name__ == "__main__":
    main()
