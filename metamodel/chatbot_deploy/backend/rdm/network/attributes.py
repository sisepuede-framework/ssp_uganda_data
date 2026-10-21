"""
Node and field attributes for the network viewer and the agent: readable name, type, sector, subsector, gas,
unit (with where it came from), SISEPUEDE category, and for emission fields the XGBoost category they sum into.

Unit rule, in order (unit_source says which applied):
  config      emission fields are in Mt CO₂e (SISEPUEDE configuration: emissions_mass = MT)
  field name  a unit written in the field name (_tonne, _pj, _ha, _mmm_usd …; frac_ = fraction 0–1)
  schema      input variables: the unit of their specification, the one their values are entered in
  name        elasticities, scalars, ratios, fractions, probabilities, shares: no unit
  config      outputs of energy (PJ) or area (ha) with no unit in their name or schema: SISEPUEDE reports them in
              its configuration units (energy_units = PJ, area_units = ha)
  unknown     otherwise; never guessed

    python -m backend.rdm.network.attributes   → network/out/<run>_node_attributes.csv, <run>_field_attributes.csv
"""

import re
from pathlib import Path

import pandas as pd

from backend.rdm.runs import get_run
from backend.rdm.tools.information import category_of, crosswalk

OUT = Path(__file__).parent / "out"
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
FIELD_UNITS = [("_mmm_usd", "billion USD"), ("_mm_usd", "million USD"), ("vehicle_distance_traveled", "vehicle-km"),
               ("_mtkm", "million tonne-km"), ("_mpkm", "million passenger-km"), ("_tonne", "tonne"),
               ("_kt", "kt"), ("_pj", "PJ"), ("_tj", "TJ"), ("_gw", "GW"), ("_ha", "ha"), ("_m3", "m³"),
               ("_km", "km"), ("_kg", "kg")]
SCHEMA_UNIT = re.compile(r"unit-([a-z]+) = ([a-z0-9_]+)")
NO_UNIT = re.compile(r"Elasticity|Scalar|Ratio|Fraction|Probability|Proportion|Share|Correction Factor|Efficiency", re.I)


def clean(name: str) -> str:
    """:math:`\\text{CH}_4` Emissions → CH₄ Emissions"""
    s = str(name).replace(":math:", "").replace("`", "")
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"_\{([^}]*)\}|_(\d+)", lambda m: (m.group(1) or m.group(2)).translate(SUB), s)
    return re.sub(r"\s+", " ", s).strip()


def field_unit(field: str, var_type: str, schema_unit: str, variable: str = "") -> tuple:
    if field.startswith("emission_co2e"):
        return "Mt CO₂e", "config"
    if field.startswith("frac_"):
        return "fraction (0–1)", "field name"
    for tok, u in FIELD_UNITS:
        if tok in field:
            return u, "field name"
    if var_type == "Input" and isinstance(schema_unit, str) and schema_unit:
        return "; ".join(f"{u} ({k})" for k, u in SCHEMA_UNIT.findall(schema_unit)), "schema"
    if NO_UNIT.search(variable):
        return "no unit (ratio, scalar or share)", "name"
    if var_type == "Output" and re.search(r"Energy (Consumption|Demand)|Energy Demand", variable):
        return "PJ", "config"
    if var_type == "Output" and variable.startswith("Area"):
        return "ha", "config"
    return "unknown", "unknown"


def build(run) -> tuple:
    v = pd.read_csv(OUT / f"{run.name}_variables.csv")
    f = pd.read_csv(OUT / f"{run.name}_fields.csv")
    cat = category_of(run)
    display = {k: c["display"] for k, c in crosswalk(run).items()}
    vt = dict(zip(v.variable, v.type))
    vu = dict(zip(v.variable, v.unit))
    f = f[f.aws_table.notna()].copy()
    units = [field_unit(r.field, vt.get(r.variable), vu.get(r.variable), r.variable) for r in f.itertuples()]
    f["unit"], f["unit_source"] = zip(*units)
    f["xgboost_category"] = f.field.map(cat).map(display)
    nodes = v[v.n_fields_in_aws > 0].copy()
    nodes.insert(1, "name", nodes.variable.map(clean))
    nodes["xgboost_categories"] = nodes.variable.map(
        f.dropna(subset=["xgboost_category"]).groupby("variable").xgboost_category
         .apply(lambda s: " | ".join(sorted(set(s)))))
    nodes["units"] = nodes.variable.map(f.groupby("variable").unit.apply(lambda s: " | ".join(sorted(set(s)))))
    nodes = nodes[["variable", "name", "type", "sector", "subsector", "gas", "units", "xgboost_categories",
                   "n_fields", "n_fields_in_aws", "aws_tables", "information"]]
    return nodes, f[["field", "variable", "category", "gas", "unit", "unit_source", "xgboost_category", "aws_table"]]


if __name__ == "__main__":
    run = get_run()
    nodes, fields = build(run)
    nodes.to_csv(OUT / f"{run.name}_node_attributes.csv", index=False)
    fields.to_csv(OUT / f"{run.name}_field_attributes.csv", index=False)
    print(f"nodes {len(nodes)} · fields {len(fields)}")
    print(fields.unit_source.value_counts().to_string())
    print(fields[fields.unit_source == "unknown"].variable.value_counts().head(12).to_string())
