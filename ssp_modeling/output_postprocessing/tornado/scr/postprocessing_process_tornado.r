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
dir.output  <- "ssp_modeling/output_postprocessing/tornado/ssp_run_output/sisepuede_run_2025-11-12t22;19;28.194097/"
output.file <- "737e73e0-254e-45e0-be1c-60584026fe0c.csv"

region <- "uganda" 
iso_code3 <- "UGA"


# set year_ref for this run
year_ref <- 2019


# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/tornado/scr/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/tornado/scr/data_prep_new_mapping_uganda.r')