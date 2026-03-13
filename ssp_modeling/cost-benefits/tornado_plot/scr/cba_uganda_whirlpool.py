# Load packages
from costs_benefits_ssp.cb_calculate import CostBenefits
import pandas as pd
import os
import pathlib
import numpy as np

# Define paths
SSP_PATH = pathlib.Path(os.getcwd())
SSP_RUN  = os.path.join(SSP_PATH, "ssp_modeling/ssp_run_output/sisepuede_run_2026-03-10t13;27;53.264959/whirlpool")

CB_DEFAULT_DEFINITION_PATH = os.path.join(SSP_PATH,"ssp_modeling/cost-benefits/cb_cost_factors")
CB_DEFAULT_DEFINITION_FILE_PATH = os.path.join(CB_DEFAULT_DEFINITION_PATH, "cb_config_params.xlsx")
CB_OUTPUT = os.path.join(SSP_PATH,"ssp_modeling/cost-benefits/tornado_plot/data/input/whirlpool")

# Load data
ssp_data = pd.read_csv(os.path.join(SSP_RUN, "uganda.csv"))
att_primary = pd.read_csv(os.path.join(SSP_RUN,"ATTRIBUTE_PRIMARY.csv"))
att_strategy = pd.read_csv(os.path.join(SSP_RUN,"ATTRIBUTE_STRATEGY.csv"))
strategy_code_base = "BASE"

# Instantiate CostBenefits object
cb = CostBenefits(ssp_data, att_primary, att_strategy, strategy_code_base)

# The export_db_to_excel method saves the initial configuration of the cost tables to an excel file.
# Each sheet represents a table in the cost and benefit program database.
# If the Excel file name is not given, the file will be saved with the default name cb_config_params.xlsx on the current python session.

#cb.export_db_to_excel(CB_DEFAULT_DEFINITION_FILE_PATH)

# Once that the excel file has been updated, we can reload it in order to update the cost factors database
cb.load_cb_parameters(CB_DEFAULT_DEFINITION_FILE_PATH)

# Compute System Costs
results_system = cb.compute_system_cost_for_all_strategies()

# Compute Technical Costs
results_tx = cb.compute_technical_cost_for_all_strategies()

# Combine results
results_all = pd.concat([results_system, results_tx], ignore_index = True)

#-------------POST PROCESS SIMULATION RESULTS---------------
# Post process interactions among strategies that affect the same variables
results_all_pp = cb.cb_process_interactions(results_all)

# SHIFT any stray costs incurred from 2015 to 2025 to 2025 and 2035
results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)

# Save the results
results_all_pp_shifted.to_csv(os.path.join(CB_OUTPUT, "cba_results_ssp_modeling_whirlpool.csv"), index = False)