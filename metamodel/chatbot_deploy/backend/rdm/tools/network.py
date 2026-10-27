"""
model_network: the agent navigates the SISEPUEDE network one node at a time.

The network (docs/rdm_network_plan.md) was read from the SISEPUEDE code: a link means "used to compute", with
levers and uncertainties setting input variables, in-between variables computed from them, emission variables,
and the 23 XGBoost categories they sum into. NemoMod (electricity) is one box. The tool reads the files built in
backend/rdm/network/out/ and never computes anything new.

Every reply gives the node, its attributes, what it is computed from (one step back) and what it is used to
compute (one step forward); any name listed can be asked next. In the arms that show values it adds, from the
experiment's runs: the values of the node's fields (median, p10–p90, in their units) for the year asked, split by
a lever's thirds if a lever is given, within one uncertainty's third if one is given.

  v0   relations only: nodes, attributes, links
  v1   + what a lever sets (its inputs at BAU, middle and top of the range run) and the values of the variables,
       emissions and categories (v1_inputs / v1_outputs, one half each, were dropped 2026-10-26)
"""

import difflib
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.rdm.runs import Run
from backend.rdm.surrogate import UNITS
from backend.rdm.tools.common import ToolError, groups

# SISEPUEDE labels GDP "billion USD"; the project labels it as the other tools do (decision D4, 2026-10-13)
ATTRIBUTE_OVERRIDES = {"GDP": {"units": UNITS["gdp"], "information": f"GDP in {UNITS['gdp']}"}}

NET = Path(__file__).parents[1] / "network" / "out"
INPUTS = Path(__file__).parents[1] / "data" / "tables"
ARMS = {"v0": (False, False), "v1": (True, True)}
VERSIONS = tuple(ARMS)
THIRDS = {"low": "0–⅓", "mid": "⅓–⅔", "high": "⅔–1"}
NEMOMOD = "NemoMod (electricity optimisation)"
MAX_LIST = 60          # neighbours listed per direction; the count of the rest is given
MAX_FIELDS = 20        # fields of one variable shown with values


def _sig(x, n=4):
    return None if x is None or pd.isna(x) else (0.0 if float(x) == 0 else float(f"{float(x):.{n}g}"))


