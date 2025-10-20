# This script prepares the data for emissions mapping in Uganda

year_ref <- 2022
file.name <- paste0(output.file)
iso_code3 <- iso_code3
Country <- region


sector_switch <- c('Solid Waste:n2o')

#load last crosswalk
mapping <- read.csv('ssp_modeling/output_postprocessing/data/decomp_package_ug_cw_ssp_to_ndc_with_synthetic_subsectors.csv')
mapping$Edgar_Class <- paste(mapping$display_subsector,mapping$gas,sep=":")

mapping <- mapping %>%
  rename(
    Edgar_Sector = sector,
    Edgar_Subsector = display_subsector,
    Gas = gas,
    Vars = variable_fields
  )

mapping<-mapping[,c("Subsector","Gas","Edgar_Sector","Edgar_Subsector","Edgar_Class", "Vars")]

mapping <- subset(mapping, Edgar_Class %in% sector_switch)


# add edgar
edgar <- read.csv('ssp_modeling/output_postprocessing/data/emission_targets_uganda_ghg_inventory_nc_csc.csv')
edgar$Edgar_Class<- paste(edgar$CSC.Subsector,edgar$Gas,sep=":")
edgar <- subset(edgar, Edgar_Class %in% sector_switch)


#load data  
data <- read.csv(paste0(dir.output,file.name)) 
data <- subset(data,region==Country)

#order data
setorder(data, primary_id, time_period, region)

#emission vars only 
id_vars <-c('region','time_period',"primary_id")
vars <- subset(colnames(data),!(colnames(data)%in%id_vars))
target_vars <- subset(vars,grepl("co2e_",vars)==TRUE)
total_vars <- subset(target_vars,grepl("emission_co2e_subsector_total",target_vars)==TRUE)
target_vars <- subset(target_vars,!(target_vars%in%total_vars))

#load inventory mapping table 
mapping$ids <- paste(row.names(mapping),mapping$Subsector,mapping$Gas,sep="_")
#now create those new columns in the simulation data set 
for  (i in 1:nrow(mapping))
{
  #i<- 63
  tvars <- mapping$Vars[i]
  tvars <- unlist(strsplit(tvars,":"))
  tvars <- subset(tvars,tvars%in%colnames(data))
  if (length(tvars)>1) {
    data [,mapping$ids[i]] <- rowSums(data[,tvars])
  } else if (length(tvars)==1 ) 
  { 
    data [,mapping$ids[i]] <- data[,tvars]
  } else {
    data [,mapping$ids[i]] <- 0
  } 
}
#now we just keep the new variables and the time period which we will reduce to above 2022
data_new <- data [,c(id_vars,mapping$ids)]
dim(data_new)

#convert from wide to long 
data_new <- data.table(data_new)
data_new <- reshape2::melt(data_new, id.vars = id_vars,
                           measure.vars = mapping$ids,
)
data_new <- data.frame(data_new)
data_new$ids <- as.character(data_new$variable)

#merge with mapping 
mapping$Vars <- NULL
colnames(mapping) <- gsub("Edgar_Sector","CSC.Sector",colnames(mapping))
colnames(mapping) <- gsub("Edgar_Subsector","CSC.Subsector",colnames(mapping)) 
data_new <- merge(data_new,mapping,by="ids")

#now aggregare at inventory level 
data_new <- aggregate(list(value=data_new$value),by=list(primary_id=data_new$primary_id,
                                                         time_period=data_new$time_period,
                                                         Edgar_Class=data_new$Edgar_Class,
                                                         CSC.Sector=data_new$CSC.Sector,
                                                         CSC.Subsector=data_new$CSC.Subsector),sum)
table(data_new$CSC.Subsector)


data_new$Year <- data_new$time_period + 2015
data_new$Gas <- do.call("rbind",strsplit(data_new$Edgar_Class,":"))[,2]

table(data_new$Gas)

#merge additional files  
att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
head(att)

dim(data_new)

data_new <- merge(data_new,att,by="primary_id")
dim(data_new)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))

#merge 
dim(data_new)
data_new <- merge(data_new,atts[c("strategy_id","strategy")],by="strategy_id")
dim(data_new)

#melt edgar data 
id_varsEd <- c("Code","CSC.Sector","CSC.Subsector","Gas","Edgar_Class")
measure.vars_Ed <- subset(colnames(edgar),grepl("X",colnames(edgar))==TRUE)
edgar <- data.table(edgar)
edgar <- melt(edgar, id.vars = id_varsEd, measure.vars =measure.vars_Ed)
edgar <- data.frame(edgar)
edgar$Year <- as.numeric(gsub("X","",edgar$variable))

