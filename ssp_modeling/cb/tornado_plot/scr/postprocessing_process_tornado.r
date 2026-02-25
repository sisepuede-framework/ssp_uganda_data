#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(dplyr)
library(ggplot2)

rm(list=ls())

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194/"
output.file <- "WIDE_INPUTS_OUTPUTS.csv"

region <- "uganda" 
iso_code3 <- "UGA"


# set year_ref for this run
year_ref <- 2019
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/LULUCF/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/LULUCF/data_prep_new_mapping_uganda.r')
source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')

# Levers table
source('ssp_modeling/output_postprocessing/scr/levers_table/#create levers table.r')

# Jobs table
source('ssp_modeling/output_postprocessing/scr/levers_table/#create jobs table.r')