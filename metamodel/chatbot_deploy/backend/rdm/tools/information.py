"""
Information tool: model_network navigates the SISEPUEDE network read from the model code (tools/network.py).
Relations in every arm; values only in the v1 arms.

This module keeps the shared helpers other modules use (the crosswalk, units read from field names, the
lever → output mapping measured in the runs) and hands model_network to tools/network.py.
"""

import json
from functools import lru_cache

import pandas as pd

from backend.rdm.mapping.build_mapping import MAPS_DIR
from backend.rdm.runs import Run
from backend.rdm.tools.common import groups  # noqa: F401  (used as information.groups)

from backend.rdm.tools.network import ARMS, VERSIONS  # noqa: F401  (the arms, defined with the tool)

EXCLUDED_STATUS = "structural, output constant in runs"


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


# ── model_network ────────────────────────────────────────────────────────────

def model_network(run: Run, node, year, version: str = "v1", lever=None, uncertainty=None, third=None) -> dict:
    """One node of the SISEPUEDE network, what it is computed from and what it is used to compute; values in the
    v1 arms. See tools/network.py."""
    from backend.rdm.tools.network import model_network as navigate
    return navigate(run, node, year, version, lever, uncertainty, third)
