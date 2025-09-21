#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(RColorBrewer)
library(ggplot2)
library(scales)
library(tidyverse)

rm(list=ls())

df_2019 <- read_excel("data_processing/input_data/ccd_emissions_inventory/GHG Emissions_2019_Complete File.xlsx", 
                      sheet = "Table A Summary Table", range = "A3:D113")

# Ensure text column name is "Categories" (adjust if your file uses another name)
names(df_2019)[1] <- "Categories"

# Normaliza texto (quita dobles espacios y convierte –/— a "-")
df_2019 <- df_2019 %>%
  mutate(Categories = str_squish(str_replace_all(Categories, "[\u2013\u2014]", "-")))

# -----------------------
# Energy
# -----------------------
en_elec   <- c("1.A.1 - Energy Industries")
en_manu   <- c("1.A.2 - Manufacturing Industries and Construction")
en_trns   <- c("1.A.3 - Transport")
en_bld    <- c("1.A.4 - Other Sectors", "1.A.5 - Non-Specified")
en_fugit  <- c(
  "1.B.1 - Solid Fuels",
  "1.B.2 - Oil and Natural Gas",
  "1.B.3 - Other emissions from Energy Production",
  "1.C.1 - Transport of CO2",
  "1.C.2 - Injection and Storage",
  "1.C.3 - Other"
)
en_leaf <- c(en_elec, en_manu, en_trns, en_bld, en_fugit)


# -----------------------
# IPPU
# -----------------------

ipcu_leaf <- c(
  "2.A.1 - Cement production",
  "2.A.2 - Lime production",
  "2.A.3 - Glass Production",
  "2.A.4 - Other Process Uses of Carbonates",
  "2.A.5 - Other (please specify)",
  "2.B.1 - Ammonia Production",
  "2.B.2 - Nitric Acid Production",
  "2.B.3 - Adipic Acid Production",
  "2.B.4 - Caprolactam, Glyoxal and Glyoxylic Acid Production",
  "2.B.5 - Carbide Production",
  "2.B.6 - Titanium Dioxide Production",
  "2.B.7 - Soda Ash Production",
  "2.B.8 - Petrochemical and Carbon Black Production",
  "2.B.9 - Fluorochemical Production",
  "2.B.10 - Hydrogen Production",
  "2.B.11 - Other (Please specify)",
  "2.C.1 - Iron and Steel Production",
  "2.C.2 - Ferroalloys Production",
  "2.C.3 - Aluminium production",
  "2.C.4 - Magnesium production",
  "2.C.5 - Lead Production",
  "2.C.6 - Zinc Production",
  "2.C.7 - Rare Earths Production",
  "2.C.8 - Other (please specify)",
  "2.D.1 - Lubricant Use",
  "2.D.2 - Paraffin Wax Use"
)

# -----------------------
# AFOLU 
# -----------------------

# Livestock
ag_lvst <- c(
  "3.A.1 - Enteric Fermentation",
  "3.A.2 - Manure Management",
  "3.C.6 - Indirect N2O Emissions from manure management"
)

# Crops
ag_crops <- c(
  "3.C.1 - Burning",
  "3.C.2 - Liming",
  "3.C.3 - Urea application",
  "3.C.4 - Direct N2O Emissions from managed soils",
  "3.C.5 - Indirect N2O Emissions from managed soils",
  "3.C.7 - Rice cultivation",
  "3.C.12 - N2O Emissions from Aquaculture" # si prefieres, cámbiala a Livestock
)

