#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)

rm(list=ls())

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_run_2025-07-29T13;04;41.898821/"
output.file <-"sisepuede_run_2025-07-29T13;04;41.898821.csv"

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_bulgaria.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')