class Network:
    """The network files of one run, loaded once."""

    def __init__(self, run: Run):
        p = lambda s: NET / f"{run.name}_{s}"
        self.run = run
        e = pd.read_csv(p("edges.csv"))
        self.edges = e
        self.attrs = pd.read_csv(p("node_attributes.csv")).set_index("variable")
        f = pd.read_csv(p("field_attributes.csv"))
        self.fields = f.groupby("variable")
        self.field_var = dict(zip(f.field, f.variable))
        self.field_row = f.set_index("field")
        self.g = groups(run)
        self.out = e.groupby("source").target.apply(list).to_dict()
        self.inn = e.groupby("target").source.apply(list).to_dict()
        nodes = pd.read_csv(p("nodes.csv")).set_index("id")
        self.kind = {}
        for n, r in nodes.iterrows():
            self.kind[n] = ("lever" if r.kind == "lever" else "uncertainty" if r.kind == "uncertainty" else
                            "category" if str(n).startswith("C:") else
                            "emission" if r.get("is_emission") is True else
                            "in-between" if r.kind == "output" else str(r.kind))
        self.kind[NEMOMOD] = "box"
        self.cat_name = {n: nodes.loc[n, "information"] for n in nodes.index if str(n).startswith("C:")}
        # names the agent may use for a node: SISEPUEDE's name, the readable name, a category's metric or display name
        self.name = {n: (self.attrs.loc[n, "name"] if n in self.attrs.index else self.cat_name.get(n, n))
                     for n in self.kind}
        self.lookup = {}
        for n, nm in self.name.items():
            self.lookup[str(n).lower()] = n
            self.lookup[str(nm).lower()] = n
        for n in self.cat_name:
            slug = n[2:]
            self.lookup[slug] = self.lookup[f"emissions_{slug}"] = n
        li = pd.read_csv(INPUTS / f"{run.name}_lever_inputs.csv")
        self.lever_inputs = li[li.changes]

    # ── resolving what the agent asked for ─────────────────────────────────
    def resolve(self, node) -> tuple:
        """(node id, field or None)."""
        key = str(node).strip()
        m = re.match(r"^(?:(lever|l|uncertainty|x)\s*)?(\d+)$", key, re.I)
        if m:
            gid = int(m.group(2))
            if gid not in self.g:
                raise ToolError("BAD_ID", f"{gid} is not a lever or uncertainty id")
            want = (m.group(1) or "").lower()
            k = self.g[gid]["kind"]
            if (want in ("lever", "l") and k != "L") or (want in ("uncertainty", "x") and k != "X"):
                raise ToolError("X_AS_LEVER" if k == "X" else "LEVER_AS_X",
                                f"{gid} is {'an uncertainty' if k == 'X' else 'a lever'} id")
            return f"{k}{gid}", None
        low = key.lower()
        if low in self.lookup:
            return self.lookup[low], None
        if key in self.field_var and self.field_var[key] in self.kind:
            return self.field_var[key], key
        close = difflib.get_close_matches(low, list(self.lookup), n=5, cutoff=0.6)
        raise ToolError("UNKNOWN_NODE", f"No node {key!r} in the network." +
                        (f" Close names: {', '.join(self.name[self.lookup[c]] for c in close)}." if close else
                         " Give a lever or uncertainty id, a category metric (emissions_<category>), or a variable "
                         "name as listed in another reply."))

    # ── pieces of a reply ────────────────────────────────────────────────
    def brief(self, n) -> dict:
        k = self.kind.get(n, "variable")
        if k in ("lever", "uncertainty"):
            gid = int(n[1:])
            return {"node": f"{n[0]}{gid}", "kind": k, "name": self.g[gid]["name"]}
        d = {"node": self.name[n], "kind": k}
        if n in self.attrs.index and pd.notna(self.attrs.loc[n, "subsector"]):
            d["subsector"] = self.attrs.loc[n, "subsector"]
        return d

    def neighbours(self, ids: list) -> dict:
        ids = sorted(set(ids), key=lambda n: (self.kind.get(n, ""), str(self.name.get(n, n))))
        out = {"count": len(ids), "nodes": [self.brief(n) for n in ids[:MAX_LIST]]}
        if len(ids) > MAX_LIST:
            out["more"] = f"{len(ids) - MAX_LIST} more not listed"
        return out

    def attributes(self, n) -> dict:
        k = self.kind.get(n, "variable")
        if k in ("lever", "uncertainty"):
            gid = int(n[1:])
            return {"node": f"{n[0]}{gid}", "kind": k, "name": self.g[gid]["name"], "sector": self.g[gid]["sector"]}
        if k == "category":
            return {"node": self.name[n], "kind": k, "metric": f"emissions_{n[2:]}", "unit": "Mt CO₂e",
                    "note": "the sum of its emission fields; exploratory_modeling reports this metric"}
        if k == "box":
            return {"node": NEMOMOD, "kind": k, "note": "SISEPUEDE's electricity optimisation, one box: what goes in "
                    "and what comes out are known, not the steps inside"}
        a = self.attrs.loc[n] if n in self.attrs.index else None
        d = {"node": self.name[n], "kind": k, "sisepuede_variable": n}
        if a is not None:
            for key in ("type", "sector", "subsector", "gas", "units", "xgboost_categories", "information"):
                v = a[key]
                if pd.notna(v) and v != "":
                    d[key] = v
        d.update(ATTRIBUTE_OVERRIDES.get(n, {}))
        return d

    def field_list(self, n) -> list:
        if self.kind.get(n) == "category":
            return [f"emissions_{n[2:]}"]
        return list(self.fields.get_group(n).field) if n in self.fields.groups else []

    def reached(self, start) -> set:
        seen, stack = {start}, [start]
        while stack:
            for t in self.out.get(stack.pop(), []):
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
        return seen - {start}

    def reaching(self, end) -> set:
        seen, stack = {end}, [end]
        while stack:
            for s in self.inn.get(stack.pop(), []):
                if s not in seen:
                    seen.add(s)
                    stack.append(s)
        return seen - {end}


