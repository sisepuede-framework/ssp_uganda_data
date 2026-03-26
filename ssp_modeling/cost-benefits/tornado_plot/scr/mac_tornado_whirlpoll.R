
# load packages
library(data.table)
library(dplyr)

rm(list=ls())

#ouputfile
dir <- "ssp_modeling/ssp_run_output/sisepuede_run_2026-03-10t13;27;53.264959/"

tornado <- fread(paste0(dir, 'marginal_abatement_costs.csv'))

tornado$mac_tornado <- tornado$marginal_abatement_cost
 
tornado <- select(tornado, primary_id, mac_tornado)



whirlpool <- fread(paste0(dir, 'marginal_abatement_costs_whirlpool.csv'))

whirlpool$mac_whirlpool <- whirlpool$marginal_abatement_cost

whirlpool <- select(whirlpool, primary_id, mac_whirlpool)


mac <- fread(paste0(dir, 'ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv'))

mac <- left_join(mac, tornado, by=c('primary_id_tornado'='primary_id'))

mac <- left_join(mac, whirlpool, by=c('primary_id_whirlpool'='primary_id'))

mac$mac_tornado <- as.numeric(mac$mac_tornado)
mac$mac_whirlpool <- as.numeric(mac$mac_whirlpool) 

fwrite(mac, paste0(dir,'mac_tornado_to_whirlpool.csv'), row.names = F)