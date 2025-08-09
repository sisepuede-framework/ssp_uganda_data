#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)

rm(list=ls())

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_run_2025-08-08T19;27;48.212333/"
output.file <-"sisepuede_run_2025-08-08T19;27;48.212333.csv"

region <- "uganda" 
iso_code3 <- "UGA"

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_uganda.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')