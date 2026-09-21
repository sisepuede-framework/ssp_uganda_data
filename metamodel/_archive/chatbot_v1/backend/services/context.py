"""
Country Context Service
========================
Provides formatted, human-readable snapshots of Uganda's baseline conditions
drawn from the SISEPUEDE model inputs (primary_id=0, BAU baseline).

The baseline row is loaded from S3 once at module import and cached.
If the S3 fetch fails at startup (e.g. auth not configured), the module
initialises with _BASELINE_ROW=None and get_country_context() returns a
graceful fallback message instead of raising.

Public API
----------
get_country_context(topic: str) -> str
    Return a formatted string describing Uganda's baseline for the given topic.

    Supported topics:
        "energy_mix"   — electricity generation technology fractions
        "gdp"          — GDP (billion USD) at 2025, 2030, 2040, 2050
        "population"   — rural/urban population at 2025, 2030, 2040, 2050
        "agriculture"  — key crop areas (ha) and livestock head counts
        "transport"    — passenger and freight mode share fractions
"""

import logging

from backend.services.s3_lookup import get_model_inputs_row

logger = logging.getLogger(__name__)

# ── Time-period helpers ───────────────────────────────────────────────────────
# SISEPUEDE time_period 0 = 2015, so tp = year - 2015.
_TP = {2025: 10, 2030: 15, 2040: 25, 2050: 35}
_SNAPSHOT_YEARS = [2025, 2030, 2040, 2050]


def _tp(year: int) -> int:
    return year - 2015


def _val(row: dict, col: str, tp: int):
    """Extract scalar value at time_period tp from the baseline row dict."""
    values = row.get(col)
    if values is None or tp >= len(values):
        return None
    return values[tp]


# ── Module-level baseline load ────────────────────────────────────────────────

_BASELINE_ROW: dict | None = None
_LOAD_ERROR: str | None = None

try:
    _BASELINE_ROW = get_model_inputs_row(primary_id=0)
    logger.info(
        "context.py: baseline row loaded (primary_id=0, %d columns)",
        len(_BASELINE_ROW),
    )
except Exception as exc:  # noqa: BLE001
    _LOAD_ERROR = str(exc)
    logger.warning(
        "context.py: could not load baseline row at startup — "
        "get_country_context() will return fallback text. Error: %s",
        exc,
    )


# ── Topic formatters ──────────────────────────────────────────────────────────

def _fmt_energy_mix(row: dict) -> str:
    """Electricity generation technology min-share fractions at 2025 and 2050."""
    # These are minimum production share targets per technology in the baseline.
    # Values are fractions (0–1). Only include power-plant (pp_) technologies;
    # hydrogen fuel-production (fp_) fractions are less policy-relevant here.
    techs = {
        "hydropower":        "nemomod_entc_frac_min_share_production_pp_hydropower",
        "solar":             "nemomod_entc_frac_min_share_production_pp_solar",
        "wind":              "nemomod_entc_frac_min_share_production_pp_wind",
        "biomass":           "nemomod_entc_frac_min_share_production_pp_biomass",
        "geothermal":        "nemomod_entc_frac_min_share_production_pp_geothermal",
        "oil":               "nemomod_entc_frac_min_share_production_pp_oil",
        "gas":               "nemomod_entc_frac_min_share_production_pp_gas",
        "biogas":            "nemomod_entc_frac_min_share_production_pp_biogas",
        "nuclear":           "nemomod_entc_frac_min_share_production_pp_nuclear",
        "coal":              "nemomod_entc_frac_min_share_production_pp_coal",
    }

    lines = [
        "Uganda Baseline — Electricity Generation Mix (minimum production share fractions):",
        f"{'Technology':<16}  {'2025':>8}  {'2050':>8}",
        "-" * 38,
    ]
    for label, col in techs.items():
        v25 = _val(row, col, _tp(2025))
        v50 = _val(row, col, _tp(2050))
        if v25 is None and v50 is None:
            continue
        v25_s = f"{v25:.1%}" if v25 is not None else "n/a"
        v50_s = f"{v50:.1%}" if v50 is not None else "n/a"
        lines.append(f"{label:<16}  {v25_s:>8}  {v50_s:>8}")

    lines.append(
        "\nNote: Values are minimum share mandates (floor constraints), not actual "
        "generation shares. Hydropower dominates Uganda's current grid."
    )
    return "\n".join(lines)


