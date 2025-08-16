#drivers
output.folder <- dir.output
dir.data <- paste0(output.folder)
file.name <- paste0(region,".csv")

#load turkey data  
data <- read.csv(paste0(dir.data,file.name)) 
data <- subset(data,region==region)

# temporal correction baseline condition BaU
table(data$primary_id)

#subset data for Ali, 

#emission vars only 
id_vars <-c('region','time_period',"primary_id")
vars <- subset(colnames(data),!(colnames(data)%in%id_vars))
target_vars <- subset(vars,grepl("co2e_",vars)==TRUE)



#read simulation 
data<-data.table::data.table(data)
DT.m1 = melt(data, id.vars = id_vars,
                   measure.vars = vars,
             )
DT.m1 <- data.frame(DT.m1)
DT.m1$variable <- as.character(DT.m1$variable)
sapply(DT.m1,class)
#unique(DT.m1$variable)

#
#variables <- data.frame(vars=unique(DT.m1$variable))
#write.csv(variables,r"(C:\Users\edmun\OneDrive\Edmundo-ITESM\3.Proyectos\51. WB Decarbonization Project\India_CaseStudy\new_runs\Tableau\vars.csv)", row.names=FALSE)


#now read drivers taxonomy. 
drivers <- read.csv("ssp_modeling/output_postprocessing/data/driver_variables_taxonomy_20240117.csv")

#change column name to taxonomy 
drivers$variable <- drivers$field
drivers$field <- NULL 


#merge
 dim(DT.m1)
 DT.m1 <- subset(DT.m1,variable%in%unique(drivers$variable))
 dim(DT.m1)
 
#
#merge  
 dim(DT.m1)
 test2 <- merge(DT.m1,data.table(drivers),by="variable")
 dim(test2)

#
#
test2$Year <- test2$time_period + 2015 
test2$time_period <- NULL 
test2 <- subset (test2,Year>=2023)

#read attribute primary
att <- read.csv(paste0(output.folder,"ATTRIBUTE_PRIMARY.csv"))
head(att)

#merge 
dim(test2)
test2 <- merge(test2,att,by="primary_id")
dim(test2)


#merge stratgy atts 
atts <- read.csv(paste0(output.folder,"ATTRIBUTE_STRATEGY.csv"))

#merge 
dim(test2)
test2 <- merge(test2,atts[c("strategy_id","strategy")],by="strategy_id")
dim(test2)

# Stratey ids 
table(test2$strategy_id)

test2$Units <- "NA"
test2$Data_Type <- "sisepuede simulation"
test2$iso_code3<- iso_code3
test2$Country <- region
test2$region <- NULL
test2$subsector_total_field <- NULL
#test2$model_variable <- NULL
test2$gas <- NA  

test2$model_variable_information <- NULL
test2$output_type<- "drivers"

#create an additional sector variable for energy  
energy_vars <- data.frame(variable=subset(unique(test2$variable),grepl("energy",unique(test2$variable))==TRUE ))
energy_vars$energy_subsector <-"TBD"
energy_vars$energy_subsector <- ifelse(grepl("ccsq",energy_vars$variable)==TRUE,"Carbon Capture and Sequestration",energy_vars$energy_subsector )
energy_vars$energy_subsector <- ifelse(grepl("inen",energy_vars$variable)==TRUE,"Industrial Energy",energy_vars$energy_subsector )
energy_vars$energy_subsector <- ifelse(grepl("entc",energy_vars$variable)==TRUE,"Power(electricity/heat)",energy_vars$energy_subsector )
energy_vars$energy_subsector <- ifelse(grepl("trns",energy_vars$variable)==TRUE,"Transportation",energy_vars$energy_subsector )
energy_vars$energy_subsector <- ifelse(grepl("scoe",energy_vars$variable)==TRUE,"Buildings",energy_vars$energy_subsector )

#merge energy vars with test2 
dim(test2)
test2 <- merge(test2,energy_vars,by="variable", all.x=TRUE)
dim(test2)

test2 <- test2[order(test2$strategy_id,test2$model_variable,test2$subsector,test2$category_value,test2$Year),]
#saved_data <- test2
#test2 <- saved_data
##
test2$ids <- paste(test2$variable,test2$subsector,test2$category_value,test2$strategy_id,sep=":")
ids_all <- unique(test2$ids)
test2$value_new <- 0
for (i in 1:length(ids_all))
{
if (grepl("prod_ippu_glass_tonne:IPPU",ids_all[i])==TRUE)
{
 pivot <-subset(test2,ids==ids_all[i] & test2$Year%in%c(2022:2030,2070))[,c("value","Year")]
 pivot$value[pivot$Year==2050] <- pivot$value[pivot$Year==2030]*1.5
 pivot <- subset(pivot,Year%in%c(2022:2025,2070))
 inter_fun <- approxfun(x=as.numeric(pivot$Year), y=as.numeric(pivot$value), rule = 2:1)
 test2[test2$ids==ids_all[i],"value_new"] <- inter_fun(test2[test2$ids==ids_all[i],"Year"])
}
if (grepl("prod_ippu_metals_tonne:IPPU",ids_all[i])==TRUE)
{
 pivot <-subset(test2,ids==ids_all[i] & test2$Year%in%c(2022:2030,2070))[,c("value","Year")]
 pivot$value[pivot$Year==2050] <- pivot$value[pivot$Year==2030]*2.0
 pivot <- subset(pivot,Year%in%c(2022:2025,2070))
 inter_fun <- approxfun(x=as.numeric(pivot$Year), y=as.numeric(pivot$value), rule = 2:1)
 test2[test2$ids==ids_all[i],"value_new"] <- inter_fun(test2[test2$ids==ids_all[i],"Year"])
}
if (grepl("prod_ippu_rubber_and_leather_tonne:IPPU",ids_all[i])==TRUE)
{
 pivot <-subset(test2,ids==ids_all[i] & test2$Year%in%c(2022:2030,2070))[,c("value","Year")]
 pivot$value[pivot$Year==2050] <- pivot$value[pivot$Year==2030]*1.5
 pivot <- subset(pivot,Year%in%c(2022:2025,2070))
 inter_fun <- approxfun(x=as.numeric(pivot$Year), y=as.numeric(pivot$value), rule = 2:1)
 test2[test2$ids==ids_all[i],"value_new"] <- inter_fun(test2[test2$ids==ids_all[i],"Year"])
}
if (grepl("prod_ippu_textiles_tonne:IPPU",ids_all[i])==TRUE)
{
 pivot <-subset(test2,ids==ids_all[i] & test2$Year%in%c(2022:2030,2070))[,c("value","Year")]
 pivot$value[pivot$Year==2050] <- pivot$value[pivot$Year==2030]*1.5
 pivot <- subset(pivot,Year%in%c(2022:2025,2070))
 inter_fun <- approxfun(x=as.numeric(pivot$Year), y=as.numeric(pivot$value), rule = 2:1)
 test2[test2$ids==ids_all[i],"value_new"] <- inter_fun(test2[test2$ids==ids_all[i],"Year"])
}
 else {}
} 
#subsitute value 
test2$value <- ifelse(test2$value_new==0,test2$value,test2$value_new)
test2$value_new <- NULL 

#write
#test2 <- subset(test2,strategy_id!=6005)

#write file
dir.tableau <- paste0("ssp_modeling/Tableau/data/")
file.name <- paste0("drivers_",region,"_",output.file)

write.csv(test2,paste0(dir.tableau,file.name), row.names=FALSE)

paste0("emissions_",region,"_raw_",output.file)

print('Finish: data_prep_drivers process')
