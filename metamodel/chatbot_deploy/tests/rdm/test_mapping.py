"""
Tests for backend/rdm/mapping: the group → output mapping.

Test 1 — summarise_rho on synthetic data: largest |rho|, its year and its sign.
Test 2 — structural links: lever 35 (light-duty fuel shift) links to electric light-duty
         vehicle-km in model_output.
Test 3 — the built map for the active run (needs the cached sample; skipped otherwise):
         every row has a known status and kind; emissions come from decomposed_emissions and
         variables from model_output; lever 35 ↔ electric light-duty vehicle-km is found by
         both sources with rho > 0.5 (checked by hand on 2026-10-06: share = 50% + 21.9 pts × L).
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

_CHATBOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_CHATBOT_DIR))

from backend.rdm.mapping import build_mapping as bm  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402

RUN = get_run()
EV_VKM = "vehicle_distance_traveled_trns_road_light_electricity"


def test_summarise_rho_picks_the_largest_effect():
    rho = pd.DataFrame({"group_id": [1, 1, 1], "output_field": ["y"] * 3,
                        "year": [2025, 2050, 2070], "rho": [0.05, -0.4, 0.2]})
    s = bm.summarise_rho(rho, (2025, 2050, 2070)).iloc[0]
    assert s.rho_max_abs == pytest.approx(0.4)
    assert s.rho_year == 2050 and s.rho_sign == -1


def test_structural_links_find_lever_35_variable():
    links = bm.structural_links(RUN, emission_fields=set(), variable_fields={EV_VKM})
    assert (links.group_id == 35).any()


def test_built_map_for_the_active_run():
    path = bm.MAPS_DIR / f"{RUN.name}.csv"
    if not path.exists():
        pytest.skip("No map built yet: python -m backend.rdm.mapping.build_mapping")
    m = pd.read_csv(path)
    assert set(m.status) <= {"both", "empirical only", "structural only", "structural, output constant in runs"}
    assert set(m.output_kind) == {"emission", "variable"}
    assert set(m.loc[m.output_kind == "emission", "source_table"]) == {RUN.table("emissions")}
    assert set(m.loc[m.output_kind == "variable", "source_table"]) == {RUN.table("variables")}
    row = m[(m.group_id == 35) & (m.output_field == EV_VKM)].iloc[0]
    assert row.status == "both" and row.rho_max_abs > 0.5 and row.rho_sign == 1
