-- cost_benefit.sql
-- ---------------------------------------------------------------------------
-- Cost/benefit fields for the surrogate-model training set.
--
-- Source table: cb  (one row per primary_id x time_period).
-- We keep only the 5 target years, encoded as time_period (= year - 2015):
--     time_period 10/20/25/35/55  ->  years 2025/2035/2040/2050/2070
--
-- Sign convention: in the source, COSTS are already negative and BENEFITS
-- positive (diverging convention). Do NOT re-negate downstream.
--
-- The 3 cost fields are *_cost; everything else is a benefit. Two benefit
-- fields are new in this run: ecosystem_services_grasslands / _wetlands.
--
-- {region} is filled in by run_extracts.py from the config (Hive partition).
-- ---------------------------------------------------------------------------
SELECT
    primary_id,
    time_period,
    air_pollution,
    congestion,
    consumer_savings,
    crop_value,
    ecosystem_services,
    env_pollution,
    fuel_cost,
    human_health,
    ippu_value,
    land_pollution,
    lvst_value,
    road_safety,
    sector_specific,
    system_cost,
    technical_cost,
    technical_savings,
    water_pollution,
    ecosystem_services_grasslands,
    ecosystem_services_wetlands
FROM cb
WHERE region = '{region}'
AND time_period IN (10, 20, 25, 35, 55);
