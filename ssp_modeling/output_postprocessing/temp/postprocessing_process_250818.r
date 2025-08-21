#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(mFilter)
library(ggplot2)

rm(list=ls())

setwd('/Users/fabianfuentes/git/ssp_uganda_data/')

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2025-08-19T15;26;17.115357/"
output.file <- "WIDE_INPUTS_OUTPUTS.csv"

region <- "uganda" 
iso_code3 <- "UGA"

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_uganda.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')
