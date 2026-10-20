"""
Information tools: read the runs. Relations in both versions; values only in v1.

  lever_x_profile  one profile per pair (L_i, X_j): the variables and emissions the lever moves,
                   and how they look across X_j
  output_levers    the reverse look-up: which levers and uncertainties move an output

What each version returns (design: docs/rdm_tools_design.md, "v0 and v1"):
  v0  relations — which L and X move which variables and emissions, the year each link is
      strongest, emission → inventory category. Lists are alphabetical, never ranked.
  v1  the same relations + how much — values (median, p10–p90) across lever levels and X bins,
      direction and strength (Spearman ρ), units; lists ranked by strength.

Only the 505 emission fields in the crosswalk are reported (they are the ones the surrogate
sums into its 23 categories). Links the structural map lists but whose output never moves in
the runs ("structural, output constant in runs") are left out.

Values are marginal: every other lever and uncertainty keeps varying across the sampled runs,
so a value is "what the output looks like when this lever is at this level", averaged over
everything else — not the lever's effect with every other lever at 0.
"""

import json
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.mapping.build_mapping import MAPS_DIR
from backend.rdm.runs import Run
from backend.rdm.tools.common import ToolError, group_id, groups

# Arms of the experiment: (show input values, show output values). v0 = relations only, always.
ARMS = {"v0": (False, False), "v1": (True, True), "v1_inputs": (True, False), "v1_outputs": (False, True)}
VERSIONS = tuple(ARMS)
L_BINS = 5
X_LOW, X_HIGH = (0.0, 1 / 3), (2 / 3, 1.0)
EXCLUDED_STATUS = "structural, output constant in runs"
MAX_VARIABLES = 30


# ── data the tools read ──────────────────────────────────────────────────────

@lru_cache(maxsize=2)
def crosswalk(run: Run) -> dict:
    """category slug → {"display": …, "fields": [...]}"""
    return {k: {"display": v["display"], "fields": list(v["fields"])}
            for k, v in json.loads(run.crosswalk.read_text()).items()}


@lru_cache(maxsize=2)
def category_of(run: Run) -> dict:
    return {f: c for c, v in crosswalk(run).items() for f in v["fields"]}


@lru_cache(maxsize=2)
def links(run: Run) -> pd.DataFrame:
    """The mapping, limited to what the tools report: variables, and emissions in the crosswalk."""
    m = pd.read_csv(MAPS_DIR / f"{run.name}.csv")
    m = m[m.status != EXCLUDED_STATUS]
    cat = category_of(run)
    keep = (m.output_kind == "variable") | m.output_field.isin(cat)
    m = m[keep].copy()
    m["category"] = m.output_field.map(cat)
    return m


_UNIT_TOKENS = [("vehicle_distance_traveled", "vehicle-km"), ("_mmm_usd", "billion USD"), ("_tonne", "tonne"), ("_pj", "PJ"), ("_ha", "ha"), ("_m3", "m³"),
                ("_mtkm", "million tonne-km"), ("_mpkm", "million passenger-km"), ("_km", "km")]


def unit(field: str) -> str:
    """Unit of an output, read from its field name (v1 only). 'unknown' until the units table exists."""
    if field.startswith("emission_co2e"):
        return "Mt CO₂e"
    if field.startswith("frac_"):
        return "fraction (0–1)"
    if field.startswith("area_"):
        return "ha"
    for tok, u in _UNIT_TOKENS:
        if tok in field:
            return u
    return "unknown"


def _sig(x, n: int = 4):
    """Round to n significant figures (outputs range from 1e-6 Mt to 1e9 tonnes)."""
    if x is None or pd.isna(x):
        return None
    x = float(x)
    return 0.0 if x == 0 else float(f"{x:.{n}g}")


def _arm(version: str) -> tuple:
    if version not in ARMS:
        raise ToolError("BAD_ARM", f"arm must be one of {VERSIONS}")
    return ARMS[version]


def _check_version(version: str):
    _arm(version)


def _check_year(run: Run, year) -> int:
    y = int(year)
    if y not in run.years:
        raise ToolError("BAD_YEAR", f"Year {y} not available; use one of {list(run.years)}")
    return y


def _series_with(store: Store, series: pd.Series, gids: list) -> pd.DataFrame:
    cols = [f"{groups(store.run)[g]['kind']}_{g}" for g in gids]
    return store.design.loc[series.index, cols].join(series.rename("value"))


def _bin_mask(v: pd.Series, lo: float, hi: float) -> pd.Series:
    return (v >= lo) & ((v < hi) if hi < 1 else (v <= hi))


# ── lever_x_profile ──────────────────────────────────────────────────────────

