"""
transformation_templates_v2.py
-------------------------------
Extends the original module with two new dictionaries:

  POLICY_DESCRIPTIONS  – static one- or two-sentence prose for the
                         "Policy Description" column. No placeholders.

  SHORT_TEMPLATES      – compact phrase for the pathway columns (BAU /
                         Unconditional / Conditional). Single {} or {0}/{1}
                         for the formatted magnitude value(s).

Public API
----------
  generate_policy_description(code)         → str | None
  generate_short_text(code, raw_magnitude)  → str | None  ("—" when inactive)
  build_table_rows(df)                      → list[dict]
      Returns one dict per transformation with keys:
        subsector, subsector_label, transformation_name, transformation_code,
        policy_description,
        bau, unconditional, conditional
      where bau/unconditional/conditional are already-formatted strings
      ready for the table cells.
"""

import ast, math
from typing import Optional, Union
import pandas as pd

# Re-use the value extraction helpers from the original module.
# (Copy them here so this file is self-contained.)

_ABSOLUTE_MAGNITUDE = {"TX:CCSQ:INC_CAPTURE", "TX:ENFU:ADJ_EXPORTS"}
_TWO_VALUE          = {"TX:TRNS:SHIFT_MODE_REGIONAL", "TX:WASO:INC_ANAEROBIC_AND_COMPOST"}
_DICT_KEY_MAP       = {
    "TX:AGRC:INC_CONSERVATION_AGRICULTURE": "magnitude_removed",
    "TX:INEN:SHIFT_FUEL_HEAT":              "frac_switchable",
    "TX:PFLO:INC_IND_CCS":                  "dict_magnitude_eff",
    "TX:SCOE:INC_EFFICIENCY_HEAT":          "fuel_biomass",
}
_STRUCTURAL_DICT = {
    "TX:LSMM:INC_MANAGEMENT_CATTLE_PIGS",
    "TX:LSMM:INC_MANAGEMENT_OTHER",
    "TX:LSMM:INC_MANAGEMENT_POULTRY",
    "TX:LVST:DEC_ENTERIC_FERMENTATION",
}
_STRUCTURAL_NO_MAG = {
    "TX:LNDU:SET_WETLANDS_MINIMUM",
    "TX:WALI:INC_TREATMENT_INDUSTRIAL",
    "TX:WALI:INC_TREATMENT_RURAL",
    "TX:WALI:INC_TREATMENT_URBAN",
}


def _parse_magnitude(raw):
    if raw is None:
        return None
    if isinstance(raw, float) and math.isnan(raw):
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.lower() in ("nan", "none", ""):
            return None
        if raw.startswith("{"):
            try:
                return ast.literal_eval(raw)
            except Exception:
                return None
        try:
            return float(raw)
        except ValueError:
            return None
    return raw


def _fmt(val: float, code: str) -> str:
    if code in _ABSOLUTE_MAGNITUDE:
        return str(int(val)) if val == int(val) else str(val)
    return str(round(val * 100))


def _extract_display(code: str, raw) -> Optional[Union[str, tuple]]:
    """Same logic as extract_display_values() in v1."""
    mag = _parse_magnitude(raw)

    if code in _STRUCTURAL_NO_MAG:
        return "STRUCTURAL" if mag is not None else None
    if code in _STRUCTURAL_DICT:
        if mag is None:
            return None
        return "STRUCTURAL"

    if mag is None:
        return None

    if code == "TX:TRNS:SHIFT_MODE_REGIONAL":
        if isinstance(mag, dict):
            cats = mag.get("dict_categories_out", {})
            if isinstance(cats, dict):
                return (_fmt(cats.get("aviation", 0.1), code),
                        _fmt(cats.get("road_light", 0.2), code))
        return None

    if code == "TX:WASO:INC_ANAEROBIC_AND_COMPOST":
        if isinstance(mag, dict):
            return (_fmt(mag.get("magnitude_biogas",  0.475), code),
                    _fmt(mag.get("magnitude_compost", 0.475), code))
        return None

    if code in _DICT_KEY_MAP:
        key = _DICT_KEY_MAP[code]
        if isinstance(mag, dict):
            val = mag.get(key)
            return _fmt(val, code) if val is not None else None
        return _fmt(mag, code) if isinstance(mag, (int, float)) else None

    if isinstance(mag, (int, float)):
        return _fmt(mag, code)
    return None


