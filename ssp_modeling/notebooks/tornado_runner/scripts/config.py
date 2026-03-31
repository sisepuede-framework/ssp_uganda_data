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
RUN_ID            = "sisepuede_summary_results_run_sisepuede_run_2026-03-30T03;04;59.566941/"
RUN_ID_OUTPUT_DIR = RUN_OUTPUT_DIR / RUN_ID

# ── Model time range ──────────────────────────────────────────────────────────
YEAR_START = 2015
YEAR_END   = 2070

# ── Post-processing parameters ────────────────────────────────────────────────
ISO_CODE3    = "UGA"
YEAR_REF     = 2019
REGION       = "uganda"
TARGETS_PATH = SSP_MODELING_DIR / "output_postprocessing/data/LULUCF/emission_targets_uganda_2019_LULUCF_updated.csv"
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
    6500, 6501, 6502, 6503, 6504, 6505, 6506, 6507, 6508, 6509,
    6510, 6511, 6512, 6513, 6514, 6515, 6516, 6517, 6518, 6519,
    6520, 6521, 6522, 6523, 6524, 6525, 6526, 6527, 6528, 6529,
    6530, 6531, 6532, 6533, 6534, 6535, 6536, 6537, 6538, 6539,
    6540, 6541, 6542, 6543, 6544, 6545, 6546, 6547, 6548, 6549,
    6550, 6551, 6552, 6553, 6554, 6555, 6556, 6557, 6558
]
