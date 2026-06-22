-- emissions_and_gdp.sql
-- ---------------------------------------------------------------------------
-- Emissions by subsector + derived GDP for the surrogate-model training set.
--
-- Source table: model_output  (one row per primary_id x time_period).
-- We keep only the 5 target years, encoded as time_period (= year - 2015):
--     time_period 10/20/25/35/55  ->  years 2025/2035/2040/2050/2070
--
-- There is NO gdp_mmm_usd column in this run, so we derive GDP in billions of
-- USD ("mmm" = thousand-million) from per-capita GDP * total population / 1e9.
--
-- {region} is filled in by run_extracts.py from the config (Hive partition,
-- so this also prunes the scan to just that region's files -> cheaper).
-- ---------------------------------------------------------------------------
SELECT
    primary_id,
    time_period,
    emission_co2e_subsector_total_agrc,
    emission_co2e_subsector_total_ccsq,
    emission_co2e_subsector_total_entc,
    emission_co2e_subsector_total_fgtv,
    emission_co2e_subsector_total_frst,
    emission_co2e_subsector_total_inen,
    emission_co2e_subsector_total_ippu,
    emission_co2e_subsector_total_lndu,
    emission_co2e_subsector_total_lsmm,
    emission_co2e_subsector_total_lvst,
    emission_co2e_subsector_total_scoe,
    emission_co2e_subsector_total_soil,
    emission_co2e_subsector_total_trns,
    emission_co2e_subsector_total_trww,
    emission_co2e_subsector_total_waso,
    gdp_per_capita_usd * population_gnrl_total / 1e9 AS gdp_mmm_usd
FROM model_output
WHERE region = '{region}'
AND time_period IN (10, 20, 25, 35, 55);
