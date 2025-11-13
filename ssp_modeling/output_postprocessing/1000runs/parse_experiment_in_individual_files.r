#load libraries

full_sim <- fread(paste0(run,file.name))

all_ids <- unique(full_sim$primary_id)

for (i in 1:length(all_ids))
{
#i<-1 
pivot <- subset(full_sim,primary_id==all_ids[i])
fwrite(pivot,paste0('ssp_modeling/output_postprocessing/1000runs/ensemble_data/meta/',all_ids[i],".csv"),row.names=FALSE)
}

print("Parsing complete")
