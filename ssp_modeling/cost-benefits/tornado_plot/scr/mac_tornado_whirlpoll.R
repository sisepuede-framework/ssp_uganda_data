
# load packages
library(data.table)
library(dplyr)

rm(list=ls())

#ouputfile
dir <- "ssp_modeling/ssp_run_output/sisepuede_run_2026-03-10t13;27;53.264959/"
mac <- fread(paste0(dir, 'ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv'))

tornado <- fread(paste0(dir, 'marginal_abatement_costs.csv'))

# data for tableau tornado plot
tableau_tornado <- left_join(mac, 
                            select(tornado, primary_id,emission_total,base_emission_total,emission_diff,
                                   technical_cost,marginal_abatement_cost), 
                            by=c('primary_id_tornado'='primary_id'))
tableau_tornado <- tableau_tornado %>% filter(emission_diff!=0)                            
fwrite(tableau_tornado, 'ssp_modeling/Tableau/data/tableau_tornado.csv', row.names = F)


tornado$mac_tornado <- tornado$marginal_abatement_cost 
tornado <- select(tornado, primary_id, mac_tornado)


whirlpool <- fread(paste0(dir, 'marginal_abatement_costs_whirlpool.csv'))

# data for tableau whirlpool
tableau_whirlpool <- left_join(mac, 
                            select(whirlpool, primary_id,emission_total,base_emission_total,emission_diff,
                                   technical_cost,marginal_abatement_cost), 
                            by=c('primary_id_whirlpool'='primary_id'))
tableau_whirlpool <- tableau_whirlpool %>% filter(emission_diff!=0)                            
fwrite(tableau_whirlpool, 'ssp_modeling/Tableau/data/tableau_whirlpool.csv', row.names = F)


whirlpool$mac_whirlpool <- whirlpool$marginal_abatement_cost
whirlpool <- select(whirlpool, primary_id, mac_whirlpool)

mac <- left_join(mac, tornado, by=c('primary_id_tornado'='primary_id'))

mac <- left_join(mac, whirlpool, by=c('primary_id_whirlpool'='primary_id'))

mac$mac_tornado <- as.numeric(mac$mac_tornado)
mac$mac_whirlpool <- as.numeric(mac$mac_whirlpool) 


mac <- mac %>% filter(!is.na(mac_tornado) & !is.na(mac_whirlpool))


fwrite(mac, 'ssp_modeling/Tableau/data/mac_tornado_to_whirlpool.csv', row.names = F)