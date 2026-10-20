"""
The in-between variables that create each surrogate emission category, for expert review.

Decided 2026-10-13. For every emission **source** — an emission field without its gas, e.g.
CH₄ and N₂O from `lvst_entferm_cattle_dairy` are one source — inside each of the 23 categories the
XGBoost predicts, keep the variable(s) that create its value, judged at the **last run year**:

  0. A source that never varies across the runs needs no driver ("constant").
  1. **Exact name** — a variable whose name contains the whole source name (`from_` ignored), e.g.
     `area_lndu_conversion_from_forests_primary_to_croplands` for `lndu_conversion_forests_primary_to_croplands`.
     Up to 2, the strongest first.
  2. **Group** — when the source adds up a dimension its variables split (the source names no fuel;
     `energy_consumption_trns_road_light_<fuel>` does), keep the whole group: the exact-name family whose
     members move most with the source.
  3. **Correlation** — otherwise, the 1–2 candidates from the subsector rule (subsector.py) that move most
     with the source across the runs (|Spearman ρ|), flagged weak below 0.3.
Variables are then listed once per category (a variable may still feed two categories).

    python -m backend.rdm.links.drivers
writes
    backend/rdm/links/<run>_drivers_by_source.csv     one row per (category, source): the choice and why
    backend/rdm/links/<run>_drivers_by_category.csv   one row per (category, variable): the review file
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.runs import Run
from backend.rdm.tools import information as I

OUT_DIR = Path(__file__).parent
GAS = re.compile(r"^emission_co2e_[a-z0-9]+_")
WEAK = 0.3
MAX_PER_SOURCE = 2


def source_of(field: str) -> str:
    return GAS.sub("", field)


def _norm(var: str) -> str:
    return var.replace("_from_", "_")


def _rho(a: pd.Series, b: pd.Series) -> float:
    idx = a.index.intersection(b.index)
    x, y = a.loc[idx], b.loc[idx]
    if len(idx) < 30 or x.std() == 0 or y.std() == 0:
        return np.nan
    return abs(float(x.rank().corr(y.rank())))


def choose(source: str, e: pd.Series, variables: pd.DataFrame, candidates: list) -> tuple:
    """(rule, [(variable, strength)…]) for one source."""
    # 1 · exact name: the whole source name inside the variable name
    exact = [v for v in variables.columns if source in _norm(v) and variables[v].std() > 0]
    if exact:
        single = [v for v in exact if _norm(v).endswith(source)]
        families = {}
        for v in exact:
            n = _norm(v)
            key = n[: n.index(source) + len(source)]
            if not n.endswith(source):
                families.setdefault(key, []).append(v)
        if single:
            ranked = sorted(((v, _rho(e, variables[v])) for v in single), key=lambda t: -np.nan_to_num(t[1]))
            return "exact name", ranked[:MAX_PER_SOURCE]
        # 2 · group: the source sums a dimension the variables split
        groups = {k: m for k, m in families.items() if len(m) >= 2}
        if groups:
            score = {k: np.nanmean([_rho(e, variables[v]) for v in m]) for k, m in groups.items()}
            best = max(score, key=lambda k: np.nan_to_num(score[k]))
            return "group", [(v, _rho(e, variables[v])) for v in sorted(groups[best])]
        ranked = sorted(((v, _rho(e, variables[v])) for v in exact), key=lambda t: -np.nan_to_num(t[1]))
        return "exact name", ranked[:MAX_PER_SOURCE]
    # 3 · correlation among the subsector-rule candidates
    ranked = [(v, _rho(e, variables[v])) for v in candidates if v in variables and variables[v].std() > 0]
    ranked = sorted((t for t in ranked if not np.isnan(t[1])), key=lambda t: -t[1])
    if not ranked:
        return "no candidate", []
    keep = ranked[:MAX_PER_SOURCE]
    return ("correlation" if keep[0][1] >= WEAK else "correlation (weak)"), keep


def build(run: Run, store: Store, year: int | None = None) -> tuple:
    year = year or max(run.years)
    cat, cw = I.category_of(run), I.crosswalk(run)
    em = store._emissions.xs(year, level="year")
    va = store._variables.xs(year, level="year")
    sub_links = pd.read_csv(OUT_DIR / f"{run.name}_variable_emission_links.csv")
    cand = sub_links.groupby("emission_field").variable_field.apply(list).to_dict()

    rows = []
    groups = pd.DataFrame({"field": list(cat)}).assign(category=lambda d: d.field.map(cat),
                                                       source=lambda d: d.field.map(source_of))
    for (slug, source), g in groups.groupby(["category", "source"]):
        fields = sorted(g.field)
        e = em[fields].sum(axis=1, min_count=1).dropna()
        base = {"category": cw[slug]["display"], "metric": f"emissions_{slug}", "source": source,
                "n_fields": len(fields), "fields": " | ".join(fields)}
        if e.empty or e.std() == 0:
            rows.append({**base, "rule": "constant in runs", "variables": "", "strength": ""})
            continue
        candidates = sorted({v for f in fields for v in cand.get(f, [])})
        rule, chosen = choose(source, e, va, candidates)
        rows.append({**base, "rule": rule, "variables": " | ".join(v for v, _ in chosen),
                     "strength": " | ".join("" if np.isnan(s) else f"{s:.2f}" for _, s in chosen)})
    by_source = pd.DataFrame(rows)
    by_source.insert(len(by_source.columns), "expert_ok", "")
    by_source.insert(len(by_source.columns), "expert_note", "")

    long = []
    for r in by_source[by_source.variables != ""].itertuples():
        for v, s in zip(r.variables.split(" | "), r.strength.split(" | ")):
            long.append({"category": r.category, "metric": r.metric, "variable": v, "source": r.source,
                         "rule": r.rule, "strength": float(s) if s else np.nan})
    long = pd.DataFrame(long)
    by_cat = (long.groupby(["category", "metric", "variable"])
              .agg(sources=("source", lambda s: " | ".join(sorted(set(s)))), n_sources=("source", "nunique"),
                   rules=("rule", lambda s: " | ".join(sorted(set(s)))), strength_max=("strength", "max"))
              .reset_index())
    by_cat["also_in_categories"] = by_cat.variable.map(
        lambda v: " | ".join(sorted(set(by_cat[by_cat.variable == v].category))))
    by_cat["also_in_categories"] = [" | ".join(c for c in a.split(" | ") if c != cat_)
                                    for a, cat_ in zip(by_cat.also_in_categories, by_cat.category)]
    by_cat["expert_ok"] = ""
    by_cat["expert_note"] = ""
    return by_source, by_cat


def write(run: Run, store: Store) -> dict:
    by_source, by_cat = build(run, store)
    by_source.to_csv(OUT_DIR / f"{run.name}_drivers_by_source.csv", index=False)
    by_cat.to_csv(OUT_DIR / f"{run.name}_drivers_by_category.csv", index=False)
    return {"sources": len(by_source), "rules": by_source.rule.value_counts().to_dict(),
            "category_rows": len(by_cat), "variables": by_cat.variable.nunique(),
            "in_more_than_one_category": int((by_cat.groupby("variable").category.nunique() > 1).sum())}


if __name__ == "__main__":
    from backend.rdm.runs import get_run
    r = get_run()
    print(write(r, Store(r)))
