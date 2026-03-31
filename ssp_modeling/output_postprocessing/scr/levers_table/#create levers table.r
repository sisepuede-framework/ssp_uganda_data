#create levers table for Uganda 

#load levers table
#attach transformations descriptions 

#read the transformation table
dir.output  <- paste0("ssp_modeling/ssp_run_output/",run,"/")
ssp_table <- read.csv(paste0(dir.output,"tableau_levers_table.csv" ))
ssp_table$transformation_code <- gsub("TFR:","",ssp_table$transformer_code)
#read descriptions 
desp <- read.csv('ssp_modeling/output_postprocessing/data/levers/ssp_descriptions.csv')

#read stakeholder codes 
scodes <- read.csv("ssp_modeling/output_postprocessing/data/levers/stakeholder_codes.csv")
scodes$transformation_code <- gsub("TX:","",scodes$transformation_code)


#merge 
dim(ssp_table)
dim(desp)
ssp_table <- merge(ssp_table,desp,by="transformation_code")
dim(ssp_table)
ssp_table <- merge(ssp_table,scodes[,c("transformation_code","transformation_name_stakeholder","Sector..output.","Subsector..output.","Example.government.policies")],by="transformation_code")
dim(ssp_table)

write.csv(ssp_table, paste0("ssp_modeling/Tableau/data/tableau_levers_table_complete_",region,".csv"), row.names = FALSE)


print("Levers table created")