def _fmt_gdp(row: dict) -> str:
    """GDP trajectory in billion USD at key years."""
    col = "gdp_mmm_usd"
    lines = [
        "Uganda Baseline — GDP Trajectory (billion USD):",
        f"{'Year':<8}  {'GDP (B USD)':>14}",
        "-" * 24,
    ]
    for yr in _SNAPSHOT_YEARS:
        v = _val(row, col, _tp(yr))
        s = f"{v:,.1f}" if v is not None else "n/a"
        lines.append(f"{yr:<8}  {s:>14}")
    lines.append(
        "\nNote: Values reflect the SSP-based baseline projection used in SISEPUEDE. "
        "GDP in purchasing-power parity terms."
    )
    return "\n".join(lines)


def _fmt_population(row: dict) -> str:
    """Rural and urban population at key years."""
    lines = [
        "Uganda Baseline — Population (persons):",
        f"{'Year':<8}  {'Rural':>14}  {'Urban':>14}  {'Total':>14}",
        "-" * 56,
    ]
    for yr in _SNAPSHOT_YEARS:
        tp = _tp(yr)
        rural = _val(row, "population_gnrl_rural", tp)
        urban = _val(row, "population_gnrl_urban", tp)
        total = _val(row, "population_gnrl_total", tp)
        rural_s = f"{rural:,.0f}" if rural is not None else "n/a"
        urban_s = f"{urban:,.0f}" if urban is not None else "n/a"
        total_s = f"{total:,.0f}" if total is not None else "n/a"
        lines.append(f"{yr:<8}  {rural_s:>14}  {urban_s:>14}  {total_s:>14}")
    lines.append(
        "\nNote: Urban share rises significantly over the projection period "
        "as Uganda continues rapid urbanisation."
    )
    return "\n".join(lines)


def _fmt_agriculture(row: dict) -> str:
    """Key crop areas (hectares) and livestock head counts at 2025."""
    tp25 = _tp(2025)
    tp50 = _tp(2050)

    # Crop areas — only show economically significant crops
    crop_cols = {
        "Cereals":              "area_agrc_crops_cereals",
        "Tubers":               "area_agrc_crops_tubers",
        "Other annual crops":   "area_agrc_crops_other_annual",
        "Fruits":               "area_agrc_crops_fruits",
        "Pulses":               "area_agrc_crops_pulses",
        "Beverages & spices":   "area_agrc_crops_bevs_and_spices",
        "Nuts":                 "area_agrc_crops_nuts",
        "Sugar cane":           "area_agrc_crops_sugar_cane",
        "Rice":                 "area_agrc_crops_rice",
        "Vegetables & vines":   "area_agrc_crops_vegetables_and_vines",
    }

    # Livestock head counts (animals)
    lvst_cols = {
        "Cattle (non-dairy)":   "pop_lvst_cattle_nondairy",
        "Cattle (dairy)":       "pop_lvst_cattle_dairy",
        "Chickens":             "pop_lvst_chickens",
        "Goats":                "pop_lvst_goats",
        "Pigs":                 "pop_lvst_pigs",
        "Sheep":                "pop_lvst_sheep",
    }

    lines = [
        "Uganda Baseline — Agriculture Sector:",
        "",
        "Crop area (hectares):",
        f"  {'Crop':<24}  {'2025':>12}  {'2050':>12}",
        "  " + "-" * 52,
    ]
    for label, col in crop_cols.items():
        v25 = _val(row, col, tp25)
        v50 = _val(row, col, tp50)
        if v25 is None and v50 is None:
            continue
        v25_s = f"{v25:,.0f}" if v25 is not None else "n/a"
        v50_s = f"{v50:,.0f}" if v50 is not None else "n/a"
        lines.append(f"  {label:<24}  {v25_s:>12}  {v50_s:>12}")

    lines += [
        "",
        "Livestock head counts (animals):",
        f"  {'Species':<24}  {'2025':>12}  {'2050':>12}",
        "  " + "-" * 52,
    ]
    for label, col in lvst_cols.items():
        v25 = _val(row, col, tp25)
        v50 = _val(row, col, tp50)
        if v25 is None and v50 is None:
            continue
        v25_s = f"{v25:,.0f}" if v25 is not None else "n/a"
        v50_s = f"{v50:,.0f}" if v50 is not None else "n/a"
        lines.append(f"  {label:<24}  {v25_s:>12}  {v50_s:>12}")

    lines.append(
        "\nNote: Crop area and livestock counts reflect the SSP-based baseline. "
        "Agriculture is a major emission source via enteric fermentation and "
        "land-use change."
    )
    return "\n".join(lines)


