"""
Step 1b · SISEPUEDE's model variables, their fields and attributes, joined to the fields the run has in AWS.

Runs in ssp_uganda_env (SISEPUEDE 1.4.0); reads network/out/<run>_aws_columns.csv from step 1a.

    /opt/miniconda3/envs/ssp_uganda_env/bin/python -m backend.rdm.network.inventory run_2026_05_30
writes
    network/out/<run>_variables.csv   one row per model variable: type, sector, subsector, unit, gas, fields
    network/out/<run>_fields.csv      one row per field: its model variable, its category, where it is in AWS
"""

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent / "out"
UNIT = re.compile(r"\$(UNIT-[A-Z-]+|GWP)\$\s*=\s*([a-z0-9_]+)", re.I)
GAS = re.compile(r"\$EMISSION-GAS\$\s*=\s*([a-z0-9]+)", re.I)
GAS_FIELD = re.compile(r"^emission_co2e_([a-z0-9]+)_")


def model_attributes():
    warnings.filterwarnings("ignore")
    from sisepuede.manager.sisepuede_file_structure import SISEPUEDEFileStructure
    return SISEPUEDEFileStructure(initialize_directories=False).model_attributes


def build(ma, aws: pd.DataFrame) -> tuple:
    where = aws.groupby("field").table.first().to_dict()
    vrows, frows = [], []
    for name in sorted(ma.all_variables):
        v = ma.get_variable(name)
        info = v.dict_varinfo
        schema = str(info.get("variable_schema", ""))
        units = "; ".join(f"{k.lower()} = {u}" for k, u in UNIT.findall(schema))
        gas = GAS.search(schema)
        fields = list(v.fields or [])
        in_aws = [f for f in fields if f in where]
        vrows.append({"variable": name, "type": info.get("variable_type"), "sector": info.get("sector"),
                      "subsector": info.get("subsector"), "subsector_abv": info.get("subsector_abv"),
                      "unit": units, "gas": gas.group(1) if gas else "",
                      "is_emission": bool(info.get("emissions_total_by_gas_component", 0)) or schema.startswith("``emission_co2e"),
                      "n_fields": len(fields), "n_fields_in_aws": len(in_aws),
                      "aws_tables": " | ".join(sorted({where[f] for f in in_aws})),
                      "information": str(info.get("information", "")).strip(), "schema": schema.strip("`")})
        cats = [c for k in (v.dict_category_keys or {}).values() for c in k]
        for i, f in enumerate(fields):
            g = GAS_FIELD.match(f)
            frows.append({"field": f, "variable": name, "category": cats[i] if len(cats) == len(fields) else "",
                          "gas": g.group(1) if g else (gas.group(1) if gas else ""), "aws_table": where.get(f, "")})
    return pd.DataFrame(vrows), pd.DataFrame(frows)


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "run_2026_05_30"
    aws = pd.read_csv(OUT / f"{run}_aws_columns.csv")
    variables, fields = build(model_attributes(), aws)
    variables.to_csv(OUT / f"{run}_variables.csv", index=False)
    fields.to_csv(OUT / f"{run}_fields.csv", index=False)

    # check · how much of AWS maps to a model variable (target ≥ 95% per table)
    known = set(fields.field)
    for table, g in aws.groupby("table"):
        hit = g.field.isin(known)
        print(f"{table}: {hit.sum()} of {len(g)} AWS columns map to a model variable ({hit.mean():.1%})")
        if (~hit).any():
            print("   unmapped e.g.:", ", ".join(g.field[~hit].head(6)))
    print(f"model variables: {len(variables)} ({(variables.n_fields_in_aws > 0).sum()} with a field in AWS)")
