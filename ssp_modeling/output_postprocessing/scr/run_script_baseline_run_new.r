################################################################################
# This script runs the intertemporal decomposition for the baseline run
################################################################################

te_all<-read.csv("ssp_modeling/output_postprocessing/data/emission_targets_bulgaria.csv")
# filter to keep only the subsectors of interest
#te_all <- subset(te_all,Subsector%in%c( "lvst","lsmm","agrc","ippu","waso","trww","frst","lndu","soil"))
target_country <- "BGR" # Bulgaria
te_all<-te_all[,c("Subsector","Gas","Vars","Edgar_Class",target_country)]
te_all[,"tvalue"] <- te_all[,target_country]
te_all[,target_country] <- NULL
target_vars <- unlist(strsplit(te_all$Vars,":"))

# modification of AG - Livestock:N2O subsector matching
te_all$Vars[3] <- "emission_co2e_n2o_lsmm_direct_anaerobic_digester:emission_co2e_n2o_lsmm_direct_anaerobic_lagoon:emission_co2e_n2o_lsmm_direct_composting:emission_co2e_n2o_lsmm_direct_daily_spread:emission_co2e_n2o_lsmm_direct_deep_bedding:emission_co2e_n2o_lsmm_direct_dry_lot:emission_co2e_n2o_lsmm_direct_incineration:emission_co2e_n2o_lsmm_direct_liquid_slurry:emission_co2e_n2o_lsmm_direct_paddock_pasture_range:emission_co2e_n2o_lsmm_direct_poultry_manure:emission_co2e_n2o_lsmm_direct_storage_solid:emission_co2e_n2o_lsmm_indirect_anaerobic_digester:emission_co2e_n2o_lsmm_indirect_anaerobic_lagoon:emission_co2e_n2o_lsmm_indirect_composting:emission_co2e_n2o_lsmm_indirect_daily_spread:emission_co2e_n2o_lsmm_indirect_deep_bedding:emission_co2e_n2o_lsmm_indirect_dry_lot:emission_co2e_n2o_lsmm_indirect_incineration:emission_co2e_n2o_lsmm_indirect_liquid_slurry:emission_co2e_n2o_lsmm_indirect_paddock_pasture_range:emission_co2e_n2o_lsmm_indirect_poultry_manure:emission_co2e_n2o_lsmm_indirect_storage_solid"


data_all<-read.csv(paste0(dir.output,output.file))
rall <- unique(data_all$region)
#check primary ids
table(data_all$primary_id)

#check time periods
table(data_all$time_period)

#set params of rescaling function
initial_conditions_id <- "_0"
time_period_ref <- 7

dim(data_all)
data_all <- subset(data_all,time_period>=time_period_ref)
dim(data_all)

#revise which sector-gas ids are zero at baseline 
te_all$simulation <- 0
for (i in 1:nrow(te_all))
 {
    #i <- 1
    vars <- unlist(strsplit(te_all$Vars[i],":"))
    if (length(vars)>1) {
    te_all$simulation[i] <- as.numeric(rowSums(data_all[data_all$primary_id==gsub("_","",initial_conditions_id) &  data_all$time_period==time_period_ref,vars]))
    } else {
     te_all$simulation[i] <- as.numeric(data_all[data_all$primary_id==gsub("_","",initial_conditions_id) &  data_all$time_period==time_period_ref,vars])   
    }
  }
te_all$simulation <- ifelse(te_all$simulation==0 & te_all$tvalue>0,0,1)
correct<- aggregate(list(factor_correction=te_all$simulation),list(Edgar_Class=te_all$Edgar_Class),mean)
te_all <- merge(te_all,correct,by="Edgar_Class")
te_all$tvalue <- te_all$tvalue/te_all$factor_correction
te_all$simulation<-NULL 
te_all$factor_correction<-NULL
te_all$Edgar_Class<-NULL

#now run

source("ssp_modeling/output_postprocessing/scr/intertemporal_decomposition.r")
z<-1
rescale(z,rall,data_all,te_all,initial_conditions_id,dir.output,time_period_ref)

print('Finish:run_script_baseline_run_new_asp process')
