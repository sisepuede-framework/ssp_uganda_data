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

# load full data
whirlpool <- fread(paste0(dir.output, output.file))
dim(whirlpool)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
dim(att)
att <- att[att$strategy_id==0 | att$strategy_id==6004 | (att$strategy_id >= 6559 & att$strategy_id <= 6617), ]
dim(att)
head(att)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(atts)
atts <- atts[atts$strategy_id==0 | atts$strategy_id==6004 | (atts$strategy_id >= 6559 & atts$strategy_id <= 6617), ]
dim(atts)
head(atts)


whirlpool <- merge(whirlpool,att,by="primary_id")
dim(whirlpool)

#filter for the strategies we want to include in the whirlpool
whirlpool <- whirlpool[whirlpool$strategy_id==0 | whirlpool$strategy_id==6004 | (whirlpool$strategy_id >= 6559 & whirlpool$strategy_id <= 6617), ]

dim(whirlpool)
whirlpool[, c('design_id','strategy_id','future_id') := NULL]
dim(whirlpool)

# # replace fail runs
# dir.output.err  <- "ssp_modeling/ssp_run_output/sisepuede_results_sisepuede_run_2026-03-12T17;22;02.508214/"
# output.file <- "sisepuede_results_sisepuede_run_2026-03-12T17;22;02.508214_WIDE_INPUTS_OUTPUTS.csv"

# error <- fread(paste0(dir.output.err, output.file))
# error <- error[error$primary_id %in% c(76076,77077,81081,89089,97097,99099,111111,119119), ]
# dim(error)

# dim(whirlpool)
# whirlpool <- whirlpool[!whirlpool$primary_id %in% c(76076,77077,81081,89089,97097,99099,111111,119119), ]
# dim(whirlpool)

# whirlpool <- rbind(whirlpool,error)
# dim(whirlpool)



#ouputfile
if (!dir.exists(paste0(dir.output, "/whirlpool/"))) {
    dir.create(paste0(dir.output, "/whirlpool/"), recursive = TRUE, showWarnings = FALSE)
}

dir.output.whirlpool  <- paste0(dir.output,"/whirlpool/")

fwrite(whirlpool, paste0(dir.output.whirlpool, "whirlpool_data_raw.csv"))
fwrite(att, paste0(dir.output.whirlpool, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output.whirlpool, "ATTRIBUTE_STRATEGY.csv"))

dir.input.whirlpool <- 'ssp_modeling/cost-benefits/tornado_plot/data/input/whirlpool/'

fwrite(att, paste0(dir.input.whirlpool, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.input.whirlpool, "ATTRIBUTE_STRATEGY.csv"))



################################################################################

dir.output  <- dir.output.whirlpool
output.file <- "whirlpool_data_raw.csv"

region <- "uganda" 
iso_code3 <- "UGA"

# set year_ref for this run
year_ref <- 2019
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/whirlpool/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/whirlpool/data_prep_new_mapping_uganda.r')
