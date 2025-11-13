#Intertemporal decomposition for 1000 runs ensamble LA
library(data.table)

#load emissions targets 
te_all<-read.csv('ssp_modeling/output_postprocessing/data/emission_targets_uganda_2019.csv')

target_country <- "UGA"
te_all<-te_all[,c("Subsector","Gas","Vars","Subsector_Category","ssp_subsector",target_country)]
te_all[,"tvalue"] <- te_all[,target_country]
te_all[,target_country] <- NULL
#target_vars <- unlist(strsplit(te_all$Vars,":"))

#output.folder <- paste0(root,"LHC_sample/2025_02_11/meta/")
output.folder <- 'ssp_modeling/output_postprocessing/1000runs/ensemble_data/meta/'
dir.output <- 'ssp_modeling/output_postprocessing/1000runs/ensemble_data/meta_decomposed/'

files_names <- list.files(output.folder,".csv")
# removes <- c(404928,404929,404930,404931,404932,404933,404934,404935,404936,404937,404938,404939,404940,404941,404942,404943,404944,404945,404946,404947,404948)
# removes <- paste0(as.character(removes),".csv")
# files_names <- subset(files_names,!(files_names%in%removes))

#for (run in 1:length(files_names))
chunks <- split(1:length(files_names), cut(1:length(files_names), 10, labels = FALSE))

for (run in chunks[[10]])
{
    #run <- 1
    output.file <- files_names[run]
    #output.file <- "403327.csv"
    data_all <- read.csv(paste0(output.folder,output.file))
    data_all[is.na(data_all)] <- 0
    rall <- unique(data_all$region)

    #set params of intertemporal decomposition function

    initial_conditions_id <- unique(data_all$primary_id)
    time_period_ref <- 4

    dim(data_all)
    data_all <- subset(data_all,time_period>=time_period_ref)
    dim(data_all)

    source('ssp_modeling/output_postprocessing/1000runs/intertemporal_function_baseline_mapping_timeref.r')
    z<-1
    rescale(z,rall,data_all,te_all,initial_conditions_id,dir.output,time_period_ref,run)    
}

#emission_co2e_co2_ippu_production_metals


#now collect all decomposed runs and the experimental files 
setDTthreads(0)
files <- list.files(dir.output, pattern = "\\.csv$", full.names = TRUE)
dt <- rbindlist(lapply(files, fread), use.names = TRUE, fill = TRUE)
dim(dt)

# #remove weird runs
#  weird_runs <- c(438570, 438641, 439137, 438634, 438620, 439050, 438889, 438572, 438901,
#                  439011, 439249, 439362, 438994, 438885, 438886, 438884, 438888, 438887,
#                  439307, 438980, 438631, 439160, 4393547)
# dt <- subset(dt,!(primary_id%in%weird_runs))
# dim(dt)


# merge with attributes
run <- "ssp_modeling/ssp_run_output/sisepuede_run_2025-11-12t22;19;28.194097/"
att <- fread(paste0(run, 'ATTRIBUTE_PRIMARY.csv'))
dt <- merge(dt, att, by="primary_id", all.x=TRUE)

table(att$strategy_id, exclude = NULL)

#write database
out_path <- 'ssp_modeling/output_postprocessing/1000runs/ensemble_data/out/sisepuede_results_IDE_2025-11-12t22;19;28.194097.csv'
fwrite(dt, out_path)



subsectors <- colnames(dt)[grepl("^emission_co2e_subsector_total_", colnames(dt))]
subsectors

dt$emissions_total <- rowSums(dt[,..subsectors], na.rm=TRUE)

dt[, sum(emissions_total), by=.(time_period, primary_id)][order(time_period)]

# plot emissions_total over time for each primary_id
library(ggplot2)

# ensure primary_id is a factor for grouping
dt[, primary_id := as.factor(primary_id)]

dt$emission_co2e_subsector_total_IPPU <- dt$emission_co2e_subsector_total_IPPU + dt$emission_co2e_co2_ippu_production_metals

# simple line plot with one line per primary_id (transparent to reduce overplotting)
p <- ggplot(dt, aes(x = time_period, y = emissions_total, 
                group = primary_id, 
                color=as.factor(strategy_id))) +
    geom_line(alpha = 0.3, linewidth = 0.4) +
    labs(x = "Time period", y = "Total emissions (CO2e)", title = "Emissions total over time by primary_id") +
    theme_minimal()

p



#upload to S3
#aws s3 cp "/Users/fabianfuentes/git/ssp_uganda_data/ssp_modeling/output_postprocessing/1000runs/ensemble_data/out/sisepuede_results_IDE_2025-11-12t22;19;28.194097.csv" 's3://sisepuede-data/transfers/sisepuede_run_2025-11-12t22;19;28.194097/'