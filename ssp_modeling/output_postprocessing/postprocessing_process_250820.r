#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(mFilter)
library(ggplot2)

rm(list=ls())

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2025-08-27T20;12;53.345956/"
output.file <- "WIDE_INPUTS_OUTPUTS.csv"

region <- "uganda" 
iso_code3 <- "UGA"

year_ref <- 2022

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_uganda.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')
