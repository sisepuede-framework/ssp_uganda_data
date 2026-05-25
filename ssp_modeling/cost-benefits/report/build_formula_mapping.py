"""
build_formula_mapping.py
Reads cb_config_params.xlsx and writes cba_formula_mapping.csv.
One row per cost/benefit line item with its Tableau category, formula, and factor.
Run in: ssp_uganda_env
"""

import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[3]
EXCEL = REPO / "ssp_modeling/cost-benefits/cb_cost_factors/cb_config_params.xlsx"
OUT_CSV = Path(__file__).parent / "cba_formula_mapping.csv"

# ── Alias dictionaries ─────────────────────────────────────────────────────────
SECTOR_ALIAS = {
    "agrc": "AG - Crops",
    "ccsq": "CCS",
    "enfu": "EN - Electricity/Heat (enfu)",
    "entc": "EN - Power Industry (entc)",
    "fgtv": "EN - Fugitive emissions",
    "inen": "EN - Industrial combustion",
    "ippu": "IN - Industrial processes",
    "lndu": "LULUCF - Forest land",
    "lsmm": "AG - Livestock (manure)",
    "lvst": "AG - Livestock",
    "pflo": "pflo",
    "scoe": "EN - Building",
    "soil": "LULUCF - Organic soil",
    "trns": "EN - Transportation",
    "trww": "Waste - Wastewater treatment (trww)",
    "wali": "Waste - Wastewater (liquid waste)",
    "waso": "Waste - Solid waste",
}

CB_TYPE_ALIAS = {
    "technical_cost":              "Capital cost",
    "technical_savings":           "O&M savings",
    "system_cost":                 "Other costs/benefits",
    "fuel_cost":                   "Fuel cost savings",
    "consumer_savings":            "Consumer savings",
    "crop_value":                  "Crop value",
    "lvst_value":                  "Livestock value",
    "ippu_value":                  "IPPU value",
    "human_health":                "Human Health",
    "air_pollution":               "Pollution (air)",
    "indoor_air_pollution":        "Air pollution (indoor)",
    "env_pollution":               "Pollution (environment)",
    "land_pollution":              "Pollution (land)",
    "water_pollution":             "Pollution (water)",
    "road_safety":                 "Other costs/benefits",
    "congestion":                  "Other costs/benefits",
    # ecosystem_services handled separately via item_1
    "ecosystem_services":          "Ecosystem services",
    # sub-types stored directly as their own cb_type in the Excel
    "ecosystem_services_wetlands":   "Ecosystem services wetlands",
    "ecosystem_services_grasslands": "Ecosystem services grasslands",
}

SECTOR_SPECIFIC_ITEM1_ALIAS = {
    "fuel_cost":        "Fuel cost savings",
    "electricity_cost": "O&M savings",
}


def tableau_label(cb_type: str, item1: str) -> str:
    if cb_type == "ecosystem_services":
        if item1 == "grasslands":
            return "Ecosystem services grasslands"
        if item1 == "wetlands":
            return "Ecosystem services wetlands"
        return "Ecosystem services"
    if cb_type == "sector_specific":
        return SECTOR_SPECIFIC_ITEM1_ALIAS.get(item1, "Other costs/benefits")
    return CB_TYPE_ALIAS.get(cb_type, "Other costs/benefits")


def _factor_display(multiplier, unit) -> str:
    """Format the actual multiplier used in the computation."""
    raw_unit = str(unit).strip() if not pd.isna(unit) else ""
    raw_unit = "" if raw_unit == "ND" else raw_unit
    try:
        num = float(multiplier)
        num_str = f"{num:,.0f}" if abs(num) >= 1000 else f"{num:g}"
    except (TypeError, ValueError):
        num_str = str(multiplier)
    return f"{num_str} {raw_unit}".strip() if raw_unit else num_str


# cb_strategy_specific_function routing:
#  WALI rows        → computed via sanitation classification table (separate path)
#  electricity_cost → NOT computed (no matching implementation)
#  change_in_emissions → NOT computed (placeholder)
#  enfu:fuel_cost   → empirically computed; applies standard formula to total fuel value consumed
#  sector_specific:fuel_cost → now use cb_apply_cost_factors (computed normally)

_NOT_COMPUTED_PREFIXES = {
    "cb:ccsq:sector_specific:electricity_cost",
    "cb:inen:sector_specific:electricity_cost",
    "cb:scoe:sector_specific:electricity_cost",
    "cb:trns:sector_specific:electricity_cost",
    "change_in_emissions",
}


