"""
Steps 4–5 · assemble the network and test it against the runs.

Nodes: levers (L<id>), uncertainties (X<id>), SISEPUEDE model variables, and the 23 XGBoost categories (C:<slug>).
Edges:
  sets       L/X → input variable     the run's VARIABLE_TRAJECTORY_GROUPS_L / _X files (fields → their variable)
  computes   variable → variable      the code: traced (trace.py) and, where tags were lost, static (step 3)
  sums_to    emission variable → C    the crosswalk (an emission field of the variable belongs to the category)

Test (plan step 5): every lever / uncertainty → output link seen in the runs (backend/rdm/mapping/maps/<run>.csv)
should have a path in the network from the group to the output's variable. Runs are used only here, never to
add an edge (plan rule 3).

    python -m backend.rdm.network.assemble        (uganda_metamodel_env)
writes
    network/out/<run>_nodes.csv, <run>_edges.csv, <run>_test.csv (one row per run link: explained or not)
"""

import json
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd

from backend.rdm.mapping.build_mapping import MAPS_DIR
from backend.rdm.runs import get_run
from backend.rdm.tools.information import crosswalk

OUT = Path(__file__).parent / "out"
NEMOMOD_SUBSECTORS = {"Energy Technology", "Energy Storage", "Energy Fuels"}


def load(run):
    p = lambda s: OUT / f"{run.name}_{s}.csv"
    fields, variables = pd.read_csv(p("fields")), pd.read_csv(p("variables"))
    edges = [pd.read_csv(p("edges_traced")).assign(source_kind="traced")]
    if p("edges_static").exists():
        edges.append(pd.read_csv(p("edges_static")).assign(source_kind="static"))
    return fields, variables, pd.concat(edges, ignore_index=True)


def build(run) -> tuple:
    fields, variables, code = load(run)
    var_of = dict(zip(fields.field, fields.variable))
    rows = []
    for kind, f in (("L", "groups_l"), ("X", "groups_x")):
        g = pd.read_csv(run.local(f))
        col = "variable_field" if "variable_field" in g else "variable"
        for (gid, v), _ in g.assign(v=g[col].map(var_of)).dropna(subset=["v"]).groupby(["variable_trajectory_group", "v"]):
            rows.append({"source": f"{kind}{int(gid)}", "target": v, "type": "sets", "provenance": run.local(f).name})
    for r in code.drop_duplicates(["source", "target"]).itertuples():
        rows.append({"source": r.source, "target": r.target, "type": "computes",
                     "provenance": f"{r.source_kind}: {r.model}.{r.function}"})
    # The electricity model is one black box (plan rule 5). Besides what its Python wrapper reads and writes
    # (traced), it takes every input variable of the subsectors it solves and gives every output variable of them:
    # these go to and come from its SQL tables without passing NumPy.
    nemo = "NemoMod (electricity optimisation)"
    solved = variables[variables.subsector.isin(NEMOMOD_SUBSECTORS)]
    for v in solved[solved.type == "Input"].variable:
        rows.append({"source": v, "target": nemo, "type": "computes",
                     "provenance": "declared: input of a subsector NemoMod solves"})
    for v in solved[solved.type == "Output"].variable:
        rows.append({"source": nemo, "target": v, "type": "computes",
                     "provenance": "declared: output of a subsector NemoMod solves"})
    for slug, c in crosswalk(run).items():
        for v in sorted({var_of[f] for f in c["fields"] if f in var_of}):
            rows.append({"source": v, "target": f"C:{slug}", "type": "sums_to", "provenance": "crosswalk"})
    edges = pd.DataFrame(rows).drop_duplicates(["source", "target", "type"])

    nodes = variables.rename(columns={"variable": "id"}).assign(kind=lambda d: d.type.str.lower())
    groups = json.loads(run.registry.read_text())
    extra = [{"id": f"{k}{int(f['group_id'])}", "kind": "lever" if k == "L" else "uncertainty",
              "information": f["display_name"], "sector": f["sector"]}
             for block, k in (("lever_features", "L"), ("exogenous_features", "X")) for f in groups[block].values()]
    extra += [{"id": f"C:{slug}", "kind": "category", "information": c["display"]} for slug, c in crosswalk(run).items()]
    nodes = pd.concat([nodes, pd.DataFrame(extra)], ignore_index=True)
    return nodes, edges


def reach(edges: pd.DataFrame) -> callable:
    nxt = defaultdict(set)
    for s, t in zip(edges.source, edges.target):
        nxt[s].add(t)
    cache = {}

    def from_(start):
        if start not in cache:
            seen, q = {start}, deque([start])
            while q:
                for n in nxt[q.popleft()]:
                    if n not in seen:
                        seen.add(n)
                        q.append(n)
            cache[start] = seen
        return cache[start]
    return from_


def test(run, nodes, edges) -> pd.DataFrame:
    fields = pd.read_csv(OUT / f"{run.name}_fields.csv")
    var_of = dict(zip(fields.field, fields.variable))
    m = pd.read_csv(MAPS_DIR / f"{run.name}.csv")
    m = m[m.status != "structural, output constant in runs"]
    # subsector totals (emission_co2e_subsector_total_*) are aggregates, not model variables: not tested
    m = m[~m.output_field.str.startswith("emission_co2e_subsector_total_")]
    r = reach(edges)
    m = m.assign(variable=m.output_field.map(var_of), group=m.group_kind + m.group_id.astype(str))
    m["explained"] = [v in r(g) if isinstance(v, str) else False for g, v in zip(m.group, m.variable)]
    return m[["group", "group_kind", "sector", "output_field", "output_kind", "variable", "status", "explained"]]


if __name__ == "__main__":
    run = get_run()
    nodes, edges = build(run)
    nodes.to_csv(OUT / f"{run.name}_nodes.csv", index=False)
    edges.to_csv(OUT / f"{run.name}_edges.csv", index=False)
    t = test(run, nodes, edges)
    t.to_csv(OUT / f"{run.name}_test.csv", index=False)

    print(f"nodes {len(nodes)} · edges {len(edges)} {edges.type.value_counts().to_dict()}")
    linked = set(edges.source) | set(edges.target)
    aws = nodes[(nodes.n_fields_in_aws > 0)]
    print(f"variables with data in AWS and no edge: {(~aws.id.isin(linked)).sum()} of {len(aws)}")
    print(f"run links explained by a path: {t.explained.sum()} of {len(t)} ({t.explained.mean():.1%})")
    print(t.groupby(["group_kind", "output_kind"]).explained.agg(["sum", "size", "mean"]).round(3).to_string())
    print(t.groupby("status").explained.mean().round(3).to_string())
