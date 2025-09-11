library(data.table)

#lets just bring in the 
#read all folders 
dir.data <- "ssp_modeling/cb/cb_results/"
target_cb_file <- "cba_results.csv"
cb_data <-read.csv(paste0(dir.data,target_cb_file))

cb_chars <- data.frame(do.call(rbind, strsplit(as.character(cb_data$variable), ":")))
colnames(cb_chars) <- c("name","sector","cb_type","item_1","item_2")
cb_data <- cbind(cb_data,cb_chars)
cb_data$value <- cb_data$value/1e9

#remove shifted 
dim(cb_data)
cb_data <- subset(cb_data,grepl("shifted",cb_data$item_2)==FALSE)
dim(cb_data)
ids <- unique(cb_data$variable)
ids <- subset(ids,grepl("shifted2",ids)==FALSE)

#clean  
cb_data <- subset(cb_data,grepl("shifted2",cb_data$variable)==FALSE)
dim(cb_data)

#add Year 
cb_data$Year <- cb_data$time_period+2015

head(cb_data)
table(cb_data$Year)


#change strategy names
cb_data$strategy <- gsub("PFLO:NDC_2", "NDC_2", cb_data$strategy)
cb_data$strategy <- gsub("PFLO:NZ", "Low Emissions Pathway", cb_data$strategy)

table(cb_data$strategy_code)

#create strategy id 
cb_data$strategy_id <- ifelse(cb_data$strategy_code=="PFLO:NDC_2", 6004,
							  ifelse(cb_data$strategy_code=="PFLO:NZ", 6006, cb_data$strategy_code))
cb_data$ids <- paste(cb_data$variable,cb_data$strategy_id,sep=":")


table(cb_data$strategy)
table(cb_data$strategy_id)
table(cb_data$strategy_code)

dir.out <- "ssp_modeling/Tableau/data/"


pib <- fread('data_processing/output_data/GDP.csv')
head(pib)

#write.csv(cb_data,paste0(dir.out,"cb_data.csv"),row.names=FALSE)

cb_data <- merge(cb_data, pib, by.x = "Year", by.y = "year")

# Transform 'value' in cb_data to relative GDP value
cb_data$value_orig <- cb_data$value 
cb_data$value <- (cb_data$value / cb_data$gdp_mmm_usd) * 100

write.csv(cb_data,paste0(dir.out,"cb_data_relative.csv"),row.names=FALSE)
