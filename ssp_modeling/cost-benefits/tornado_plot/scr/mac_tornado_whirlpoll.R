
# load packages
library(data.table)
library(reshape2)
library(dplyr)
library(ggplot2)

rm(list=ls())

#ouputfile
dir <- "ssp_modeling/cb/tornado_plot/data/output/"

tornado <- fread(paste0(dir, '/tornado/tornado_plot.csv'))

tornado$mac_tornado <- tornado$`marginal_total_abatement_cost_(USD/tCO2e)`
 
tornado <- select(tornado, primary_id, mac_tornado)



whirlpool <- fread(paste0(dir, '/whirlpool/tornado_plot_whirlpool.csv'))

whirlpool$mac_whirlpool <- whirlpool$`marginal_total_abatement_cost_(USD/tCO2e)`

whirlpool <- select(whirlpool, primary_id, mac_whirlpool)


mac <- fread('ssp_modeling/cb/tornado_plot/data/input/primary_id_map_tornado_to_whirlpool.csv')

mac <- left_join(mac, tornado, by=c('tornado'='primary_id'))

mac <- left_join(mac, whirlpool, by=c('whirlpool'='primary_id'))

fwrite(mac, paste0(dir,'mac_tornado_to_whirlpool.csv'), row.names = F)