# LULUCF
lulucf_forest <- c(
  "3.B.1 - Forest land",
  "3.D.1 - Harvested Wood Products"
)
lulucf_other <- c(
  "3.B.2 - Cropland",
  "3.B.3 - Grassland",
  "3.B.4 - Wetlands",
  "3.B.5 - Settlements",
  "3.B.6 - Other Land",
  "3.C.8 - CH4 from Drained Organic Soils",
  "3.C.9 - CH4 from Drainage Ditches on Organic Soils",
  "3.C.10 - CH4 from Rewetting of Organic Soils",
  "3.C.11 - CH4 Emissions from Rewetting of Mangroves and Tidal Marshes",
  "3.C.13 - CH4 Emissions from Rewetted and Created Wetlands on Inland Wetland Mineral Soils",
  "3.C.14 - Other (please specify)",
  "3.D.2 - Other (please specify)"
)

afolu_leaf <- c(ag_lvst, ag_crops, lulucf_forest, lulucf_other)

# -----------------------
# Waste (4) - hojas
# -----------------------
w_solid <- c(
  "4.A - Solid Waste Disposal",
  "4.B - Biological Treatment of Solid Waste",
  "4.C - Incineration and Open Burning of Waste",
  "4.E - Other (please specify)"
)
w_wwt <- c("4.D - Wastewater Treatment and Discharge")
w_leaf <- c(w_solid, w_wwt)



df_2019 <- df_2019 %>%
  mutate(
    `CSC Sector` = case_when(
      Categories %in% en_leaf   ~ "Energy",
      
      Categories %in% ipcu_leaf ~ "Industrial Processes",
      
      Categories %in% ag_lvst        ~ "Agriculture",
      Categories %in% ag_crops       ~ "Agriculture",
      Categories %in% lulucf_forest  ~ "Land Use, Land Use Change, and Forestry",
      Categories %in% lulucf_other   ~ "Land Use, Land Use Change, and Forestry",
      
      Categories %in% w_leaf ~ "Waste",
      
      TRUE ~ NA
    ),
    `CSC Subsector` = case_when(
      Categories %in% en_elec   ~ "EN - Electricity/Heat",
      Categories %in% en_manu   ~ "EN - Manufacturing/Construction",
      Categories %in% en_trns   ~ "EN - Transportation",
      Categories %in% en_bld    ~ "EN - Building",
      Categories %in% en_fugit  ~ "EN - Fugitive Emissions",
      
      Categories %in% ipcu_leaf ~ "IN - Industrial Processes",
      
      Categories %in% ag_lvst        ~ "AG - Livestock",
      Categories %in% ag_crops       ~ "AG - Crops",
      Categories %in% lulucf_forest  ~ "LULUCF - Forest Land",
      Categories %in% lulucf_other   ~ "LULUCF - Other Land",
      
      Categories %in% w_solid ~ "Waste - Solid Waste",
      Categories %in% w_wwt   ~ "Waste - Wastewater Treatment",
      TRUE ~ NA
    )
  )

df_2019 <- filter(df_2019, !is.na(`CSC Subsector`))


df_2019_clean <- df_2019 %>%
  rename(CO2 = `Net CO2 (1)(2)`) %>%
  mutate(
    across(c(CO2, CH4, N2O), ~na_if(as.character(.), "NE")),
    across(c(CO2, CH4, N2O), ~as.numeric(gsub(",", "", .)))
  )

df_2019_clean <- mutate(df_2019_clean,
  CO2 = CO2/1000,
  CH4 = (CH4*28)/1000,
  N2O = (N2O*265)/1000
  
)

# 2) Pivotea a formato long (una fila por gas)
df_long <- df_2019_clean %>%
  pivot_longer(
    cols = c(CO2, CH4, N2O),
    names_to  = "Gas",
    values_to = "2019"
  ) %>%
  filter(!is.na(`2019`)) %>%                       # elimina celdas sin dato
  mutate(Gas = factor(Gas, levels = c("CH4","CO2","N2O")))  # orden opcional

fwrite(df_long,  "data_processing/input_data/ccd_emissions_inventory/match_GHG_Emissions_uganda.csv")

df_csc_gas <- df_long %>%
  group_by(`CSC Sector`, `CSC Subsector`, Gas) %>%
  summarise(`2019` = sum(`2019`, na.rm = TRUE), .groups="drop")


