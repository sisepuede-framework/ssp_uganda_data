"""
config.py  (tornado)
---------------------
All configuration constants for the tornado experiment.
Edit RUN_ID and experiment parameters here; everything else is derived.

Key differences vs whirlpool:
  - PRIMARY_IDS_FILTER  : tornado strategy set (0, 760076 … 1340134)
  - CB_CONFIG_PATH      : cb_cost_factors/ subfolder
  - STRATEGY_CODE_BASE  : 'BASE'  (used as emission AND cost baseline in MAC)
  - Output suffix       : _tornado
"""

import pathlib

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # tornado_runner/
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
OUTPUT_DECOMPOSED      = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_tornado.csv"
OUTPUT_CB_DATA         = RUN_ID_OUTPUT_DIR / "cost_benefits_data_tornado.csv"
OUTPUT_MAC             = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_tornado.csv"

# ── Tableau output ─────────────────────────────────────────────────────────────
TABLEAU_DIR            = SSP_MODELING_DIR / "Tableau/data"
OUTPUT_TABLEAU_TORNADO = TABLEAU_DIR / "tableau_tornado.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
# Tornado uses cb_cost_factors/ (different subfolder than whirlpool)
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits/cb_cost_factors/cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits/out"

# ── Strategy codes ────────────────────────────────────────────────────────────
# In tornado, 'BASE' serves as the reference for both emissions AND costs in MAC
STRATEGY_CODE_BASE     = "BASE"
STRATEGY_CODE_BASELINE = "BASE"   # alias used by mac_pipeline

# ── Primary IDs to analyze (tornado strategy set) ─────────────────────────────
PRIMARY_IDS_FILTER = [
    0,
    760076,  770077,  780078,  790079,  800080,  810081,  820082,  830083,
    840084,  850085,  860086,  870087,  880088,  890089,  900090,  910091,
    920092,  930093,  940094,  950095,  960096,  970097,  980098,  990099,
    1000100, 1010101, 1020102, 1030103, 1040104, 1050105, 1060106,
    1070107, 1080108, 1090109, 1100110, 1110111, 1120112, 1130113,
    1140114, 1150115, 1160116, 1170117, 1180118, 1190119, 1200120,
    1210121, 1220122, 1230123, 1240124, 1250125, 1260126, 1270127,
    1280128, 1290129, 1300130, 1310131, 1320132, 1330133, 1340134,
]