# ── POLICY DESCRIPTIONS (static, no placeholders) ──────────────────────────

POLICY_DESCRIPTIONS: dict[str, str] = {
    # AGRC
    "TX:AGRC:DEC_CH4_RICE": (
        "Reduce methane emissions from rice cultivation through improved water "
        "management, fertilization, tillage, and residue management practices."
    ),
    "TX:AGRC:DEC_EXPORTS": (
        "Decrease agricultural exports relative to baseline levels by the "
        "final time period."
    ),
    "TX:AGRC:DEC_LOSSES_SUPPLY_CHAIN": (
        "Reduce pre-consumer food waste along the agricultural supply chain, "
        "lowering production demand for crops."
    ),
    "TX:AGRC:INC_CONSERVATION_AGRICULTURE": (
        "Expand conservation agriculture practices — minimum tillage, permanent "
        "soil cover, and species diversification — increasing crop residues "
        "retained on the field."
    ),
    "TX:AGRC:INC_PRODUCTIVITY": (
        "Apply a fractional increase to crop yield factors per hectare to "
        "improve land productivity."
    ),
    # CCSQ
    "TX:CCSQ:INC_CAPTURE": (
        "Deploy Direct Air Capture (DAC) technology to remove CO₂e directly "
        "from the atmosphere by 2050."
    ),
    # ENTC
    "TX:ENTC:DEC_LOSSES": (
        "Upgrade electrical transmission infrastructure to reduce grid "
        "transmission losses. The magnitude sets a final-period loss ceiling "
        "(final_value_ceiling): only regions whose baseline loss exceeds the "
        "target are affected; losses already below the ceiling remain unchanged. "
        "A minimum feasible loss floor (min_loss) applies regardless of target."
    ),
    "TX:ENTC:TARGET_CLEAN_HYDROGEN": (
        "Set a target share of hydrogen production sourced from green "
        "hydrogen (electrolysis) by the final time period."
    ),
    "TX:ENTC:TARGET_RENEWABLE_ELEC": (
        "Set a minimum share of electricity generation from renewable sources "
        "(geothermal, hydropower, ocean, solar, wind, and tidal) by 2050."
    ),
    # FGTV
    "TX:FGTV:DEC_LEAKS": (
        "Reduce fugitive methane emission factors across the production, "
        "distribution, and transmission of coal, natural gas, and oil "
        "through leak detection and repair (LDAR) programs."
    ),
    "TX:FGTV:INC_FLARE": (
        "Replace methane venting at orphan wells and mining facilities with "
        "flaring, converting CH₄ to the less potent CO₂."
    ),
    # INEN
    "TX:INEN:INC_EFFICIENCY_ENERGY": (
        "Increase the average energy efficiency of industrial production "
        "processes by fuel type to reduce overall energy demands."
    ),
    "TX:INEN:INC_EFFICIENCY_PRODUCTION": (
        "Reduce industrial end-use energy demand through modernization of "
        "production processes (kJ per tonne improvement)."
    ),
    "TX:INEN:SHIFT_FUEL_HEAT": (
        "Switch industrial low-temperature heat processes to electricity and "
        "high-temperature heat processes to electricity and hydrogen across "
        "cement, metals, chemicals, glass, paper, and lime sectors."
    ),
    # IPPU
    "TX:IPPU:DEC_CLINKER": (
        "Substitute clinker in cement production with supplementary "
        "cementitious materials (SCMs), LC3 cement, or equivalent processes. "
        
    ),
    "TX:IPPU:DEC_DEMAND": (
        "Reduce overall industrial production demand relative to the "
        "baseline by the final time period."
    ),
    "TX:IPPU:DEC_HFCS": (
        "Reduce IPPU emission factors for hydrofluorocarbons (HFCs) through "
        "improved refrigerant management, recovery, and phase-down."
    ),
    "TX:IPPU:DEC_N2O": (
        "Reduce IPPU emission factors for nitrous oxide (N₂O) generated "
        "as a byproduct of industrial processes."
    ),
    "TX:IPPU:DEC_OTHER_FCS": (
        "Reduce emission factors for other fluorinated compounds (SF₆, NF₃, "
        "HCFCs) generated as byproducts of industrial processes."
    ),
    "TX:IPPU:DEC_PFCS": (
        "Reduce IPPU emission factors for perfluorinated carbons (PFCs) "
        "generated as byproducts of industrial processes."
    ),
    # LNDU
    "TX:LNDU:DEC_DEFORESTATION": (
        "Halt deforestation by setting the primary forest self-transition "
        "probability to near one — primary forest is kept as primary forest "
        "rather than being converted to other land uses."
    ),
    "TX:LNDU:DEC_SOC_LOSS_PASTURES": (
        "Decrease soil organic carbon loss in grasslands by expanding "
        "sustainable grazing practices across a defined share of pasture area."
    ),
    "TX:LNDU:INC_REFORESTATION": (
        "Increase probability of land being converted to secondary forest, "
        "raising secondary forest area above baseline by the final time period."
    ),
    "TX:LNDU:INC_SILVOPASTURE": (
        "Convert a share of pasture to silvopasture (integrated tree–livestock "
        "systems), with livestock carrying capacity adjusted to compensate."
    ),
    # LSMM
    "TX:LSMM:INC_CAPTURE_BIOGAS": (
        "Increase the fraction of biogas captured at anaerobic livestock "
        "manure management facilities."
    ),
    "TX:LSMM:INC_MANAGEMENT_CATTLE_PIGS": (
        "Improve manure management for cattle (dairy and non-dairy) and pigs, "
        "directing treated manure to: ~59% anaerobic digestion, ~24% daily "
        "spreading, and ~12% composting by the final time period."
    ),
    "TX:LSMM:INC_MANAGEMENT_OTHER": (
        "Improve manure management for other livestock (buffalo, goats, horses, "
        "mules, sheep), directing treated manure to: ~48% anaerobic digestion, "
        "~24% composting, ~12% dry lot, and ~12% daily spreading."
    ),
    "TX:LSMM:INC_MANAGEMENT_POULTRY": (
        "Improve manure management for poultry (chickens), directing treated "
        "manure to: ~48% anaerobic digestion and ~48% dedicated poultry "
        "manure management pathways."
    ),
    # LVST
    "TX:LVST:DEC_ENTERIC_FERMENTATION": (
        "Reduce methane emissions from enteric fermentation in ruminant "
        "livestock through feed management and/or methagenic vaccines. "
        "Default reductions per species: 40% for buffalo, dairy cattle, and "
        "non-dairy cattle; 56% for goats and sheep."
    ),
    "TX:LVST:DEC_EXPORTS": (
        "Decrease exports of livestock and livestock products relative to "
        "baseline levels by the final time period."
    ),
    "TX:LVST:INC_PRODUCTIVITY": (
        "Increase livestock carrying capacity (average land productivity) "
        "above baseline levels by the final time period."
    ),
    # PFLO
    "TX:PFLO:INC_HEALTHIER_DIETS": (
        "Reduce average per-capita demand for cattle products through dietary "
        "shifts toward healthier, lower-emissions diets."
    ),
    "TX:PFLO:INC_IND_CCS": (
        "Deploy carbon capture and sequestration (CCS) across applicable "
        "industrial facilities excluding energy generation, with a default "
        "capture efficacy of 90%."
    ),
    # SCOE
    "TX:SCOE:DEC_DEMAND_HEAT": (
        "Reduce end-use heat energy demand in buildings through retrofitting, "
        "insulation improvements, and smart thermostats."
    ),
    "TX:SCOE:INC_EFFICIENCY_APPLIANCE": (
        "Reduce electricity demand in buildings by increasing the efficiency "
        "of electrified appliances and building energy systems."
    ),
    "TX:SCOE:SHIFT_FUEL_HEAT": (
        "Electrify building heat demand (space heating, water heating, and "
        "cooking) using heat pumps, electric stoves, and equivalent equipment."
    ),
    # SOIL
    "TX:SOIL:DEC_LIME_APPLIED": (
        "Decrease lime applied to agricultural soils through improved soil "
        "management and pH monitoring practices."
    ),
    "TX:SOIL:DEC_N_APPLIED": (
        "Decrease total nitrogen applied through precision fertilizer use "
        "without reducing crop yields."
    ),
    # TRDE
    "TX:TRDE:DEC_DEMAND": (
        "Reduce aggregate public and private transportation demand through "
        "urban planning, congestion pricing, and demand management policies."
    ),
    # TRNS
    "TX:TRNS:INC_EFFICIENCY_ELECTRIC": (
        "Improve the on-road efficiency of electric vehicles through "
        "regulation and technology standards."
    ),
    "TX:TRNS:INC_EFFICIENCY_NON_ELECTRIC": (
        "Improve the on-road efficiency of non-electric vehicles (fossil-fuel "
        "ICEs and other fuel types) through fuel standards and regulation."
    ),
    "TX:TRNS:INC_OCCUPANCY_LIGHT_DUTY": (
        "Increase the average occupancy rate of private light-duty vehicles "
        "through carpool lanes and incentive programs."
    ),
    "TX:TRNS:SHIFT_FUEL_LIGHT_DUTY": (
        "Set a minimum share of the light-duty vehicle fleet (private cars and "
        "light trucks) fueled by electricity"
    ),
    "TX:TRNS:SHIFT_FUEL_MARITIME": (
        "Shift maritime transportation demand away from fossil fuels toward "
        "hydrogen and electricity."
    ),
    "TX:TRNS:SHIFT_FUEL_MEDIUM_DUTY": (
        "Shift medium-duty vehicles (heavy freight, regional, and public "
        "transport) from fossil fuels to electricity and hydrogen."
    ),
    "TX:TRNS:SHIFT_FUEL_RAIL": (
        "Electrify rail transportation (freight and passenger) by setting "
        "a target share of rail demand fueled by electricity."
    ),
    "TX:TRNS:SHIFT_MODE_FREIGHT": (
        "Shift a share of aviation and road freight demand to freight rail "
        "by the final time period."
    ),
    "TX:TRNS:SHIFT_MODE_PASSENGER": (
        "Shift a share of passenger road demand to human-powered transport, "
        "powered bikes, and public transit."
    ),
    "TX:TRNS:SHIFT_MODE_REGIONAL": (
        "Shift shares of regional aviation and light-duty road demand to "
        "heavy-duty road transport."
    ),
    # TRWW
    "TX:TRWW:INC_CAPTURE_BIOGAS": (
        "Increase the fraction of biogas captured at anaerobic wastewater "
        "treatment facilities (advanced and secondary anaerobic)."
    ),
    "TX:TRWW:INC_COMPLIANCE_SEPTIC": (
        "Increase compliance with pumping schedule and maintenance requirements "
        "for rural septic tanks to preserve full emissions and health benefits."
    ),
    # WALI
    "TX:WALI:INC_TREATMENT_INDUSTRIAL": (
        "Restructure industrial wastewater treatment to default targets: 80% "
        "in advanced anaerobic facilities, 10% secondary aerobic, and 10% "
        "secondary anaerobic. Targets may be overridden via dict_magnitude."
    ),
    "TX:WALI:INC_TREATMENT_RURAL": (
        "Restructure rural wastewater treatment so that 100% is treated in "
        "septic tanks (default target). Target may be overridden via "
        "dict_magnitude."
    ),
    "TX:WALI:INC_TREATMENT_URBAN": (
        "Restructure urban wastewater treatment to default targets: 30% "
        "advanced anaerobic, 30% advanced aerobic, 20% secondary anaerobic, "
        "and 20% secondary aerobic. Targets may be overridden via dict_magnitude."
    ),
    # WASO
    "TX:WASO:DEC_CONSUMER_FOOD_WASTE": (
        "Reduce per-capita food waste generation at the consumer level."
    ),
    "TX:WASO:INC_ANAEROBIC_AND_COMPOST": (
        "Increase the fraction of organic waste (yard waste, food waste, and "
        "sludge) treated in anaerobic digesters and compost facilities."
    ),
    "TX:WASO:INC_CAPTURE_BIOGAS": (
        "Increase the fraction of biogas captured from landfills and "
        "anaerobic digesters."
    ),
    "TX:WASO:INC_ENERGY_FROM_BIOGAS": (
        "Increase the fraction of captured biogas converted to energy use."
    ),
    "TX:WASO:INC_ENERGY_FROM_INCINERATION": (
        "Increase the fraction of incinerated solid waste used for energy "
        "recovery (waste-to-energy)."
    ),
    "TX:WASO:INC_LANDFILLING": (
        "Increase the fraction of solid waste — not recycled, composted, or "
        "digested — directed to managed sanitary landfills (away from open "
        "dumping)."
    ),
    "TX:WASO:INC_RECYCLING": (
        "Increase the fraction of recyclable solid waste that is recycled, "
        "reducing landfill decomposition and virgin material production."
    ),
    # ENFU
    "TX:ENFU:ADJ_EXPORTS": (
        "Adjust fuel export volumes relative to baseline export levels "
        "by the final time period."
    ),
    # FRST
    "TX:FRST:INCREASE_SEQUESTRATION": (
        "Increase carbon sequestration in secondary forests to represent "
        "gains from sustainable biomass management and forest restoration."
    ),
    # LNDU — additional
    "TX:LNDU:PLUR": (
        "Apply a partial land use reallocation factor that redistributes "
        "a fraction of projected land use transitions across categories, "
        "smoothing extreme shifts in the land use transition matrix."
    ),
    "TX:LNDU:DEC_WETLAND_LOSS": (
        "Halt wetland loss by increasing the self-transition probability "
        "for wetlands to near one, preventing conversion to other land uses."
    ),
    "TX:LNDU:SET_WETLANDS_MINIMUM": (
        "Set a minimum bound on wetlands area using the land use "
        "quadratic programming framework, representing protected area "
        "targets or restoration commitments for wetland ecosystems."
    ),
    # SCOE — additional
    "TX:SCOE:INC_EFFICIENCY_HEAT": (
        "Increase the average efficiency of heat energy from biomass "
        "through adoption of clean cookstoves and improved heating systems."
    ),
}