def _inputs_table(run: Run) -> pd.DataFrame:
    from backend.rdm.data.lever_inputs import TABLES
    path = TABLES / f"{run.name}_lever_inputs.csv"
    if not path.exists():
        raise FileNotFoundError(f"No lever input table {path.name}; run python -m backend.rdm.data.lever_inputs")
    return pd.read_csv(path)


_TABLE_CACHE: dict = {}


def _tables(run: Run) -> tuple:
    if run.name not in _TABLE_CACHE:
        from backend.rdm.data import values
        _TABLE_CACHE[run.name] = (_inputs_table(run), values.load(run), values.lever_outputs(run))
    return _TABLE_CACHE[run.name]


def _cell_values(t: pd.DataFrame, unit_: str) -> dict:
    """Compact values of one output: medians by lever level, the high-level range, and low vs high X."""
    a = t[t.x_bin == "any"].set_index("lever_level")
    lo_x = t[t.x_bin == "low"].set_index("lever_level")
    hi_x = t[t.x_bin == "high"].set_index("lever_level")
    return {
        "unit": unit_,
        "median_by_lever_level": {lv: _sig(a.loc[lv, "median"]) for lv in ("low", "mid", "high")},
        "p10_p90_at_high_level": [_sig(a.loc["high", "p10"]), _sig(a.loc["high", "p90"])],
        "uncertainty_low": {"lever_low": _sig(lo_x.loc["low", "median"]), "lever_high": _sig(lo_x.loc["high", "median"])},
        "uncertainty_high": {"lever_low": _sig(hi_x.loc["low", "median"]), "lever_high": _sig(hi_x.loc["high", "median"])},
    }


def lever_x_profile(run: Run, store: Store, lever, x, year, version: str = "v1") -> dict:
    """The chain lever → inputs it sets → in-between variables → emission categories, for one
    uncertainty. Relations in every arm; input values and output values only in the arms that show them."""
    show_inputs, show_outputs = _arm(version)
    lid, xid = group_id(run, lever, "L"), group_id(run, x, "X")
    y = _check_year(run, year)
    g = groups(run)
    inputs, vals, cover = _tables(run)
    m = links(run)
    lv = m[(m.group_kind == "L") & (m.group_id == lid)]
    x_moves = set(m[(m.group_kind == "X") & (m.group_id == xid)].output_field)
    cw = crosswalk(run)

    out = {"arm": version,
           "lever": {"id": lid, "name": g[lid]["name"], "sector": g[lid]["sector"]},
           "uncertainty": {"id": xid, "name": g[xid]["name"]}, "year": y}

    # 1 · Inputs the lever sets (what a level means in real terms)
    inp = inputs[(inputs.lever_id == lid) & inputs.changes]
    rows = []
    for field, gi in inp.groupby("field", sort=True):
        d = {"field": field, "description": gi.variable.iloc[0]}
        if show_inputs:
            # The range the lever moves this quantity in the experiment's runs, measured from BAU (P13): the
            # bottom of the lever's explored range is BAU, the top is the most ambitious level the runs reached;
            # in between the value is linear in the lever level.
            d["unit"] = gi.unit.iloc[0]
            d["range_from_bau"] = {str(r.year): {f"bau (lever {r.level_low:g})": _sig(r.at_0),
                                                 f"lever {(r.level_low + r.level_high) / 2:g}": _sig(r["at_0.5"]),
                                                 f"top of the range run (lever {r.level_high:g})": _sig(r.at_1),
                                                 "direction": "up" if r.at_1 > r.at_0 else "down"}
                                   for _, r in gi.iterrows()}
        rows.append(d)
    out["inputs"] = rows

    # 2 · Emission categories the lever moves, with the fields under each (the crosswalk, in every arm)
    cv = cover.get(lid, {"categories": [], "variables": []})
    vt = vals[(vals.lever_id == lid) & (vals.year == y) & vals.x_id.isin([0, xid])]
    em = lv[lv.output_kind == "emission"]
    cats = []
    for slug in cv["categories"]:
        e = em[em.category == slug]
        d = {"category": cw[slug]["display"], "metric": f"emissions_{slug}",
             "fields_the_lever_moves": sorted(e.output_field),
             "uncertainty_also_moves": bool(set(cw[slug]["fields"]) & x_moves),
             "strongest_year": None if e.rho_year.isna().all() else int(e.loc[e.rho_max_abs.abs().idxmax(), "rho_year"])}
        if show_outputs:
            d["values"] = _cell_values(vt[(vt.kind == "category") & (vt.output == slug)], "Mt CO₂e (whole category)")
        cats.append(d)
    out["emission_categories"] = cats

    # 3 · In-between variables: moved by the lever and linked to one of its categories
    var_links = _var_categories(run)
    vars_ = []
    for f in cv["variables"]:
        r = lv[lv.output_field == f].iloc[0]
        feeds = sorted(cw[c]["display"] for c in var_links.get(f, set()) if c in cv["categories"])
        d = {"field": f,
             "why_shown": " and ".join(w for w, ok in (("drives an emission category", bool(feeds)),
                                                       ("moves most with this lever", f in cv.get("channel", [])))
                                       if ok),
             "feeds": feeds,
             "uncertainty_also_moves": f in x_moves,
             "strongest_year": None if pd.isna(r.rho_year) else int(r.rho_year)}
        if show_outputs:
            d["values"] = _cell_values(vt[(vt.kind == "variable") & (vt.output == f)], unit(f))
        vars_.append(d)
    out["in_between_variables"] = vars_

    if not (rows or cats or vars_):
        out["note"] = "No links recorded for this lever (the mapping is incomplete for it)."
    else:
        out["note"] = ("Chain: inputs the lever sets → in-between variables → emission categories (the metrics "
                       "exploratory_modeling reports). " +
                       ("Values are medians over the model runs with every other lever and uncertainty varying; "
                        "lever level low/mid/high = 0–⅓/⅓–⅔/⅔–1; uncertainty low/high = bottom/top third of its range."
                        if show_outputs or show_inputs else "Relations only."))
    return out


