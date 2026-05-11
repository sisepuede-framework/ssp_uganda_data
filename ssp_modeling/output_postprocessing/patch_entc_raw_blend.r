################################################################################
# patch_entc_raw_blend.r
#
# Run this AFTER postprocessing_process_nr.r has completed.
#
# Problem: the calibration anchor in emission_targets_uganda_2019.csv sets the
# 2019 ENTC "Electricity and Heat Generation" baseline to ~0.074 MT CO2e
# (Uganda's grid was ~85% hydro in 2019). This crushes the entire trajectory,
# hiding the natural-gas generation growth that SISEPUEDE projects.
#
# Fix: keep calibrated values through 2025, then linearly blend toward the
# raw SISEPUEDE values, reaching full raw values by 2070. After 2070, use
# raw values directly. Re-generates the Tableau emissions CSV at the end.
################################################################################

library(data.table)
library(dplyr)
library(reshape2)

# ── Parameters (must match postprocessing_process_nr.r) ──────────────────────
run         <- 'sisepuede_summary_results_run_sisepuede_run_2026-05-10T09;58;21.534094'
dir.output  <- paste0("ssp_modeling/ssp_run_output/", run, "/")
output.file <- "c585e7e9-e32f-4131-999b-ee7fc5ec014e.csv"
region      <- "uganda"
iso_code3   <- "UGA"
year_ref    <- 2019

year_blend_start <- 2025
year_blend_end   <- 2070
tp_blend_start   <- year_blend_start - 2015  # time_period 10
tp_blend_end     <- year_blend_end   - 2015  # time_period 55

# ── Load calibrated output ───────────────────────────────────────────────────
cal_file <- paste0(dir.output, region, ".csv")
cal <- fread(cal_file) %>% as.data.frame()

# ── Load raw SISEPUEDE output ────────────────────────────────────────────────
raw <- fread(paste0(dir.output, output.file)) %>% as.data.frame()
raw <- raw[raw$region == region, ]

# ── Identify ENTC Electricity and Heat Generation variables ──────────────────
targets <- read.csv("ssp_modeling/output_postprocessing/data/emission_targets_uganda_2019.csv")
entc_elec_rows <- subset(targets, Subsector == "Electricity and Heat Generation" & ssp_subsector == "entc")
entc_gen_vars  <- unique(unlist(strsplit(paste(entc_elec_rows$Vars, collapse = ":"), ":")))
entc_gen_vars  <- intersect(entc_gen_vars, colnames(cal))

message(sprintf("Blending %d ENTC generation variables: calibrated at %d, raw by %d",
                length(entc_gen_vars), year_blend_start, year_blend_end))

# ── Build raw lookup keyed on primary_id|time_period ────────────────────────
raw_blend <- raw[raw$time_period > tp_blend_start, c("primary_id", "time_period", entc_gen_vars)]
raw_blend$row_key <- paste(raw_blend$primary_id, raw_blend$time_period, sep = "|")
raw_lookup <- raw_blend[, c("row_key", entc_gen_vars)]
rownames(raw_lookup) <- raw_lookup$row_key
raw_lookup$row_key <- NULL

# ── Apply linear blend for time_period > tp_blend_start ─────────────────────
blend_mask <- cal$time_period > tp_blend_start
cal$row_key <- paste(cal$primary_id, cal$time_period, sep = "|")

tp_vals <- cal$time_period[blend_mask]
weights  <- pmin((tp_vals - tp_blend_start) / (tp_blend_end - tp_blend_start), 1.0)

for (var in entc_gen_vars) {
  keys     <- cal$row_key[blend_mask]
  raw_vals <- raw_lookup[keys, var]

  # Fall back to calibrated if raw is missing (e.g. primary_id not in raw)
  missing_raw <- is.na(raw_vals)
  raw_vals[missing_raw] <- cal[[var]][blend_mask][missing_raw]

  cal[[var]][blend_mask] <- (1 - weights) * cal[[var]][blend_mask] + weights * raw_vals
}

cal$row_key <- NULL

# ── Recompute entc subsector total ───────────────────────────────────────────
all_entc_vars <- unique(unlist(strsplit(
  paste(subset(targets, ssp_subsector == "entc")$Vars, collapse = ":"), ":"
)))
all_entc_vars <- intersect(all_entc_vars, colnames(cal))
cal[["emission_co2e_subsector_total_entc"]] <- rowSums(
  cal[, all_entc_vars, drop = FALSE], na.rm = TRUE
)

# ── Write backup and patched uganda.csv ──────────────────────────────────────
file.copy(cal_file, paste0(cal_file, ".bak"), overwrite = TRUE)
fwrite(cal, cal_file, row.names = FALSE)
message("uganda.csv patched. Original saved to uganda.csv.bak")

# ── Regenerate Tableau emissions CSV ─────────────────────────────────────────
source("ssp_modeling/output_postprocessing/scr/LULUCF/data_prep_new_mapping_uganda.r")

message(sprintf("Done. Tableau output regenerated: ssp_modeling/Tableau/data/emissions_%s_%d.csv",
                region, year_ref))