# ── SHORT PATHWAY TEMPLATES (compact phrase, {} for value) ──────────────────

SHORT_TEMPLATES: dict[str, str] = {
    # AGRC
    "TX:AGRC:DEC_CH4_RICE":                "{}% reduction in methane emissions from rice cultivation",
    "TX:AGRC:DEC_EXPORTS":                 "{}% reduction in agricultural exports",
    "TX:AGRC:DEC_LOSSES_SUPPLY_CHAIN":     "{}% reduction in supply chain food losses",
    "TX:AGRC:INC_CONSERVATION_AGRICULTURE":"{}% of crop residues retained on field",
    "TX:AGRC:INC_PRODUCTIVITY":            "{}% increase in crop yields per hectare",
    # CCSQ
    "TX:CCSQ:INC_CAPTURE":                 "{} Mt CO₂e/yr removed via direct air capture",
    # ENTC
    "TX:ENTC:DEC_LOSSES":                  "Grid losses capped at {}% — applied only where current losses exceed this level",
    "TX:ENTC:TARGET_CLEAN_HYDROGEN":       "{}% of hydrogen from green electrolysis",
    "TX:ENTC:TARGET_RENEWABLE_ELEC":       "{}% renewable electricity share by 2050",
    # FGTV
    "TX:FGTV:DEC_LEAKS":                   "{}% reduction in methane leakage rates (oil, gas, coal sectors)",
    "TX:FGTV:INC_FLARE":                   "{}% of vented methane converted via flaring",
    # INEN
    "TX:INEN:INC_EFFICIENCY_ENERGY":       "{}% improvement in industrial energy efficiency",
    "TX:INEN:INC_EFFICIENCY_PRODUCTION":   "{}% reduction in energy needed per unit of industrial output",
    "TX:INEN:SHIFT_FUEL_HEAT":             "{}% of industrial heat processes switched to low-carbon fuels",
    # IPPU
    "TX:IPPU:DEC_CLINKER":                 "Clinker fraction capped at {}% of cement production",
    "TX:IPPU:DEC_DEMAND":                  "{}% reduction in industrial production demand",
    "TX:IPPU:DEC_HFCS":                    "{}% reduction in HFC emissions from industrial processes",
    "TX:IPPU:DEC_N2O":                     "{}% reduction in industrial N₂O emissions",
    "TX:IPPU:DEC_OTHER_FCS":               "{}% reduction in SF₆, NF₃, and other fluorinated compound emissions",
    "TX:IPPU:DEC_PFCS":                    "{}% reduction in PFC emissions from industrial processes",
    # LNDU
    "TX:LNDU:DEC_DEFORESTATION":           "{}% of primary forest remains forested each period (near-zero deforestation rate)",
    "TX:LNDU:DEC_SOC_LOSS_PASTURES":       "{}% of pasture under sustainable grazing",
    "TX:LNDU:INC_REFORESTATION":           "{}% increase in secondary forest area",
    "TX:LNDU:INC_SILVOPASTURE":            "{}% of pasture converted to silvopasture",
    # LSMM
    "TX:LSMM:INC_CAPTURE_BIOGAS":          "{}% of biogas captured at manure facilities",
    "TX:LSMM:INC_MANAGEMENT_CATTLE_PIGS":  "Manure treated (cattle, pigs): ~59% anaerobic digestion, ~24% daily spread, ~12% composting",
    "TX:LSMM:INC_MANAGEMENT_OTHER":        "Manure treated (buffalo, goats, horses, sheep): ~48% anaerobic digestion, ~24% composting, ~24% dry lot/daily spread",
    "TX:LSMM:INC_MANAGEMENT_POULTRY":      "Poultry manure (chickens): ~48% anaerobic digestion, ~48% dedicated poultry treatment",
    # LVST
    "TX:LVST:DEC_ENTERIC_FERMENTATION":    "Default rates: 40% reduction (buffalo, cattle), 56% reduction (goats, sheep)",
    "TX:LVST:DEC_EXPORTS":                 "{}% reduction in livestock exports",
    "TX:LVST:INC_PRODUCTIVITY":            "{}% increase in livestock productivity (animals per unit area)",
    # PFLO
    "TX:PFLO:INC_HEALTHIER_DIETS":         "{}% reduction in per-capita cattle consumption",
    "TX:PFLO:INC_IND_CCS":                 "Industrial CCS deployed with {}% capture efficacy per facility",
    # SCOE
    "TX:SCOE:DEC_DEMAND_HEAT":             "{}% reduction in building heat energy demand",
    "TX:SCOE:INC_EFFICIENCY_APPLIANCE":    "{}% reduction in building electricity demand",
    "TX:SCOE:SHIFT_FUEL_HEAT":             "{}% of building heat demand electrified",
    # SOIL
    "TX:SOIL:DEC_LIME_APPLIED":            "{}% reduction in lime applied to soils",
    "TX:SOIL:DEC_N_APPLIED":               "{}% reduction in fertilizer nitrogen applied",
    # TRDE
    "TX:TRDE:DEC_DEMAND":                  "{}% reduction in total transport demand",
    # TRNS
    "TX:TRNS:INC_EFFICIENCY_ELECTRIC":     "{}% improvement in electric vehicle fuel efficiency",
    "TX:TRNS:INC_EFFICIENCY_NON_ELECTRIC": "{}% improvement in non-electric vehicle fuel efficiency",
    "TX:TRNS:INC_OCCUPANCY_LIGHT_DUTY":    "{}% increase in average private vehicle occupancy",
    "TX:TRNS:SHIFT_FUEL_LIGHT_DUTY":       "{}% of light-duty vehicle fleet electrified",
    "TX:TRNS:SHIFT_FUEL_MARITIME":         "{}% of maritime transport shifted to low-carbon fuels",
    "TX:TRNS:SHIFT_FUEL_MEDIUM_DUTY":      "{}% of medium-duty fleet shifted to electricity or hydrogen",
    "TX:TRNS:SHIFT_FUEL_RAIL":             "{}% of rail transport electrified",
    "TX:TRNS:SHIFT_MODE_FREIGHT":          "{}% of road and air freight shifted to rail",
    "TX:TRNS:SHIFT_MODE_PASSENGER":        "{}% of private road trips shifted to public or active transport",
    "TX:TRNS:SHIFT_MODE_REGIONAL":         "{0}% of regional aviation, {1}% of light-duty road demand shifted to heavy road",
    # TRWW
    "TX:TRWW:INC_CAPTURE_BIOGAS":          "{}% of biogas captured at wastewater treatment facilities",
    "TX:TRWW:INC_COMPLIANCE_SEPTIC":       "{}% of septic tanks meeting maintenance compliance standards",
    # WALI (structural — no variable magnitude in any pathway)
    "TX:WALI:INC_TREATMENT_INDUSTRIAL":    "Target mix: 80% advanced anaerobic, 10% secondary aerobic, 10% secondary anaerobic",
    "TX:WALI:INC_TREATMENT_RURAL":         "Target mix: 100% treated in septic tanks",
    "TX:WALI:INC_TREATMENT_URBAN":         "Target mix: 30% advanced anaerobic, 30% advanced aerobic, 20% secondary anaerobic, 20% secondary aerobic",
    # WASO
    "TX:WASO:DEC_CONSUMER_FOOD_WASTE":     "{}% reduction in per-capita consumer food waste",
    "TX:WASO:INC_ANAEROBIC_AND_COMPOST":   "{0}% of organic waste to anaerobic digestion, {1}% to composting",
    "TX:WASO:INC_CAPTURE_BIOGAS":          "{}% of biogas captured from landfills and digesters",
    "TX:WASO:INC_ENERGY_FROM_BIOGAS":      "{}% of captured biogas converted to energy",
    "TX:WASO:INC_ENERGY_FROM_INCINERATION":"{}% of incinerated waste used for energy recovery",
    "TX:WASO:INC_LANDFILLING":             "{}% of residual solid waste directed to managed landfills",
    "TX:WASO:INC_RECYCLING":               "{}% of recyclable waste recycled",
    # ENFU
    "TX:ENFU:ADJ_EXPORTS":                 "{}× baseline fuel export volume",
    # FRST
    "TX:FRST:INCREASE_SEQUESTRATION":      "{}% increase in secondary forest carbon sequestration",
    # LNDU — additional
    "TX:LNDU:PLUR":                        "{}% land use reallocation factor applied",
    "TX:LNDU:DEC_WETLAND_LOSS":            "{}% wetland self-transition probability (near-zero wetland loss)",
    "TX:LNDU:SET_WETLANDS_MINIMUM":        "Minimum wetlands area bound enforced to protect and restore wetland ecosystems",
    # SCOE — additional
    "TX:SCOE:INC_EFFICIENCY_HEAT":         "{}% improvement in biomass heating efficiency (clean cookstoves)",
}