@lru_cache(maxsize=2)
def network(run: Run) -> Network:
    return Network(run)


@lru_cache(maxsize=8)
def ranges(run: Run, year: int) -> pd.DataFrame:
    r = pd.read_parquet(NET / f"{run.name}_ranges.parquet", filters=[("year", "==", year)])
    r["field"] = r.field.astype(str)
    r["x_bin"] = r.x_bin.astype(str)
    r["lever_level"] = r.lever_level.astype(str)
    return r.set_index(["lever_id", "x_id", "x_bin", "field"]).sort_index()


def _cell(r: pd.DataFrame, lid: int, xid: int, xb: str, field: str) -> dict:
    try:
        g = r.loc[(lid, xid, xb, field)]
    except KeyError:
        return {}
    g = g if isinstance(g, pd.DataFrame) else g.to_frame().T
    return {lv: {"median": _sig(row["median"]), "p10_p90": [_sig(row.p10), _sig(row.p90)], "runs": int(row.n)}
            for lv, row in g.set_index("lever_level").iterrows() if row.n > 0}


def model_network(run: Run, node, year, version: str = "v1", lever=None, uncertainty=None, third=None) -> dict:
    if version not in ARMS:
        raise ToolError("BAD_ARM", f"arm must be one of {VERSIONS}")
    show_inputs, show_values = ARMS[version]
    y = int(year)
    if y not in run.years:
        raise ToolError("BAD_YEAR", f"Year {y} not available; use one of {list(run.years)}")
    net = network(run)
    n, field = net.resolve(node)
    k = net.kind.get(n, "variable")

    lid = xid = None
    if lever is not None:
        lnode, _ = net.resolve(f"lever {lever}")
        lid = int(lnode[1:])
    third_ignored = lever is not None and uncertainty is None and third is not None
    if uncertainty is not None or (third is not None and not third_ignored):
        if uncertainty is None or third not in THIRDS:
            raise ToolError("BAD_FILTER", "Give both uncertainty (an id) and third (low, mid or high).")
        xnode, _ = net.resolve(f"uncertainty {uncertainty}")
        xid = int(xnode[1:])

    out = {"arm": version, "year": y, **net.attributes(n)}
    if third_ignored:
        out["filter_note"] = ("third filters an uncertainty; with a lever alone, the node is shown for each of the "
                              "lever's thirds (low, mid, high)")
    if field:
        out["field_asked"] = field
    if k in ("lever", "uncertainty"):
        sets = sorted(t for t in net.out.get(n, []))
        out["sets"] = net.neighbours(sets)
        down = net.reached(n)
        cats = sorted(f"emissions_{c[2:]}" for c in down if c.startswith("C:"))
        out["reaches"] = {"variables": len([d for d in down if net.kind.get(d) not in ("category", "box")]),
                          "emission_categories": cats}
        if not down - set(sets):
            out["note"] = ("Its inputs are not used to compute anything in the traced run of the model code (a gap "
                           "of the network), so no chain is known for it.")
        if k == "lever" and show_inputs:
            li = net.lever_inputs[(net.lever_inputs.lever_id == int(n[1:]))]
            yy = y if y in set(li.year) else max(li.year) if len(li) else None
            out["input_values"] = {
                "year": yy, "note": ("what the lever level means: the input at BAU (bottom of the range run), the "
                                     "middle and the top of the range run, a straight line in between" +
                                     ("" if yy == y else f"; given for {yy}, the nearest year computed")),
                "fields": [{"field": r.field, "unit": r.unit,
                            "bau": _sig(r.at_0), "middle": _sig(r["at_0.5"]), "top_of_range": _sig(r.at_1)}
                           for _, r in li[li.year == yy].iterrows()]} if yy else None
        if k == "lever" and show_values and cats:
            r = ranges(run, y)
            out["category_values"] = {c: (_cell(r, int(n[1:]), xid, third, c) if xid else {}) or
                                         _cell(r, int(n[1:]), 0, "any", c) for c in cats}
            out["values_note"] = _values_note(xid, third, int(n[1:]), net)
        return out

    out["computed_from"] = net.neighbours(net.inn.get(n, []))
    out["used_to_compute"] = net.neighbours(net.out.get(n, []))
    up = net.reaching(n)
    out["levers_that_reach_it"] = sorted((f"L{u[1:]}" for u in up if net.kind.get(u) == "lever"), key=lambda s: int(s[1:]))
    out["uncertainties_that_reach_it"] = sorted((f"X{u[1:]}" for u in up if net.kind.get(u) == "uncertainty"),
                                                key=lambda s: int(s[1:]))
    if k == "box":
        return out

    flds = [field] if field else net.field_list(n)
    if not show_values:
        out["fields"] = [_field_info(net, f) for f in flds[:MAX_FIELDS]]
    else:
        r = ranges(run, y)
        use_l = lid if lid is not None and f"L{lid}" in up else 0
        use_x = xid if xid is not None and f"X{xid}" in up else 0
        rows = []
        for f in flds[:MAX_FIELDS]:
            d = _field_info(net, f)
            d["values"] = _cell(r, use_l, use_x, third if use_x else "any", f) or "no values in the runs for this year"
            rows.append(d)
        out["fields"] = rows
        notes = []
        if lid is not None and use_l == 0:
            notes.append(f"L{lid} does not reach this variable: values over every lever level")
        if xid is not None and use_x == 0:
            notes.append(f"X{xid} does not reach this variable: values over all futures")
        out["values_note"] = "; ".join(notes + [_values_note(use_x and xid, third, use_l, net)])
        if k == "category" and lid is None:
            out["lever_effects"] = _effects(r, net, up, f"emissions_{n[2:]}", xid if use_x else 0, third)
    if len(flds) > MAX_FIELDS:
        out["more_fields"] = f"{len(flds) - MAX_FIELDS} more fields; ask for one by its field name"
    return out