#make sure both data frames have the same columns 
#edgar 
edgar$variable <- NULL
edgar$strategy_id <- NA
edgar$primary_id <- NA 
edgar$design_id <- NA 
edgar$future_id <- NA 
edgar$Contry <- Country
edgar$strategy <- "Historical" 
edgar$source <- "EDGAR"
edgar <- subset(edgar,Year<=year_ref)

#data_new 
data_new$time_period <- NULL 
data_new$Code <- iso_code3 
data_new$Contry <- Country
data_new$source <- "SISEPUEDE"
data_new <- subset(data_new,Year>=year_ref)


#rbind both 
data_new <- rbind(data_new,edgar)
data_new <- data_new[order(data_new$strategy_id,data_new$CSC.Subsector,data_new$Gas,data_new$Year),]

data_new <- subset(data_new , strategy_id != 6008)

table(data_new$strategy_id, data_new$strategy)
table(data_new$strategy, exclude = NULL)


#write file
dir.tableau <- paste0("ssp_modeling/Tableau/data/")

combined <- read.csv(paste0(dir.tableau,'raw_emissions_uganda_2022_WIDE_INPUTS_OUTPUTS.csv'))
combined <- subset(combined , is.na(strategy_id) | strategy_id!=6008)
combined <- subset(combined, !(Edgar_Class %in% sector_switch & !is.na(strategy_id)))


combined <- rbind(combined, data_new)

df_20  <- read.csv(paste0(dir.tableau,'emissions_uganda_WIDE_INPUTS_OUTPUTS_combined_fgtv_2020.csv')) 

combined <- rbind(combined, df_20)

table(combined$strategy, exclude = NULL)

hist <- combined$value[combined$strategy == "Historical" &
                 combined$Edgar_Class %in% sector_switch &
                 combined$Year == 2022]

obs <- combined$value[combined$strategy == "NZ" &
                         combined$Edgar_Class %in% sector_switch &
                         combined$Year == 2022]
diff<- obs/hist

combined$value[combined$strategy == "Historical" & 
                 combined$Edgar_Class %in% sector_switch ] <- combined$value[combined$strategy == "Historical" &
                                                                              combined$Edgar_Class %in% sector_switch ] * diff
combined$value[combined$strategy == "Historical" &
                 combined$Edgar_Class %in% sector_switch &
                 combined$Year == 2022]

file.name <- 'emissions_uganda_WIDE_INPUTS_OUTPUTS_combined_vf.csv'
write.csv(combined,paste0(dir.tableau,file.name),row.names=FALSE)






df <- read.csv(paste0(dir.tableau,'emissions_uganda_WIDE_INPUTS_OUTPUTS_combined_vf.csv'))
df <- subset(df, !(strategy_id == 6008 & 
                     CSC.Subsector == "Buildings (Stationary Combustion)" & 
                     Year >= 2023))

df_22 <- read.csv(paste0(dir.tableau,'raw_emissions_uganda_2022_WIDE_INPUTS_OUTPUTS.csv'))
df_22 <- subset(df_22, strategy_id==6008 & CSC.Subsector=='Buildings (Stationary Combustion)' )

combined <- rbind(df, df_22)

combined <- combined[!duplicated(combined[, c("strategy_id", "CSC.Subsector", "Year", "Gas", "primary_id")]), ]

subset(combined, strategy_id==6008 & CSC.Subsector=='Buildings (Stationary Combustion)' & Year==2022 )

file.name <- 'emissions_uganda_WIDE_INPUTS_OUTPUTS_combined_vf2.csv'
write.csv(combined,paste0(dir.tableau,file.name),row.names=FALSE)



#load data  
data_raw <- read.csv(paste0(dir.output,'WIDE_INPUTS_OUTPUTS.csv')) 

data_raw <- data_raw[ data_raw$time_period>=7, ]
table(data_raw$primary_id)

data_res <- read.csv(paste0(dir.output,'uganda.csv')) 
table(data_res$primary_id)


waste_no2 <- c('emission_co2e_n2o_waso_compost_food','emission_co2e_n2o_waso_compost_sludge',
               'emission_co2e_n2o_waso_compost_yard','emission_co2e_n2o_waso_incineration')

sum(data_raw[waste_no2])
sum(data_res[waste_no2])

common_vars <- intersect(waste_no2, names(data_res))
data_res[common_vars] <- data_raw[common_vars]

sum(data_res[waste_no2])


write.csv(data_res, paste0(dir.output,'uganda_res.csv'))


