"""
gen_emissions_sql.py
--------------------
Generate `queries/emissions_and_gdp.sql` AND `config/sector_categories.json`
from the team's official inventory crosswalk, so both the training extract and
the chatbot label sectors identically to the official pathways.

Why a generator (not a hand-written SQL):
  The crosswalk re-aggregates ~500 GRANULAR `emission_co2e_*` fields into the
  official inventory categories. Doing that by hand in SQL is error-prone and
  drifts the moment the crosswalk is updated. Instead we derive everything from
  ONE source of truth -- the crosswalk CSV -- and regenerate.

What it does:
  * Groups every `sisepuede_fields` entry by `aggregation_category` (union across
    the per-gas rows), de-duplicated.
  * Emits, per category, an arithmetic sum of COALESCE(field, 0) as
    `emission_co2e_category_<slug>` -- COALESCE so a single missing field can't
    null out the whole category. decomposed_emissions has one row per
    (primary_id, time_period), so this is a per-row sum, not a GROUP BY.
  * Writes `config/sector_categories.json`: slug -> {display, lead_code, lulucf}
    for the app to consume (replaces the ad-hoc SECTOR_DISPLAY_NAMES).

Run:  python athena/gen_emissions_sql.py      (writes the two files, prints a summary)
It writes NOTHING to AWS and costs nothing.
"""

import csv
import json
import os
import re
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # surrogate_model_sector/
CROSSWALK = os.path.join(ROOT, "config", "crosswalk_inventory_to_sisepuede_20260510.csv")
SQL_OUT = os.path.join(HERE, "queries", "emissions_and_gdp.sql")
JSON_OUT = os.path.join(ROOT, "config", "sector_categories.json")
# The chatbot loads the SAME sidecar (it must travel inside the Docker image, which
# only copies backend/). We write a second copy there so the app and the training
# pipeline never drift. If the app tree isn't present, we just skip it.
APP_JSON_OUT = os.path.normpath(os.path.join(
    ROOT, "..", "chatbot_deploy", "backend", "sector_categories.json"))

# Per-category presentation, from the team's official Tableau legend (2026-07-15).
# `order` is the legend/stacking order; `color` is read from that legend (hex values
# estimated from the image — safe to fine-tune to the exact Tableau values later).
# Slugs must match slug(aggregation_category). Any category missing here falls back
# to a neutral grey (asserted against in main() so a new category can't slip through).
STYLE: dict = {
    "fugitive_emissions":                {"order":  1, "short": "Fugitive",        "color": "#E15759"},
    "fuel_production":                   {"order":  2, "short": "Fuel Production",  "color": "#FF9DA7"},
    "electricity_and_heat_generation":   {"order":  3, "short": "Electricity",      "color": "#EDC948"},
    "commercial":                        {"order":  4, "short": "Commercial",       "color": "#4E79A7"},
    "residential":                       {"order":  5, "short": "Residential",      "color": "#A0CBE8"},
    "transportation":                    {"order":  6, "short": "Transport",        "color": "#79706E"},
    "industrial_combustion":             {"order":  7, "short": "Ind. Combustion",  "color": "#B07AA1"},
    "ippu":                              {"order":  8, "short": "IPPU",             "color": "#D4A6C8"},
    "solid_waste":                       {"order":  9, "short": "Solid Waste",      "color": "#9D7660"},
    "wastewater_treatment":              {"order": 10, "short": "Wastewater",       "color": "#D7B5A6"},
    "agriculture_and_managed_soil":      {"order": 11, "short": "Agriculture",      "color": "#F28E2B"},
    "livestock":                         {"order": 12, "short": "Livestock",        "color": "#FFBE7D"},
    "deforestation":                     {"order": 13, "short": "Deforestation",    "color": "#C7E9B4"},
    "forest_land_removals":              {"order": 14, "short": "Forest Removals",  "color": "#A1D99B"},
    "forest_land_methane":               {"order": 15, "short": "Forest CH4",       "color": "#74C476"},
    "other_land_use_conversion":         {"order": 16, "short": "Other Land Use",   "color": "#4CAF50"},
    "other_not_estimated_conversion":    {"order": 17, "short": "Other Conversion", "color": "#41A845"},
    "other_not_estimated_sequestration": {"order": 18, "short": "Other Seq.",       "color": "#2E8B37"},
    "other_not_estimated_soils":         {"order": 19, "short": "Other Soils",      "color": "#237A2E"},
    "forest_land_sequestration":         {"order": 20, "short": "Forest Seq.",      "color": "#14602A"},
    "carbon_capture_industries":         {"order": 21, "short": "Carbon Capture",   "color": "#F5921B"},
    "other_combustion":                  {"order": 22, "short": "Other Combustion", "color": "#B07AA1"},
    "wetlands":                          {"order": 23, "short": "Wetlands",         "color": "#86BCDA"},
}

# Column prefix for the generated category columns. Deliberately NOT
# `emission_co2e_subsector_total_` -- these are inventory categories, not raw
# subsector totals. assemble_training_data.py strips this prefix, then names the
# parquet target `emission_<slug>_yr<year>` (that output prefix is unchanged).
COL_PREFIX = "emission_co2e_category_"

TARGET_TPS = "10, 20, 25, 35, 45, 55"            # years 2025/35/40/50/60/70


def slug(name: str) -> str:
    """'Forest Land - Removals' -> 'forest_land_removals'. Stable join key used
    across SQL, parquet, model targets and the app. Must not contain '_yr'
    (predictor.py splits `emission_<slug>_yr<year>` on '_yr')."""
    s = re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_")
    assert "_yr" not in s, f"slug {s!r} contains '_yr' -- would break target parsing"
    return s


