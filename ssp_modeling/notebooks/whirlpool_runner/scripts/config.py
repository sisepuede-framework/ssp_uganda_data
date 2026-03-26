"""
config.py
---------
All configuration constants and derived paths for the whirlpool experiment.
Edit RUN_ID and the experiment parameters here; everything else is derived.
"""

import pathlib

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # whirlpool_runner/
NOTEBOOKS_DIR     = RUNNER_DIR.parent                       # notebooks/
SSP_MODELING_DIR  = NOTEBOOKS_DIR.parent                    # ssp_modeling/
PROJECT_DIR       = SSP_MODELING_DIR.parent                 # repo root

DATA_DIR          = SSP_MODELING_DIR / "input_data"
RUN_OUTPUT_DIR    = SSP_MODELING_DIR / "ssp_run_output"

# ── Run to analyze ────────────────────────────────────────────────────────────
RUN_ID            = "sisepuede_run_2026-03-10t13;27;53.264959/"
RUN_ID_OUTPUT_DIR = RUN_OUTPUT_DIR / RUN_ID

# ── Model time range ──────────────────────────────────────────────────────────
YEAR_START = 2015
YEAR_END   = 2070

# ── Post-processing parameters ────────────────────────────────────────────────
ISO_CODE3    = "UGA"
YEAR_REF     = 2019
REGION       = "uganda"
TARGETS_PATH = SSP_MODELING_DIR / "output_postprocessing/data/LULUCF/emission_targets_uganda_2019_LULUCF.csv"
INVENT_DIR   = SSP_MODELING_DIR / "output_postprocessing/data/LULUCF"

# Output paths for intermediate results
OUTPUT_DECOMPOSED  = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_whirlpool.csv"
OUTPUT_CB_DATA     = RUN_ID_OUTPUT_DIR / "cost_benefits_data_whirlpool.csv"
OUTPUT_MAC         = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_whirlpool.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits/cb_cost_factors/cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits/out"

# ── Strategy codes ────────────────────────────────────────────────────────────
STRATEGY_CODE_BASE      = "BASE"        # used by CostBenefits as reference
STRATEGY_CODE_PFLO_HBLE = "PFLO:HBLE"  # used as emissions / cost baseline in MAC

# ── Primary IDs to analyze ────────────────────────────────────────────────────
PRIMARY_IDS_FILTER = [
    0, 700070,
    1350135, 1360136, 1370137, 1380138, 1390139, 1400140,
    1410141, 1420142, 1430143, 1440144, 1450145, 1460146, 1470147,
    1480148, 1490149, 1500150, 1510151, 1520152, 1530153, 1540154,
    1550155, 1560156, 1570157, 1580158, 1590159, 1600160, 1610161,
    1620162, 1630163, 1640164, 1650165, 1660166, 1670167, 1680168,
    1690169, 1700170, 1710171, 1720172, 1730173, 1740174, 1750175,
    1760176, 1770177, 1780178, 1790179, 1800180, 1810181, 1820182,
    1830183, 1840184, 1850185, 1860186, 1870187, 1880188, 1890189,
    1900190, 1910191, 1920192, 1930193,
]
