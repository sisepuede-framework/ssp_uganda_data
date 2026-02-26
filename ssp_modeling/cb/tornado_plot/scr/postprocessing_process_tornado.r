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
att <- "ATTRIBUTE_STRATEGY.csv"


sttrategy_ids <- c(0,1000,1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,
                   2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,
                   3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012,3013,3014,3015,3016,3017,3018,3019,3020,3021,3022,3023,
                   4000,4001,4002,4003,4004,4005,6000,6001)

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
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194/tornado/"

fwrite(tornado, paste0(dir.output, "tornado_data_raw.csv"))
fwrite(att, paste0(dir.output, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output, "ATTRIBUTE_STRATEGY.csv"))

dir.output <- 'ssp_modeling/cb/tornado_plot/data/input/tornado/'

fwrite(att, paste0(dir.output, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output, "ATTRIBUTE_STRATEGY.csv"))



################################################################################


dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194/tornado/"
output.file <- "tornado_data_raw.csv"

region <- "uganda" 
iso_code3 <- "UGA"


# set year_ref for this run
year_ref <- 2019
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/tornado/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/tornado/data_prep_new_mapping_uganda.r')
