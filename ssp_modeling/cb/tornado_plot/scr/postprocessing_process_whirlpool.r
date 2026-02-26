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

# load full data
whirlpool <- fread(paste0(dir.output, output.file))
dim(whirlpool)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
dim(att)
att <- att[att$strategy_id==0 | (att$strategy_id >= 6500 & att$strategy_id <= 6561), ]
dim(att)
head(att)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(atts)
atts <- atts[att$strategy_id==0 | (atts$strategy_id >= 6500 & atts$strategy_id <= 6561), ]
dim(atts)
head(atts)


whirlpool <- merge(whirlpool,att,by="primary_id")
dim(whirlpool)

#filter for the strategies we want to include in the whirlpool
whirlpool <- whirlpool[whirlpool$strategy_id==0 | (whirlpool$strategy_id >= 6500 & whirlpool$strategy_id <= 6561), ]

dim(whirlpool)
whirlpool[, c('design_id','strategy_id','future_id') := NULL]
dim(whirlpool)

# load data for NZ
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_run_2025-10-29T19;49;25.722413/"
output.file <- "sisepuede_ide_run_2025-10-29T19;49;25.722413.csv"

nz <- fread(paste0(dir.output, output.file))
nz <- nz[nz$primary_id == 70070, ]
dim(nz)
whirlpool <- rbind(nz, whirlpool)

att_nz <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
att_nz <- att_nz[att_nz$primary_id == 70070, ]

atts_nz <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
atts_nz <- atts_nz[atts_nz$strategy_id == 6004, ]
atts_nz

att <- rbind(att_nz, att)
atts <- rbind(atts_nz, atts)

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194/whirlpool/"

fwrite(whirlpool, paste0(dir.output, "whirlpool_data_raw.csv"))
fwrite(att, paste0(dir.output, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output, "ATTRIBUTE_STRATEGY.csv"))

dir.output <- 'ssp_modeling/cb/tornado_plot/data/input/whirlpool/'

fwrite(att, paste0(dir.output, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output, "ATTRIBUTE_STRATEGY.csv"))



################################################################################


dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194/whirlpool/"
output.file <- "whirlpool_data_raw.csv"

region <- "uganda" 
iso_code3 <- "UGA"


# set year_ref for this run
year_ref <- 2019
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/whirlpool/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/whirlpool/data_prep_new_mapping_uganda.r')