def _strategy_specific_note(var_name: str, factor: str) -> str:
    v = str(var_name)
    if any(v.startswith(p) for p in _NOT_COMPUTED_PREFIXES):
        return "Not computed — placeholder entry (no matching implementation in current package version)"
    if v.startswith("cb:wali"):
        return f"Computed via WALI sanitation classification table (per-capita tier costs) × {factor}"
    # enfu:fuel_cost and any other unmatched rows: empirically confirmed computed via standard formula
    return f"(SSP_strategy − SSP_baseline) × {factor} (applied to total fuel value consumed per fuel type)"


def formula_text(cb_function, multiplier, unit, annual_change, var_name="") -> str:
    if pd.isna(cb_function) or cb_function == "":
        return "Factor not specified in config"
    fn = str(cb_function).strip()
    factor = _factor_display(multiplier, unit)
    ac = "" if annual_change == 1 else f" × {annual_change}^max(0, year−2023)"

    if fn in ("cb_apply_cost_factors", "cb_system_fuel_costs"):
        return f"(SSP_strategy − SSP_baseline) × {factor}{ac}"
    if fn == "cb_difference_between_two_strategies":
        return f"(SSP_strategy − SSP_comparison_strategy) × {factor}{ac}"
    if fn == "cb_strategy_specific_function":
        return _strategy_specific_note(var_name, factor)
    # All other named sector functions — standard base formula
    return f"(SSP_strategy − SSP_baseline) × {factor}{ac}"


def parse_variable(var: str):
    parts = var.split(":")
    return {
        "sector_code": parts[1] if len(parts) > 1 else "",
        "cb_type":     parts[2] if len(parts) > 2 else "",
        "item_1":      parts[3] if len(parts) > 3 else "",
        "item_2":      parts[4] if len(parts) > 4 else "",
    }


def load_excel():
    xl = pd.ExcelFile(EXCEL)
    tx = xl.parse("tx_table")[
        ["output_variable_name", "output_display_name", "display_notes", "cost_type"]
    ]
    cf = xl.parse("cost_factors")[
        [
            "output_variable_name", "output_display_name", "difference_variable", "multiplier",
            "multiplier_unit", "natural_multiplier_units", "annual_change",
            "cb_function", "display_notes",
        ]
    ].rename(columns={"display_notes": "methodology_notes", "output_display_name": "cf_display_name"})
    tc = xl.parse("transformation_costs")[
        [
            "output_variable_name", "transformation_code", "difference_variable",
            "multiplier", "multiplier_unit", "natural_multiplier_units",
            "annual_change", "cb_function",
        ]
    ] if "natural_multiplier_units" in xl.parse("transformation_costs").columns else \
        xl.parse("transformation_costs")[
        [
            "output_variable_name", "transformation_code", "difference_variable",
            "multiplier", "multiplier_unit", "annual_change", "cb_function",
        ]
    ]
    return tx, cf, tc