NO_POLICY = "No policy"


# ── PATHWAY CONFIGURATION ───────────────────────────────────────────────────
# Maps scenario pathways to their strategy names as they appear in the CSV
# column headers (magnitude_{column_suffix}).
#
#   column_suffix  – suffix used in the DataFrame column (magnitude_<suffix>)
#   label          – column header shown in the output table / Word document

from dataclasses import dataclass, field


@dataclass
class PathwayConfig:
    """
    Configuration for an arbitrary number of scenario pathways.

    Parameters
    ----------
    pathways : list of (column_suffix, label) tuples
        Each tuple maps a DataFrame column ``magnitude_{column_suffix}``
        to a display label used in table headers and the Word document.

    Example — Uganda
    ----------------
    cfg = PathwayConfig(pathways=[
        ("BAU",    "BAU"),
        ("NDC2020","NDC 2.0"),
        ("NDC_25", "NDC 2.0 (2025)"),
        ("HBLE",   "HBLE"),
    ])

    Example — Libya (3 pathways)
    ----------------------------
    cfg = PathwayConfig(pathways=[
        ("strategy_NDC",         "BAU"),
        ("strategy_LEP",         "Unconditional"),
        ("strategy_Conditional", "Conditional"),
    ])
    """
    pathways: list[tuple[str, str]] = field(default_factory=lambda: [
        ("strategy_NDC",         "BAU"),
        ("strategy_LEP",         "Unconditional"),
        ("strategy_Conditional", "Conditional"),
    ])

