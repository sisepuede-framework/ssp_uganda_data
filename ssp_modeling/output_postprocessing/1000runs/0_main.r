#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(parallel)


rm(list=ls())


run <- "ssp_modeling/ssp_run_output/sisepuede_run_2025-11-12t22;19;28.194097/"
file.name <- "a6f74804-3b5e-431d-8be4-e5a57efb4dfa.csv"

source('ssp_modeling/output_postprocessing/1000runs/parse_experiment_in_individual_files.r')

source('ssp_modeling/output_postprocessing/1000runs/run_script_baseline_run_new_1000ensamble.r')