def build():
    tx, cf, tc = load_excel()

    # ── System costs: join tx_table ↔ cost_factors ─────────────────────────────
    sys_rows = tx[tx["cost_type"] == "system_cost"].copy()
    sys_merged = sys_rows.merge(cf, on="output_variable_name", how="left")
    sys_merged["transformation_code"] = ""
    sys_merged["source_sheet"] = "cost_factors"

    # When tx_table display name is "ND", fall back to the cost_factors display name
    if "cf_display_name" in sys_merged.columns:
        sys_merged["output_display_name"] = sys_merged.apply(
            lambda r: r["cf_display_name"]
            if str(r.get("output_display_name", "")).strip() in ("ND", "nan", "")
            else r["output_display_name"],
            axis=1,
        )

    # ── Transformation costs: join tx_table ↔ transformation_costs ─────────────
    tx_rows = tx[tx["cost_type"] == "transformation_cost"].copy()
    if "natural_multiplier_units" not in tc.columns:
        tc["natural_multiplier_units"] = ""
    tx_merged = tx_rows.merge(tc, on="output_variable_name", how="left")
    tx_merged["methodology_notes"] = tx_merged.get("display_notes", "")
    tx_merged["source_sheet"] = "transformation_costs"

    combined = pd.concat([sys_merged, tx_merged], ignore_index=True)

    # ── Parse variable parts ────────────────────────────────────────────────────
    parsed = combined["output_variable_name"].apply(parse_variable)
    combined = pd.concat([combined, pd.DataFrame(list(parsed))], axis=1)

    # Normalise the SISEPUEDE variable column name
    if "difference_variable" in combined.columns:
        combined["sisepuede_variable"] = combined["difference_variable"]
    elif "sisepuede_variable" not in combined.columns:
        combined["sisepuede_variable"] = ""

    # ── Apply aliases ───────────────────────────────────────────────────────────
    combined["sector_alias"] = combined["sector_code"].map(SECTOR_ALIAS).fillna(combined["sector_code"])
    combined["cb_type_display"] = combined.apply(
        lambda r: tableau_label(r["cb_type"], r["item_1"]), axis=1
    )
    combined["tableau_type"] = combined["cb_type"].apply(
        lambda x: "Cost" if x == "technical_cost" else "Benefit"
    )
    combined["tableau_category"] = combined.apply(
        lambda r: r["sector_alias"] if r["tableau_type"] == "Cost" else r["cb_type_display"],
        axis=1,
    )

    # ── Unified factor display — always uses the actual multiplier + unit ───────
    combined["factor_display"] = combined.apply(
        lambda r: _factor_display(r.get("multiplier", ""), r.get("multiplier_unit", "")),
        axis=1,
    )

    # ── Formula text ────────────────────────────────────────────────────────────
    combined["formula_text"] = combined.apply(
        lambda r: formula_text(
            r.get("cb_function"),
            r.get("multiplier", ""),
            r.get("multiplier_unit", ""),
            r.get("annual_change", 1),
            r.get("output_variable_name", ""),
        ),
        axis=1,
    )
    combined["gdp_formula"] = "value_B_USD / gdp_mmm_usd"

    # ── Source label (which Excel sheet drove this row) ─────────────────────────
    combined["source"] = combined["transformation_code"].apply(
        lambda x: f"Investment cost — {x}" if str(x).strip() not in ("", "nan") else "System cost"
    )

    # ── Formula type (short label for appendix tables) ──────────────────────────
    def _formula_type(row) -> str:
        fn  = str(row.get("cb_function", "")).strip()
        var = str(row.get("output_variable_name", ""))
        if fn in ("cb_apply_cost_factors", "cb_system_fuel_costs"):
            return "Standard"
        if fn == "cb_difference_between_two_strategies":
            return "Vs. comparison strategy"
        if fn == "cb_strategy_specific_function":
            if var.startswith("cb:wali"):
                return "WALI classification table"
            if any(var.startswith(p) for p in _NOT_COMPUTED_PREFIXES):
                return "Not computed"
            return "Standard (fuel value)"
        return "Sector-specific"

    combined["formula_type"] = combined.apply(_formula_type, axis=1)

    # ── Deduplicate rows that repeat the same item across many fuel variables ──
    # Keep only the first occurrence of each (display_name, cb_type, formula_text) triple
    combined = combined.drop_duplicates(
        subset=["output_display_name", "cb_type", "formula_text"], keep="first"
    ).reset_index(drop=True)

    # ── Select and rename output columns ────────────────────────────────────────
    # Ensure methodology_notes exists
    if "methodology_notes" not in combined.columns:
        combined["methodology_notes"] = combined.get("display_notes", "")

    out = combined[[
        "tableau_type",
        "tableau_category",
        "sector_code",
        "sector_alias",
        "cb_type",
        "cb_type_display",
        "item_1",
        "item_2",
        "output_display_name",
        "sisepuede_variable",
        "factor_display",
        "multiplier",
        "multiplier_unit",
        "annual_change",
        "cb_function",
        "transformation_code",
        "source",
        "formula_type",
        "formula_text",
        "gdp_formula",
        "methodology_notes",
    ]].rename(columns={
        "output_display_name": "display_name",
        "factor_display":      "factor_readable",
    })

    out.to_csv(OUT_CSV, index=False)
    print(f"Written: {OUT_CSV}  ({len(out)} rows)")

    # Quick summary
    print("\nCosts by sector:")
    print(out[out["tableau_type"] == "Cost"]["tableau_category"].value_counts().to_string())
    print("\nBenefits by category:")
    print(out[out["tableau_type"] == "Benefit"]["tableau_category"].value_counts().to_string())


if __name__ == "__main__":
    build()
