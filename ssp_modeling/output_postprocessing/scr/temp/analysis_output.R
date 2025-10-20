#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(RColorBrewer)
library(ggplot2)
library(scales)

rm(list=ls())

run <- "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2025-09-27T21;50;10.556740/"


df <- fread(paste0(run,'/uganda.csv'))
#df <- fread(paste0(run,'/WIDE_INPUTS_OUTPUTS.csv'))
att <- fread(paste0(run,'/ATTRIBUTE_PRIMARY.csv'))
stt <- fread(paste0(run,'/ATTRIBUTE_STRATEGY.csv'))


df <- merge(df, att, by = "primary_id", all.x = TRUE)
df <- merge(df, stt, by = "strategy_id", all.x = TRUE)

table(df$strategy)

 
other_ch4 <- c('emission_co2e_ch4_agrc_biomass_burning',
                 'emission_co2e_ch4_lndu_wetlands')

other_n2o <- c('emission_co2e_n2o_agrc_biomass_burning')


df_long <- melt(df, 
                id.vars = c("primary_id", "strategy", "time_period"), 
                measure.vars = other_n2o)

ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "",
       x = "Time Period",
       y = "",
       fill = "Variable") +
  theme_dark()

df$emission_co2e_subsector_total_fgtv



build_ch4 <- c('emission_co2e_ch4_scoe_commercial_municipal',
               'emission_co2e_ch4_scoe_other_se',
               'emission_co2e_ch4_scoe_residential')

waste_no2 <- c('emission_co2e_n2o_waso_compost_food','emission_co2e_n2o_waso_compost_sludge',
               'emission_co2e_n2o_waso_compost_yard','emission_co2e_n2o_waso_incineration')


fgtv_co2 <- c('emission_co2e_subsector_total_fgtv',
                 'emission_co2e_co2_fgtv_fuel_natural_gas',
                 'emission_co2e_co2_fgtv_fuel_oil',
                 'emission_co2e_co2_entc_mining_and_extraction_me_coal',
                 'emission_co2e_co2_entc_mining_and_extraction_me_crude',
                 'emission_co2e_co2_entc_mining_and_extraction_me_natural_gas',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_ammonia_production',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_hydrogen_electrolysis',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_hydrogen_gasification',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_hydrogen_reformation',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_hydrogen_reformation_ccs',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_natural_gas',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_natural_gas_liquefaction',
                 'emission_co2e_co2_entc_nbmass_processing_and_refinement_fp_petroleum_refinement')


df_long <- melt(df, 
                id.vars = c("primary_id", "strategy", "time_period"), 
                measure.vars = waste_no2)

ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "",
       x = "Time Period",
       y = "",
       fill = "Variable") +
  theme_dark()