SUBSECTOR_LABELS = {
    "AGRC": "Agriculture – Crops",
    "CCSQ": "Carbon Capture & Sequestration",
    "ENTC": "Energy – Electricity",
    "FGTV": "Fugitive Emissions",
    "FRST": "Forestry",
    "INEN": "Industry – Energy",
    "IPPU": "Industry – Processes",
    "LNDU": "Land Use",
    "LSMM": "Livestock – Manure Management",
    "LVST": "Livestock",
    "PFLO": "Cross-Cutting",
    "SCOE": "Buildings",
    "SOIL": "Agriculture – Soils",
    "TRDE": "Transport – Demand",
    "TRNS": "Transport – Supply",
    "TRWW": "Transport – Wastewater",
    "WALI": "Wastewater",
    "WASO": "Waste – Solid",
    "ENFU": "Energy – Fuels",
}

# Subsector display order
SUBSECTOR_ORDER = [
    "AGRC", "SOIL", "LNDU", "FRST", "LVST", "LSMM",
    "ENTC", "FGTV", "ENFU",
    "INEN", "IPPU", "PFLO",
    "SCOE",
    "TRDE", "TRNS",
    "TRWW", "WALI",
    "WASO",
    "CCSQ",
]


def generate_policy_description(code: str) -> Optional[str]:
    return POLICY_DESCRIPTIONS.get(code)


