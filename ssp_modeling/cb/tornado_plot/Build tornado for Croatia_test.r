#Build tornado for Croatia  

#fetch the data 
root<- "/Users/tony/Documents/sisepuede_modeling/ssp_bulgaria/ssp_modeling/cost-benefits/tornado_plot/"
dir.data <- paste0(root,"data/input/")
target_sectors <- c("AG - Crops",
                    "AG - Livestock",
                    "IN - Industrial Processes",
                    "LULUCF - Forest Land",
                    "LULUCF - HWP",
                    "LULUCF - Wetlands",
                    "LULUCF - Cropland",
                    "LULUCF - Grassland",
                    "LULUCF - Settlements",
                    "LULUCF - Other Land",
                    "Waste - Solid Waste",
                    "Waste - Wastewater Treatment")

#load tornado runs 
file.name <- "decomposed_emissions_bulgaria_2022_tornado.csv"
tornado <- read.csv(paste0(dir.data,file.name))
tornado <- subset(tornado,CSC.Subsector%in%target_sectors)
 # print shape
dim(tornado)


#unique(tornado$strategy)
#unique(tornado$CSC.Subsector)

#load baseline runs 
file.name_ref <- "emissions_04_09.csv"
base <- read.csv(paste0(dir.data,file.name_ref))
base <- subset(base,CSC.Subsector%in%target_sectors)
base <- subset(base,Year>=2022)
unique(base$strategy)
#retain only WAM 
#now aggregare at inventory level 
#base first base 
base <- aggregate(list(value=base$value),by=list(primary_id=base$primary_id,
                                                 strategy_id=base$strategy_id,
                                                 strategy=base$strategy),sum)

#then tornado 
tornado  <- aggregate(list(value=tornado$value),by=list(primary_id=tornado$primary_id,
                                                       strategy_id=tornado$strategy_id,
                                                       strategy=tornado$strategy),sum)

#keep only whirpool runs 
whirpool_runs <- subset(unique(tornado$strategy),grepl("Remove",unique(tornado$strategy))==TRUE)
tornado <- subset(tornado,strategy%in%whirpool_runs)
tornado$base_WAM <- 48.64 #subset(base,strategy=="WAM")$value
tornado$emissions_diff <- tornado$value-tornado$base_WAM 

#change names of strategy  
tornado$strategy_code <- gsub("_STRATEGY_WAM from WAM","",tornado$strategy)
tornado$strategy_code <- gsub("Remove TX:","",tornado$strategy_code)


#add strategy names 
strategy_names <- read.csv(paste0(dir.data,"strategy_names.csv")) 
strategy_names$strategy_code <- gsub("TX:","",strategy_names$strategy_code)
#merge 
dim(tornado)
tornado <- merge(tornado,strategy_names,by="strategy_code",all.x=TRUE)
dim(tornado)

#read cost-benefit data 
#lets just bring in the 
#read all folders 
# target_cb_file <- "cost_benefit_results_croatia_2025_05_15.csv"
target_cb_file <- "costs_benefits_sisepuede_results_sisepuede_run_2026-01-12T18;06;55.813694_tornado_raw.csv"

cb_data <-read.csv(paste0(dir.data,target_cb_file))
dim(cb_data)

cb_chars <- data.frame(do.call(rbind, strsplit(as.character(cb_data$variable), ":")))
colnames(cb_chars) <- c("name","sector","cb_type","item_1","item_2")
cb_data <- cbind(cb_data,cb_chars)
cb_data$value <- cb_data$value/1e9

#remove shifted 
# dim(cb_data)
 #cb_data <- subset(cb_data,grepl("shifted",cb_data$item_2)==FALSE)
# dim(cb_data)
# ids <- unique(cb_data$variable)
# ids <- subset(ids,grepl("shifted2",ids)==FALSE)
#clean  
# cb_data <- subset(cb_data,grepl("shifted2",cb_data$variable)==FALSE)
# dim(cb_data)

#add Year 
cb_data$Year <- cb_data$time_period+2015
#create strategy id 
#add_strategy_id 
as <-  read.csv(paste0(dir.data,"ATTRIBUTE_STRATEGY.csv"))
as <- unique(as[,c("strategy_code", "strategy_id")])

dim(cb_data)
cb_data<-merge(cb_data,as,by="strategy_code")
dim(cb_data)
cb_data$ids <- paste(cb_data$variable,cb_data$strategy_id,sep=":")

#create aggregation table for tornado 
cb <- cb_data #subset(cb_data,cb_type=="technical_cost")
cb <- subset(cb,sector%in%c("waso","soil","ippu","lvst","agrc","lndu","lsmm"))
cb <- aggregate(list(Cumulative = cb$value),list(strategy_id=cb$strategy_id, cb_type = cb$cb_type),sum, na.rm=TRUE)
cb_cats <- unique(cb$cb_type)
#change from long to wide format  
library(reshape2)
wide_cb <- dcast(cb, strategy_id ~ cb_type, value.var = "Cumulative")

#wide_cb[,c("strategy_id","technical_cost","technical_savings","consumer_savings")]

#subset(wide_cb,strategy_id%in%c(6005,6161))


#create variables Dave used for Iran 
wide_cb[,"net_benefit"] <- rowSums(wide_cb[,cb_cats])
#create additional benefits 
wide_cb[,"additional_benefits"] <- rowSums(wide_cb[,subset(cb_cats,cb_cats!="technical_cost")])
#create total transformation cost 
wide_cb[,"total_transformation_costs"] <- rowSums(wide_cb[,c("technical_cost","technical_savings","fuel_cost")])

# #update cb_cats 
# cb_cats <- c(cb_cats,"net_benefit","additional_benefits","total_transformation_costs")

# # #now merge both tables 
# #choose a base and estimate differences 
# head(wide_cb)
# base_id <- 6161 #6005 
# base <- subset(wide_cb,strategy_id==base_id) 
# colnames(base) <- paste0(colnames(base),"_ref")
# base[,"strategy_id_ref"] <- NULL 
# #now merge  
# dim(wide_cb)
# wide_cb <- merge(wide_cb,base)
# dim(wide_cb)
# #now estimate differences 

# for (i in 1:length(cb_cats))
# {
#  wide_cb[,cb_cats[i]] <- wide_cb[,paste0(cb_cats[i],"_ref")] - wide_cb[,cb_cats[i]]
# }
# wide_cb[,paste0(cb_cats,"_ref")] <- NULL


#finally merge both files 
dim(tornado)
dim(wide_cb)
tornado <- merge(tornado,wide_cb,by="strategy_id")
dim(tornado)

dir.out <- paste0(root,"Tableau/")
write.csv(tornado,paste0(dir.out,"tornado_plot.csv"),row.names=FALSE)



#this is the processs 
#go grab WAM  in emissions.csv
#rbind that file with this fiñe