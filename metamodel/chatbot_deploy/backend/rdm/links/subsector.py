"""
Variable → emission links by the subsector-name rule, for expert review.

Rule (decided 2026-10-13): a model_output variable is linked to a decomposed_emissions field when
  1. both names carry the same SISEPUEDE subsector code (agrc, lvst, trns, …); for energy-fuel
     variables (enfu) the code of the sector using the fuel counts, and
  2. they share at least one specific word — what the quantity is about (cattle, rice,
     road_light, croplands …) — once generic words, gases, units and the subsector are removed.

Only the 505 emission fields in the crosswalk are used, so every link also names the inventory
category the surrogate reports. Experts can add missing links in the review file; the rule is a
starting point, not a model of SISEPUEDE's equations.

    python -m backend.rdm.links.subsector
writes
    backend/rdm/links/<run>_variable_emission_links.csv    one row per (variable, emission field)
    backend/rdm/links/<run>_variable_category_links.csv    one row per (variable, category): the review file
"""

import re
from pathlib import Path

import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.runs import Run
from backend.rdm.tools import information as I

OUT_DIR = Path(__file__).parent
SUBSECTORS = {"agrc": "Agriculture", "frst": "Forestry", "lndu": "Land use", "lsmm": "Livestock manure",
              "lvst": "Livestock", "soil": "Soil", "ccsq": "Carbon capture", "entc": "Electricity generation",
              "enfu": "Energy fuels", "enst": "Energy storage", "fgtv": "Fugitive emissions",
              "inen": "Industrial energy", "scoe": "Buildings (stationary combustion)", "trde": "Transport demand",
              "trns": "Transport", "ippu": "Industrial processes", "trww": "Wastewater", "waso": "Solid waste",
              "wali": "Liquid waste", "gnrl": "General", "econ": "Economy"}
GASES = {"co2", "ch4", "n2o", "co2e", "hfc", "pfc", "sf6", "nf3"}
GENERIC = {
    "emission", "emissions", "subsector", "total", "frac", "area", "pop", "demand", "prod", "production", "qty",
    "consumption", "energy", "energy_consumption", "tonne", "tonnes", "pj", "ha", "m3", "km", "mmm", "usd", "kg",
    "vehicle", "distance", "traveled", "initial", "calculated", "from", "to", "and", "of", "per", "the", "by",
    "with", "other", "net", "gross", "value", "fuel", "fuels", "yield", "conversion", "use", "trajectory",
}


def subsector(field: str):
    """The subsector a field belongs to. Energy-fuel fields name two codes, the fuel sector (enfu)
    and the sector that uses the fuel (energy_demand_enfu_…_ccsq_fuel_coal): the user wins."""
    codes = [t for t in field.split("_") if t in SUBSECTORS]
    if len(codes) > 1 and codes[0] == "enfu":
        return codes[1]
    return codes[0] if codes else None


def specific_words(field: str) -> set:
    toks = [t for t in re.split(r"_+", field) if t]
    keep = {t for t in toks if t not in GENERIC and t not in GASES and t not in SUBSECTORS
            and not re.fullmatch(r"[a-z]?\d+[a-z0-9]*|c\d.*", t)}
    return keep


def build(run: Run, store: Store) -> tuple:
    cat = I.category_of(run)
    cw = I.crosswalk(run)
    emis = pd.DataFrame({"emission_field": sorted(cat)})
    emis["subsector"] = emis.emission_field.map(subsector)
    emis["category"] = emis.emission_field.map(lambda f: cw[cat[f]]["display"])
    var = pd.DataFrame({"variable_field": store.variable_fields})
    var["subsector"] = var.variable_field.map(subsector)

    rows = []
    for s, ev in emis.groupby("subsector"):
        vv = var[var.subsector == s]
        for v in vv.variable_field:
            vw = specific_words(v)
            for e in ev.itertuples():
                shared = vw & specific_words(e.emission_field)
                if shared:
                    rows.append({"variable_field": v, "emission_field": e.emission_field, "subsector": s,
                                 "subsector_name": SUBSECTORS[s], "category": e.category,
                                 "shared_words": " ".join(sorted(shared))})
    links = pd.DataFrame(rows)

    # Supporting evidence: does some lever move both, in the lever → output mapping?
    m = I.links(run)
    mv = m[m.group_kind == "L"].groupby("output_field").group_id.apply(set).to_dict()
    links["levers_moving_both"] = [" ".join(str(g) for g in sorted(mv.get(a, set()) & mv.get(b, set())))
                                   for a, b in zip(links.variable_field, links.emission_field)]

    review = (links.groupby(["variable_field", "subsector_name", "category"])
              .agg(n_emission_fields=("emission_field", "nunique"),
                   emission_fields=("emission_field", lambda s: " | ".join(sorted(s))),
                   shared_words=("shared_words", lambda s: " ".join(sorted(set(" ".join(s).split())))),
                   levers_moving_both=("levers_moving_both", lambda s: " ".join(sorted({x for v in s for x in v.split()}, key=int))))
              .reset_index())
    review.insert(3, "expert_ok", "")
    review.insert(4, "expert_note", "")
    unlinked = var[~var.variable_field.isin(links.variable_field)]
    return links, review, unlinked


def write(run: Run, store: Store) -> dict:
    links, review, unlinked = build(run, store)
    p1 = OUT_DIR / f"{run.name}_variable_emission_links.csv"
    p2 = OUT_DIR / f"{run.name}_variable_category_links.csv"
    links.to_csv(p1, index=False)
    review.to_csv(p2, index=False)
    (OUT_DIR / f"{run.name}_unlinked_variables.csv").write_text(unlinked.to_csv(index=False))
    return {"links": len(links), "variables_linked": links.variable_field.nunique(),
            "emissions_linked": links.emission_field.nunique(), "review_rows": len(review),
            "variables_unlinked": len(unlinked)}


if __name__ == "__main__":
    from backend.rdm.runs import get_run
    r = get_run()
    print(write(r, Store(r)))
