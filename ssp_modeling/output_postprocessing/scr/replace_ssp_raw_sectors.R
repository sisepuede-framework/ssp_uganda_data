# =========================================================
# This script prepares the data for emissions mapping in Uganda
# =========================================================

suppressPackageStartupMessages({
  library(data.table)
  library(dplyr)
  library(reshape2)
})

# ----------------- Shared parameters/inputs -----------------
year_ref_1 <- 2019
file.name  <- paste0(output.file)
iso_code3  <- iso_code3
Country    <- region
dir.tableau <- paste0("ssp_modeling/Tableau/data/")

sector_switch <- c('Fugitive Emissions:co2',
                   'Fugitive Emissions:ch4',
                   'Fugitive Emissions:n2o',
                   'Electricity and Heat Generation:co2',
                   'Electricity and Heat Generation:ch4',
                   'Electricity and Heat Generation:n2o',
                   'Fuel Production:co2',)
                   'Fuel Production:ch4',
                   'Fuel Production:n2o')

# ----------------- Load crosswalk (once) -----------------
mapping <- read.csv('ssp_modeling/output_postprocessing/data/crosswalk_inventory_to_sisepeude.csv')
mapping$Subsector_Category <- paste(mapping$aggregation_category,
                             mapping$gas,sep=":")

mapping <- mapping %>%
  rename(
    Subsector = aggregation_category,
    Gas = gas,
    Vars = sisepuede_fields
  )

mapping<-mapping[,c("Subsector","Gas","Subsector_Category", "Vars")]
mapping <- subset(mapping, Subsector_Category %in% sector_switch)

# ----------------- Load EDGAR  -----------------
edgar_wide <- read.csv('ssp_modeling/output_postprocessing/data/inventory_trajectories.csv')

edgar_wide <- subset(edgar_wide, Subsector_Category %in% sector_switch)

# ----------------- Load raw -----------------
data <- fread(paste0(dir.output,file.name)) %>% as.data.frame()
data <- subset(data,region==Country)
setorder(data, primary_id, time_period, region)

# ----------------- Build mapped columns in sim (once) -----------------
id_vars <- c('region','time_period',"primary_id")
mapping$ids <- paste(row.names(mapping),mapping$Subsector,mapping$Gas,sep="_")

for (i in 1:nrow(mapping)) {
  tvars <- mapping$Vars[i]
  tvars <- unlist(strsplit(tvars,":"))
  tvars <- subset(tvars,tvars%in%colnames(data))
  if (length(tvars)>1) {
    data[, mapping$ids[i]] <- rowSums(data[, tvars, drop=FALSE])
  } else if (length(tvars)==1) { 
    data[, mapping$ids[i]] <- data[, tvars]
  } else {
    data[, mapping$ids[i]] <- 0
  } 
}

# =========================================================
# -------------------------- 219 --------------------------
# =========================================================

year_ref <- year_ref_1

# rebuild data_new from the same 'data' and 'mapping' (fresh block as in your script 2)
data_new <- data[, c(id_vars, mapping$ids)]
dim(data_new)

data_new <- data.table(data_new)
data_new <- reshape2::melt(data_new, id.vars = id_vars, measure.vars = mapping$ids)
data_new <- data.frame(data_new)
data_new$ids <- as.character(data_new$variable)

mapping_tmp <- mapping
mapping$Vars <- NULL
colnames(mapping)[colnames(mapping) == "Subsector"] <- "CSC.Subsector"
data_new <- merge(data_new,mapping,by="ids")

#now aggregare at inventory level 
data_new <- aggregate(list(value=data_new$value),by=list(primary_id=data_new$primary_id,
                                             time_period=data_new$time_period,
                                             Subsector_Category=data_new$Subsector_Category,
                                             CSC.Subsector=data_new$CSC.Subsector),sum)
table(data_new$Subsector_Category)

data_new$Year <- data_new$time_period + 2015
data_new$Gas <- do.call("rbind",strsplit(data_new$Subsector_Category,":"))[,2]
table(data_new$Gas)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
head(att)
dim(data_new)

data_new <- merge(data_new,att,by="primary_id")
dim(data_new)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(data_new)
data_new <- merge(data_new,atts[c("strategy_id","strategy")],by="strategy_id")
dim(data_new)

# melt edgar (for 2022)
id_varsEd <- c("Code","CSC.Subsector","Gas","Subsector_Category")
measure.vars_Ed <- subset(colnames(edgar_wide),grepl("X",colnames(edgar_wide))==TRUE)
edgar <- data.table(edgar_wide)
edgar <- melt(edgar, id.vars = id_varsEd, measure.vars =measure.vars_Ed)
edgar <- data.frame(edgar)
edgar$Year <- as.numeric(gsub("X","",edgar$variable))

# align columns
edgar$variable <- NULL
edgar$strategy_id <- NA
edgar$primary_id <- NA 
edgar$design_id <- NA 
edgar$future_id <- NA 
edgar$Contry <- Country
edgar$strategy <- "Historical" 
edgar$source <- "EDGAR"
edgar <- subset(edgar,Year<=year_ref)

data_new$time_period <- NULL 
data_new$Code <- iso_code3 
data_new$Contry <- Country
data_new$source <- "SISEPUEDE"
data_new <- subset(data_new,Year>=year_ref)

data_new <- rbind(data_new,edgar)
data_new <- data_new[order(data_new$strategy_id,data_new$CSC.Subsector,data_new$Gas,data_new$Year),]

table(data_new$strategy_id, data_new$strategy)
table(data_new$strategy, exclude = NULL)

# write 2019 file
combined <- read.csv(paste0(dir.tableau,'raw_emissions_uganda_2019_WIDE_INPUTS_OUTPUTS.csv'))
combined <- subset(combined, !(Subsector_Category %in% sector_switch & !is.na(strategy_id)))

combined <- rbind(combined, data_new)




file.name.out22 <- 'emissions_uganda_WIDE_INPUTS_OUTPUTS_vf.csv'
write.csv(combined,paste0(dir.tableau,file.name.out22),row.names=FALSE)


