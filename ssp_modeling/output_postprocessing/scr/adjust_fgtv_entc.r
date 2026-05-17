################################################################################
# Adjustment: Fugitive Emissions, Electricity and Heat Generation, Fuel Production
#
# Replaces calibrated values with raw SISEPUEDE values from the start year,
# with a 5-year blend to avoid a sharp spike at the transition:
#   Year 1: 30% raw + 70% calibrated
#   Year 2: 50% raw + 50% calibrated
#   Year 3: 60% raw + 40% calibrated
#   Year 4: 70% raw + 30% calibrated
#   Year 5+: 100% raw
################################################################################

tp_fgtv_start <- 2020 - 2015  # = 5
tp_entc_start <- 2027 - 2015  # = 12
tp_fuel_start <- 2027 - 2015  # = 12

blend_weights <- c(0.3, 0.5, 0.6, 0.7, 1.0)  # 5-year transition

uga <- fread(paste0(dir.output, region, ".csv")) %>% as.data.frame()
raw <- fread(paste0(dir.output, output.file))   %>% as.data.frame()
raw <- subset(raw, time_period >= time_period_ref)

crosswalk <- read.csv('ssp_modeling/output_postprocessing/data/crosswalk_inventory_to_sisepeude_20260510.csv',
                      stringsAsFactors = FALSE)

get_crosswalk_vars <- function(crosswalk, sector_name) {
  rows <- crosswalk[crosswalk$aggregation_category == sector_name, ]
  unique(trimws(unlist(strsplit(rows$sisepuede_fields, ":"))))
}

replace_with_raw <- function(uga, raw, cols, tp_start, blend_weights) {
  cols         <- intersect(cols, intersect(colnames(uga), colnames(raw)))
  n_blend      <- length(blend_weights)
  tp_full_raw  <- tp_start + n_blend  # first year at 100% raw (no blend needed)

  for (pid in unique(uga$primary_id)) {
    mask_uga <- uga$primary_id == pid
    mask_raw <- raw$primary_id == pid

    for (col in cols) {
      # Blend years: partial raw
      for (i in seq_along(blend_weights)) {
        tp_i <- tp_start + (i - 1)
        w    <- blend_weights[i]
        raw_val <- raw[mask_raw  & raw$time_period == tp_i, col]
        cal_val <- uga[mask_uga  & uga$time_period == tp_i, col]
        if (length(raw_val) == 0 || length(cal_val) == 0) next
        uga[mask_uga & uga$time_period == tp_i, col] <- w * raw_val + (1 - w) * cal_val
      }

      # Full raw years: direct replacement
      mask_full <- mask_uga & uga$time_period >= tp_full_raw
      raw_full  <- raw[mask_raw & raw$time_period >= tp_full_raw, ]
      raw_full  <- raw_full[order(raw_full$time_period), col]
      if (length(raw_full) > 0)
        uga[mask_full, col] <- raw_full
    }
  }
  uga
}

fgtv_vars <- get_crosswalk_vars(crosswalk, "Fugitive Emissions")
entc_vars <- get_crosswalk_vars(crosswalk, "Electricity and Heat Generation")
fuel_vars <- get_crosswalk_vars(crosswalk, "Fuel Production")

uga <- replace_with_raw(uga, raw, fgtv_vars, tp_fgtv_start, blend_weights)
uga <- replace_with_raw(uga, raw, entc_vars, tp_entc_start, blend_weights)
uga <- replace_with_raw(uga, raw, fuel_vars, tp_fuel_start, blend_weights)

fwrite(uga, paste0(dir.output, region, ".csv"), row.names = FALSE)
print("Finish: adjust_fgtv_entc")
