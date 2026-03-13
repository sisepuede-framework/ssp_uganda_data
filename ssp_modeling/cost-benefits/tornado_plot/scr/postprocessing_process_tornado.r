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


sttrategy_ids <- c(0,6500,6501,6502,6503,6504,6505,6506,6507,6508,6509,6510,6511,6512,6513,6514,6515,6516,6517,6518,6519,6520,6521,
6522,6523,6524,6525,6526,6527,6528,6529,6530,6531,6532,6533,6534,6535,6536,6537,6538,6539,6540,6541,6542,6543,6544,6545,6546,6547,
6548,6549,6550,6551,6552,6553,6554,6555,6556,6557,6558)

# load full data
tornado <- fread(paste0(dir.output, output.file))
dim(tornado)

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


tornado <- merge(tornado,att,by="primary_id")
dim(tornado)

#filter for the strategies we want to include in the tornado
tornado <- tornado[tornado$strategy_id %in% sttrategy_ids, ]

dim(tornado)
tornado[, c('design_id','strategy_id','future_id') := NULL]
dim(tornado)

#ouputfile
if (!dir.exists(paste0(dir.output, "/tornado/"))) {
    dir.create(paste0(dir.output, "/tornado/"), recursive = TRUE, showWarnings = FALSE)
}

dir.output.tornado  <- paste0(dir.output,"/tornado/")

fwrite(tornado, paste0(dir.output.tornado, "tornado_data_raw.csv"))
fwrite(att, paste0(dir.output.tornado, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output.tornado, "ATTRIBUTE_STRATEGY.csv"))

dir.input.tornado <- 'ssp_modeling/cost-benefits/tornado_plot/data/input/tornado/'

fwrite(att, paste0(dir.input.tornado, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.input.tornado, "ATTRIBUTE_STRATEGY.csv"))



################################################################################


dir.output  <-dir.output.tornado
output.file <- "tornado_data_raw.csv"


region <- "uganda" 
iso_code3 <- "UGA"


# set year_ref for this run
year_ref <- 2019
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/tornado/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/tornado/data_prep_new_mapping_uganda.r')