def _fmt_transport(row: dict) -> str:
    """Passenger and freight transport mode share fractions at 2025 and 2050."""
    # Passenger-km demand mode shares (private + public local trips)
    pkm_pp = {
        "Human-powered":       "frac_trns_pkm_dem_private_and_public_human_powered",
        "Powered bikes":        "frac_trns_pkm_dem_private_and_public_powered_bikes",
        "Public transit":       "frac_trns_pkm_dem_private_and_public_public",
        "Road (light vehicle)": "frac_trns_pkm_dem_private_and_public_road_light",
        "Water-borne":          "frac_trns_pkm_dem_private_and_public_water_borne",
    }

    # Passenger-km demand shares for regional trips
    pkm_reg = {
        "Aviation (regional)":  "frac_trns_pkm_dem_regional_aviation",
        "Rail (passenger)":     "frac_trns_pkm_dem_regional_rail_passenger",
        "Road heavy (regional)":"frac_trns_pkm_dem_regional_road_heavy_regional",
        "Road light (regional)":"frac_trns_pkm_dem_regional_road_light",
        "Water-borne (reg.)":   "frac_trns_pkm_dem_regional_water_borne",
    }

    # Freight tonne-km demand shares
    mtkm = {
        "Aviation (freight)":   "frac_trns_mtkm_dem_freight_aviation",
        "Rail (freight)":       "frac_trns_mtkm_dem_freight_rail_freight",
        "Road heavy (freight)": "frac_trns_mtkm_dem_freight_road_heavy_freight",
        "Water-borne (freight)":"frac_trns_mtkm_dem_freight_water_borne",
    }

    tp25 = _tp(2025)
    tp50 = _tp(2050)

    def section(title: str, cols: dict) -> list[str]:
        out = [f"\n{title}:", f"  {'Mode':<26}  {'2025':>8}  {'2050':>8}", "  " + "-" * 46]
        for label, col in cols.items():
            v25 = _val(row, col, tp25)
            v50 = _val(row, col, tp50)
            if v25 is None and v50 is None:
                continue
            v25_s = f"{v25:.1%}" if v25 is not None else "n/a"
            v50_s = f"{v50:.1%}" if v50 is not None else "n/a"
            out.append(f"  {label:<26}  {v25_s:>8}  {v50_s:>8}")
        return out

    lines = ["Uganda Baseline — Transport Mode Shares:"]
    lines += section("Passenger — Local (pkm demand share)", pkm_pp)
    lines += section("Passenger — Regional (pkm demand share)", pkm_reg)
    lines += section("Freight (tonne-km demand share)", mtkm)
    lines.append(
        "\nNote: Mode shares represent the fraction of total travel demand met by "
        "each mode. Motorisation is low in 2025 but rises under baseline projections."
    )
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

_SUPPORTED_TOPICS = {"energy_mix", "gdp", "population", "agriculture", "transport"}


def get_country_context(topic: str) -> str:
    """
    Return a formatted human-readable string describing Uganda's baseline
    conditions for the requested topic.

    Parameters
    ----------
    topic : str
        One of: "energy_mix", "gdp", "population", "agriculture", "transport"

    Returns
    -------
    str
        Multi-line formatted text Claude can include directly in a response.
        Returns a fallback message if the baseline row is unavailable or the
        topic is unrecognised.
    """
    if topic not in _SUPPORTED_TOPICS:
        return (
            f"Unknown context topic '{topic}'. "
            f"Supported topics: {', '.join(sorted(_SUPPORTED_TOPICS))}."
        )

    if _BASELINE_ROW is None:
        return (
            f"Uganda baseline context for '{topic}' is currently unavailable "
            f"(S3 baseline row could not be loaded at startup: {_LOAD_ERROR})."
        )

    formatters = {
        "energy_mix":  _fmt_energy_mix,
        "gdp":         _fmt_gdp,
        "population":  _fmt_population,
        "agriculture": _fmt_agriculture,
        "transport":   _fmt_transport,
    }

    try:
        return formatters[topic](_BASELINE_ROW)
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_country_context('%s') failed: %s", topic, exc)
        return (
            f"Could not format context for topic '{topic}': {exc}. "
            "The baseline row may be missing expected columns."
        )
