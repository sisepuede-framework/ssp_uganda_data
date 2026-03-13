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
run <- 'sisepuede_run_2026-03-10t13;27;53.264959'

dir.output  <- paste0("ssp_modeling/ssp_run_output/",run,"/")
output.file <- "c585e7e9-e32f-4131-999b-ee7fc5ec014e.csv"

att <- "ATTRIBUTE_STRATEGY.csv"


sttrategy_ids <- c(0,6004,6008,6009) 

# load full data
nwr <- fread(paste0(dir.output, output.file))
dim(nwr)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
dim(att)
att <- att[att$strategy_id %in% sttrategy_ids, ]
dim(att)
head(att)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(atts)
atts <- atts[atts$strategy_id %in% sttrategy_ids, ]
dim(atts)
head(atts)


nwr <- merge(nwr,att,by="primary_id")
dim(nwr)

#filter for the strategies we want to include in the nwr
nwr <- nwr[nwr$strategy_id %in% sttrategy_ids, ]

dim(nwr)
nwr[, c('design_id','strategy_id','future_id') := NULL]
dim(nwr)

#ouputfile
if (!dir.exists(paste0(dir.output, "/nwr/"))) {
    dir.create(paste0(dir.output, "/nwr/"), recursive = TRUE, showWarnings = FALSE)
}

dir.output.nwr  <- paste0(dir.output,"/nwr/")

fwrite(nwr, paste0(dir.output.nwr, "nwr_data_raw.csv"))
fwrite(att, paste0(dir.output.nwr, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output.nwr, "ATTRIBUTE_STRATEGY.csv"))


################################################################################

#ouputfile
dir.output  <-dir.output.nwr
output.file <- "nwr_data_raw.csv"

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