def load_categories():
    """category display name -> OrderedDict{field: None} (deduped, order-stable)."""
    cats = OrderedDict()
    lead = {}      # display -> ssp_subsector lead code (first seen)
    lulucf = {}    # display -> True/False from aggregation_category_2
    with open(CROSSWALK, newline="") as f:
        for r in csv.DictReader(f):
            cat = r["aggregation_category"]
            cats.setdefault(cat, OrderedDict())
            lead.setdefault(cat, r["ssp_subsector"])
            lulucf.setdefault(cat, r["aggregation_category_2"].strip().upper() == "LULUCF")
            for field in r["sisepuede_fields"].split(":"):
                field = field.strip()
                if field:
                    cats[cat][field] = None
    return cats, lead, lulucf


def build_sql(cats) -> str:
    ordered = sorted(cats)                        # alphabetical for a stable diff
    lines = []
    for cat in ordered:
        fields = list(cats[cat])
        terms = " + ".join(f"COALESCE(e.{fld}, 0)" for fld in fields)
        lines.append(f"    ({terms}) AS {COL_PREFIX}{slug(cat)}")
    select_block = ",\n".join(lines)

    n_fields = sum(len(v) for v in cats.values())
    header = f"""-- emissions_and_gdp.sql
-- ---------------------------------------------------------------------------
-- GENERATED by athena/gen_emissions_sql.py from
--   config/crosswalk_inventory_to_sisepuede_20260510.csv
-- Do NOT edit by hand -- re-run the generator if the crosswalk changes.
--
-- FINAL (post-processed) emissions RE-AGGREGATED into the official inventory
-- categories, + derived GDP, for the surrogate-model training set.
--
-- Emissions source: decomposed_emissions -- post-processed FINAL emissions, one
--   row per (primary_id, time_period). It carries the ~620 GRANULAR
--   emission_co2e_* fields, which the crosswalk sums into {len(cats)} categories
--   ({n_fields} distinct fields, each mapped to exactly one category -- verified).
--   Each field is COALESCE(...,0) so one missing field can't null a category.
-- GDP source: model_output -- derive GDP in billions USD ("mmm") from
--   per-capita GDP * total population / 1e9.
--
-- Joined on (primary_id, time_period). `region` is a Hive partition on both
-- tables, so filtering both prunes each scan to that region's files.
--
-- Target years, encoded as time_period (= year - 2015):
--     10/20/25/35/45/55  ->  2025/2035/2040/2050/2060/2070
--
-- {{region}} is filled in by run_extracts.py from the config.
-- ---------------------------------------------------------------------------
SELECT
    e.primary_id,
    e.time_period,
{select_block},
    m.gdp_per_capita_usd * m.population_gnrl_total / 1e9 AS gdp_mmm_usd
FROM decomposed_emissions e
JOIN model_output m
    ON  e.primary_id  = m.primary_id
    AND e.time_period = m.time_period
WHERE e.region = '{{region}}'
  AND m.region = '{{region}}'
  AND e.time_period IN ({TARGET_TPS})
  AND m.time_period IN ({TARGET_TPS});
"""
    return header


def build_json(cats, lead, lulucf) -> dict:
    out = OrderedDict()
    for cat in sorted(cats):
        s = slug(cat)
        style = STYLE.get(s, {"order": 999, "short": cat, "color": "#888888"})
        out[s] = {
            "display": cat.replace("  ", " "),   # normalise the "Other  Combustion" double space
            "short": style["short"],
            "color": style["color"],
            "order": style["order"],
            "lead_code": lead[cat],
            "lulucf": lulucf[cat],
            "fields": list(cats[cat]),           # granular emission_co2e_* fields summed into this category
        }
    return out


def main():
    cats, lead, lulucf = load_categories()

    # sanity: slugs unique, no field shared across categories
    slugs = [slug(c) for c in cats]
    assert len(slugs) == len(set(slugs)), "slug collision"
    seen = {}
    for cat, fields in cats.items():
        for fld in fields:
            assert fld not in seen, f"field {fld} in both {seen[fld]} and {cat}"
            seen[fld] = cat

    # Every category must have an explicit STYLE entry (colour/order from the team's
    # legend) — a new category without one would silently render grey/unordered.
    missing_style = [slug(c) for c in cats if slug(c) not in STYLE]
    assert not missing_style, f"add STYLE entries for: {missing_style}"

    sql = build_sql(cats)
    with open(SQL_OUT, "w") as f:
        f.write(sql)
    meta = build_json(cats, lead, lulucf)
    payload = json.dumps(meta, indent=2) + "\n"
    with open(JSON_OUT, "w") as f:
        f.write(payload)
    print(f"Wrote {SQL_OUT}")
    print(f"Wrote {JSON_OUT}")
    if os.path.isdir(os.path.dirname(APP_JSON_OUT)):
        with open(APP_JSON_OUT, "w") as f:
            f.write(payload)
        print(f"Wrote {APP_JSON_OUT}  (chatbot copy — keep in sync)")
    else:
        print(f"(skipped app copy — {os.path.dirname(APP_JSON_OUT)} not present)")

    print(f"\n{len(cats)} categories, {len(seen)} distinct fields:")
    for s, info in sorted(meta.items(), key=lambda kv: kv[1]["order"]):
        tag = "LULUCF" if info["lulucf"] else ""
        print(f"  {info['order']:2d}. {s:34s} <- {len(info['fields']):3d} fields  {info['color']}  [{info['lead_code']}] {tag}")


if __name__ == "__main__":
    main()