def generate_short_text(code: str, raw_magnitude) -> str:
    """
    Return the short pathway cell text.
    Returns NO_POLICY string when the transformation is inactive for this pathway.
    """
    template = SHORT_TEMPLATES.get(code)
    if template is None:
        return NO_POLICY

    # Structural (no variable magnitude): template has no {}, return as-is
    if code in _STRUCTURAL_NO_MAG or code in _STRUCTURAL_DICT:
        mag = _parse_magnitude(raw_magnitude)
        if mag is None and code not in _STRUCTURAL_NO_MAG:
            return NO_POLICY
        return template  # fixed phrase

    display = _extract_display(code, raw_magnitude)
    if display is None:
        return NO_POLICY
    if display == "STRUCTURAL":
        return template
    if isinstance(display, tuple):
        return template.format(*display)
    return template.format(display)


def build_table_rows(
    df: pd.DataFrame,
    config: PathwayConfig = None,
) -> list[dict]:
    """
    Build all table rows sorted by SUBSECTOR_ORDER.

    Parameters
    ----------
    df : pd.DataFrame
        Transformations DataFrame produced by the existing pipeline.
        Must contain columns ``magnitude_{suffix}`` for each pathway
        defined in *config*.
    config : PathwayConfig, optional
        Pathway column suffixes and display labels.

    Returns
    -------
    list of dict with keys:
        subsector, subsector_label, transformation_name, transformation_code,
        policy_description, pathways (list of {label, text} dicts)
    """
    if config is None:
        config = PathwayConfig()

    rows = []
    for _, record in df.iterrows():
        code = record["transformation_code"]
        pw_entries = []
        for col_suffix, label in config.pathways:
            col = f"magnitude_{col_suffix}"
            pw_entries.append({
                "label": label,
                "text":  generate_short_text(code, record.get(col)),
            })
        rows.append({
            "subsector":           record["subsector"],
            "subsector_label":     SUBSECTOR_LABELS.get(record["subsector"], record["subsector"]),
            "transformation_name": record["transformation_name"],
            "transformation_code": code,
            "policy_description":  generate_policy_description(code) or "",
            "pathways":            pw_entries,
        })

    order_map = {s: i for i, s in enumerate(SUBSECTOR_ORDER)}
    rows.sort(key=lambda r: (order_map.get(r["subsector"], 99), r["transformation_name"]))
    return rows