def _field_info(net: Network, f: str) -> dict:
    if f.startswith("emissions_") and f not in net.field_row.index:
        return {"field": f, "unit": "Mt CO₂e"}
    r = net.field_row.loc[f]
    d = {"field": f, "unit": r.unit}
    if pd.notna(r.category):
        d["category"] = r.category
    if pd.notna(r.xgboost_category):
        d["xgboost_category"] = r.xgboost_category
    return d


def _values_note(xid, third, lid, net) -> str:
    who = f"split by L{lid}'s level: low 0–⅓, mid ⅓–⅔, high ⅔–1 of its range" if lid else "over every run"
    where = f", only futures with X{xid} ({net.g[xid]['name']}) in its {third} third ({THIRDS[third]})" if xid else ""
    return (f"Median and p10–p90 over the experiment's runs {who}{where}; every other lever and uncertainty "
            "varies. Values from the model runs, not the surrogate.")


def _effects(r, net, up, field, xid, third) -> list:
    """For a category: each lever that reaches it, the median at the lever's top third minus the bottom third."""
    out = []
    for u in up:
        if net.kind.get(u) != "lever":
            continue
        c = _cell(r, int(u[1:]), xid, third if xid else "any", field)
        if "low" in c and "high" in c:
            out.append({"lever": f"L{u[1:]}", "name": net.g[int(u[1:])]["name"],
                        "median_low_third": c["low"]["median"], "median_high_third": c["high"]["median"],
                        "change": _sig(c["high"]["median"] - c["low"]["median"])})
    return sorted(out, key=lambda d: -abs(d["change"] or 0))
