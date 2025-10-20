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
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2025-10-19T21;10;17.921062/"
output.file <- "WIDE_INPUTS_OUTPUTS.csv"

region <- "uganda" 
iso_code3 <- "UGA"

for (yr in c(2020, 2022)) {
  
  # set year_ref for this run
  year_ref <- yr
  message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))
  
  # run the original steps (they read year_ref from the env)
  source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')
  source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_uganda.r')
}


# Combine 2020 & 2022 runs
source('ssp_modeling/output_postprocessing/scr/combine_20_22_replace_ssp_raw_sectors.r')


source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')

# Levers table
source('ssp_modeling/output_postprocessing/scr/levers_table/#create levers table.r')

# Jobs table
source('ssp_modeling/output_postprocessing/scr/levers_table/#create jobs table.r')