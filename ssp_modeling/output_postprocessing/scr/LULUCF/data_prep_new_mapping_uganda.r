# This script prepares the data for emissions mapping in Uganda
file.name <- paste0(region,".csv")
iso_code3 <- iso_code3
Country <- region

#load last crosswalk
mapping <- read.csv('ssp_modeling/output_postprocessing/data/LULUCF/crosswalk_inventory_to_sisepeude_20260220.csv')
mapping$Subsector_Category <- paste(mapping$aggregation_category,
                             mapping$gas,sep=":")

mapping <- mapping %>%
  rename(
    Sector = aggregation_category_2,
    Subsector = aggregation_category,
    Gas = gas,
    Vars = sisepuede_fields
  )

mapping<-mapping[,c("Sector","Subsector","Gas","Subsector_Category", "Vars")]


# add edgar
edgar <- read.csv('ssp_modeling/output_postprocessing/data/LULUCF/inventory_trajectories.csv')

table(edgar$CSC.Subsector)

#load data  
data <- fread(paste0(dir.output,file.name)) %>% as.data.frame()
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
colnames(mapping)[colnames(mapping) == "Subsector"] <- "CSC.Subsector"
data_new <- merge(data_new,mapping,by="ids")

#now aggregare at inventory level 
data_new <- aggregate(list(value=data_new$value),by=list(primary_id=data_new$primary_id,
                                             time_period=data_new$time_period,
                                             Subsector_Category=data_new$Subsector_Category,
                                             CSC.Subsector=data_new$CSC.Subsector,
                                             CSC.Sector=data_new$Sector),sum)
table(data_new$Subsector_Category)
table(data_new$CSC.Sector)


data_new$Year <- data_new$time_period + 2015
data_new$Gas <- do.call("rbind",strsplit(data_new$Subsector_Category,":"))[,2]

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
id_varsEd <- c("Code","CSC.Sector","CSC.Subsector","Gas","Subsector_Category")
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

table(data_new$CSC.Subsector)
table(data_new$strategy)


#write file
dir.tableau <- paste0("ssp_modeling/Tableau/data/")
file.name <- paste0("emissions_", region, "_", year_ref, "_", output.file)

fwrite(data_new,paste0(dir.tableau,'raw_',file.name),row.names=FALSE)


print(paste0('Finish:data_prep_new_mapping process'))