@lru_cache(maxsize=2)
def _var_categories(run: Run) -> dict:
    from backend.rdm.data.values import driver_categories
    return driver_categories(run)


# ── output_levers ────────────────────────────────────────────────────────────

def _resolve_output(run: Run, store: Store, output: str) -> tuple:
    """(kind, label, fields) for a category slug or display name, an emission field, or a variable."""
    key = str(output).strip()
    if key.startswith("emissions_"):          # the metric name the technical tools use
        key = key[len("emissions_"):]
    cw = crosswalk(run)
    for slug, c in cw.items():
        if key.lower() in (slug, c["display"].lower()):
            return "category", c["display"], c["fields"]
    if key in category_of(run):
        return "emission", key, [key]
    if key in store.variable_fields:
        return "variable", key, [key]
    if key.startswith("emission_co2e"):
        raise ToolError("FIELD_NOT_IN_SURROGATE", f"{key} is not one of the 505 emission fields the surrogate uses")
    raise ToolError("UNKNOWN_OUTPUT", f"Unknown output {key!r}. Give one of the 23 categories "
                    f"({', '.join(sorted(cw))}), an emission field or a variable field.")


def output_levers(run: Run, store: Store, output: str, year, version: str = "v1") -> dict:
    _check_version(version)
    y = _check_year(run, year)
    kind, label, fields = _resolve_output(run, store, output)
    g = groups(run)
    m = links(run)
    lk = m[m.output_field.isin(fields)]
    out = {"version": version, "output": label, "kind": kind, "year": y}
    if kind == "category":
        out["fields_in_category"] = sorted(fields)

    by_group = lk.groupby(["group_kind", "group_id"]).output_field.nunique()
    def rel(kind_, gid, n):
        d = {"id": int(gid), "name": g[int(gid)]["name"]}
        if kind_ == "L":
            d["sector"] = g[int(gid)]["sector"]
        if kind == "category":
            d["moves_fields"] = int(n)
        return d

    levers = [rel("L", gid, n) for (k, gid), n in by_group.items() if k == "L"]
    uncs = [rel("X", gid, n) for (k, gid), n in by_group.items() if k == "X"]
    if not _arm(version)[1]:
        out["levers"] = sorted(levers, key=lambda d: d["id"])
        out["uncertainties"] = sorted(uncs, key=lambda d: d["id"])
        out["note"] = "Relations only, in id order: which levers and uncertainties move this output."
        return out

    series = store.total(fields, y) if kind != "variable" else store.values(fields[0], y)
    u = "Mt CO₂e" if kind != "variable" else unit(fields[0])

    def effect(d: dict) -> dict:
        df = _series_with(store, series, [d["id"]])
        v = df.iloc[:, 0]
        low, high = df.value[_bin_mask(v, 0, 0.2)], df.value[_bin_mask(v, 0.8, 1)]
        rho = df.iloc[:, 0].rank().corr(df.value.rank())
        return {**d,
                "median_at_low_end": _sig(low.median()), "median_at_high_end": _sig(high.median()),
                "effect_low_to_high": _sig(high.median() - low.median()),
                "p10_p90_at_high_end": [_sig(high.quantile(.1)), _sig(high.quantile(.9))],
                "correlation": _sig(rho, 2)}

    out["unit"] = u
    out["levers"] = sorted((effect(d) for d in levers), key=lambda d: -abs(d["effect_low_to_high"] or 0))
    out["uncertainties"] = sorted((effect(d) for d in uncs), key=lambda d: -abs(d["effect_low_to_high"] or 0))
    out["note"] = ("Ranked by effect: median of the output with the group in the top fifth of its range minus the "
                   "median in the bottom fifth, every other input varying. Low end = 0–0.2, high end = 0.8–1.")
    return out
