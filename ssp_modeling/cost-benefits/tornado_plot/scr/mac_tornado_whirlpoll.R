
# load packages
library(data.table)
library(reshape2)
library(dplyr)
library(ggplot2)

rm(list=ls())

#ouputfile
dir <- "ssp_modeling/cost-benefits/tornado_plot/data/output/"

tornado <- fread(paste0(dir, '/tornado/tornado_plot.csv'))

tornado$mac_tornado <- tornado$`marginal_total_abatement_cost_(USD/tCO2e)`
 
tornado <- select(tornado, primary_id, mac_tornado)



whirlpool <- fread(paste0(dir, '/whirlpool/tornado_plot_whirlpool.csv'))

whirlpool$mac_whirlpool <- whirlpool$`marginal_total_abatement_cost_(USD/tCO2e)`

whirlpool <- select(whirlpool, primary_id, mac_whirlpool)


mac <- fread('ssp_modeling/cost-benefits/tornado_plot/data/input/sisepuede_run_2026-03-10T13;27;53.264959/ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv')

mac <- left_join(mac, tornado, by=c('primary_id_tornado'='primary_id'))

mac <- left_join(mac, whirlpool, by=c('primary_id_whirlpool'='primary_id'))

mac$mac_tornado <- as.numeric(mac$mac_tornado)
mac$mac_whirlpool <- as.numeric(mac$mac_whirlpool) 

fwrite(mac, paste0(dir,'mac_tornado_to_whirlpool.csv'), row.names = F)