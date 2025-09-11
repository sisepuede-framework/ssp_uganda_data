## Cargamos paqueterías
from costs_benefits_ssp.cb_calculate import CostBenefits
import numpy as np
import pandas as pd 
import os 

from costs_benefits_ssp.model.cb_data_model import TXTable,CostFactor,TransformationCost,StrategyInteraction


##---- Definimos directorios

DIR_PATH = "/home/milo/Documents/egtp/sisepuede/CB/ejecuciones_paquete_cb/mexico"

build_path = lambda PATH  : os.path.abspath(os.path.join(*PATH))

### Directorio de salidas de SSP
SSP_RESULTS_PATH = build_path([DIR_PATH,"ssp_salidas"])

### Directorio de configuración de tablas de costos
CB_DEFAULT_DEFINITION_PATH = build_path([DIR_PATH, "cb_factores_costo"])

### Directorio de salidas del módulo de costos y beneficios
OUTPUT_CB_PATH = build_path([DIR_PATH, "cb_resultados"])

### Directorio de datos requeridos paragenerar el archivo tornado_plot_data_QA_QC.csv
QA_PATH = build_path([DIR_PATH, "edgar_cw"])

## Cargamos los datos
ssp_data = pd.read_csv(os.path.join(SSP_RESULTS_PATH, "mexico.csv"))
att_primary = pd.read_csv(os.path.join(SSP_RESULTS_PATH, "ATTRIBUTE_PRIMARY.csv"))
att_strategy = pd.read_csv(os.path.join(SSP_RESULTS_PATH, "ATTRIBUTE_STRATEGY.csv"))

#ssp_data = ssp_data.drop(columns = ["totalvalue_enfu_fuel_consumed_inen_fuel_hydrogen", "totalvalue_enfu_fuel_consumed_inen_fuel_furnace_gas"])

# Definimos la estrategia baseline
strategy_code_base = "BASE"

## Instanciamos un objeto de la clase CostBenefits 
cb = CostBenefits(ssp_data, att_primary, att_strategy, strategy_code_base)

## El método export_db_to_excel guarda la configuración inicial de las tablas de costos a un archivo excel. 
### Cada pestaña representa una tabla en la base de datos del programa de costos y beneficios.
CB_DEFAULT_DEFINITION_FILE_PATH = os.path.join(CB_DEFAULT_DEFINITION_PATH, "cb_config_params_mexico.xlsx")

#cb.export_db_to_excel(CB_DEFAULT_DEFINITION_FILE_PATH)
cb.load_cb_parameters(CB_DEFAULT_DEFINITION_FILE_PATH)

#------ System Costs
## Calculamos los system costs para todas las estrategias
results_system = cb.compute_system_cost_for_all_strategies()

#-------Technical Costs
## Calculamos los technical costs para todas las estrategias
results_tx = cb.compute_technical_cost_for_all_strategies()

# Combina resultados
results_all = pd.concat([results_system, results_tx], ignore_index = True)

#-------------POST PROCESS SIMULATION RESULTS---------------
# Post process interactions among strategies that affect the same variables
results_all_pp = cb.cb_process_interactions(results_all)

# SHIFT any stray costs incurred from 2015 to 2025 to 2025 and 2035
#results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)

# Guardamos los resultados de CBA
OUTPUT_CB_FILE_PATH = os.path.join(OUTPUT_CB_PATH, "cost_benefit_results_mexico.csv")

results_all_pp.to_csv(OUTPUT_CB_FILE_PATH, index = False)

###----------- QUALITY ASSURANCE ANALYSIS ---------#

#filter subsector totals
ids = ["primary_id", "region", "time_period"]
subsector_totals = [i for i in ssp_data.columns if "co2e_subsector_total" in i]

#create ch4 totals  
subsector_totals_ch4 = ["emission_co2e_ch4_agrc",
                           "emission_co2e_ch4_ccsq",
                          "emission_co2e_ch4_entc",
                          "emission_co2e_ch4_fgtv",
                          "emission_co2e_ch4_frst",
                          "emission_co2e_ch4_inen",
                          "emission_co2e_ch4_ippu",
                          "emission_co2e_ch4_lsmm",
                          "emission_co2e_ch4_lvst",
                          "emission_co2e_ch4_scoe",
                          "emission_co2e_ch4_trns",
                          "emission_co2e_ch4_trww",
                          "emission_co2e_ch4_waso"]

ch4 = {i:i.split("_")[-1] for i in subsector_totals_ch4}

#read mapping  
EMMISIONS_TARGETS_FILE_PATH = os.path.join(QA_PATH, "emission_targets_mexico.csv")
te_all = pd.read_csv(EMMISIONS_TARGETS_FILE_PATH)


target_country = "MEX"
te_all = te_all[["Subsector","Gas","Vars","Edgar_Class",target_country]].rename(columns = {target_country : "tvalue"})

data = ssp_data[ids + subsector_totals]

for ch_subsector, subsector in ch4.items():
    edgar_vars = te_all.query(f"Subsector == '{subsector}' and Gas=='ch4'")["Vars"].values[0].split(":")
    data[ch_subsector] = ssp_data[edgar_vars].sum(axis = 1)

#estimate totals emissions
data["emission_co2e_total"] = data[subsector_totals].sum(axis = 1)
data["emission_co2e_ch4_total"] = data[subsector_totals_ch4].sum(axis = 1)

# estimate cumulative emissions 
data = data.drop(columns="time_period").groupby(["primary_id", "region"]).sum().reset_index()

#add reference 
estrategia_base = 0
data_0 = data.query(f"primary_id == {estrategia_base}").drop(columns=["primary_id", "region"])
data_diff = data.set_index(["primary_id", "region"]) - data_0.to_numpy()
data_diff.columns = [f"{i}_diff" for i in data_diff.columns ]

data = pd.concat([data.set_index(["primary_id", "region"]), data_diff], axis = 1).reset_index()

data = data.merge(right = att_primary, on="primary_id").merge(right = att_strategy, on = "strategy_id")
data_backup = data.copy()

#now add cost & benefits 
cb_data = results_all_pp.copy()
#cb_data = cb_data.query("variable!='cb:agrc:crop_value:crops_produced:vegetables'").reset_index(drop = True)
cb_chars = pd.DataFrame([i for i in cb_data.variable.apply(lambda x : x.split(":"))], columns=("name","sector","cb_type","item_1","item_2"))
cb_data = pd.concat([cb_data, cb_chars], axis = 1)

cb_data["value"] /= 1e9 #making all BUSD

### Excluimos las variables de costo que usen las siguientes funciones de costo:
# * cb_agrc_lvst_productivity 
# * cb_entc_reduce_losses
# * cb_ippu_inen_ccs
cb_var_excluye = cb.get_technical_costs()[cb.get_technical_costs().cb_function.isin(["cb_agrc_lvst_productivity", "cb_entc_reduce_losses", "cb_ippu_inen_ccs"])].output_variable_name.values.tolist()

# aggregate
cdata = cb_data.groupby(["sector", "cb_type", "strategy_code"]).agg({"value" : "sum"}).reset_index()

## Remueve algunas categorías que están ocasionando problemas
### inen en sector_specific
#cdata = cdata.query("not(cb_type=='sector_specific' and sector=='inen')").reset_index(drop=True)


id_vars = ["strategy","strategy_id","primary_id","region","strategy_code"]
fvars = ["emission_co2e_total_diff","emission_co2e_ch4_total_diff"]
data = data[id_vars + fvars]

#add cb categories  
data_by_cb_type = cdata.groupby(["strategy_code", "cb_type"]).agg({"value" : "sum"})\
                        .reset_index().pivot(index='strategy_code', 
                                            columns='cb_type', 
                                            values='value')\
                        .replace(np.nan, 0.0)\
                        .reset_index()


data = data.merge(right=data_by_cb_type, on = "strategy_code")
data = data.drop(columns=["emission_co2e_ch4_total_diff"])

#now create columns with marginal values  
cb_cats = cdata["cb_type"].unique()
data[[f"{i}_mi_CO2e"for i in cb_cats]] = (data[cb_cats]/abs(data["emission_co2e_total_diff"].to_numpy()[:,np.newaxis]))*1000

#create net benefits 
data["net_benefit"] = data[cb_cats].sum(axis = 1)
data["net_benefit_mi_CO2e"] = (data["net_benefit"]/abs(data["emission_co2e_total_diff"]))*1000

#create additional benefits 
data["additional_benefits"] = data[[i for i in cb_cats if i != "technical_cost"]].sum(axis = 1)

#create total transformation cost 
data["total_transformation_costs"] = data[ ["technical_cost","technical_savings","fuel_cost"]].sum(axis = 1)
data["total_transformation_costs_mi_CO2e"] = (data["total_transformation_costs"]/abs(data["emission_co2e_total_diff"]))*1000

# Visualización
data[["strategy", "emission_co2e_total_diff", "net_benefit", "net_benefit_mi_CO2e"]]

#read strategy names
#STRATEGY_NAMES_FILE_PATH = os.path.join(QA_PATH, "strategy_names.csv")
#strategy_names = pd.read_csv(STRATEGY_NAMES_FILE_PATH)
#strategy_names["strategy_code"] = strategy_names["strategy_code"].apply(lambda x: x.replace("TX:",""))

OUTPUT_CB_FILE_PATH = os.path.join(OUTPUT_CB_PATH, "mexico_QA_QC_nuevo.csv")

data.to_csv(OUTPUT_CB_FILE_PATH, index = False)


### Generamos el excel desagregado para el QA
from cb_qa_excel_builder import QAExcelBuilder
import re 
from typing import List
from costs_benefits_ssp.cb_calculate import TransformationCost
import copy

def get_all_vars_on_diff_var(diff_var_pattern : str, cb_var_list : List[str]) -> List[str]:
    return [cb_var for cb_var in cb_var_list if  re.match(re.compile(diff_var_pattern), cb_var)]


cb_var_list = cb_data.difference_variable.unique()

cb_variables_computadas = list(cb_data.variable.unique())

mapping_cb_diff_var = {i : get_all_vars_on_diff_var(cb.get_cb_var_fields(i).difference_variable.replace("*", ".*"), cb_var_list) for i in cb.get_all_cost_factor_variables().output_variable_name if i in cb_variables_computadas}
mapping_cb_diff_var_to_test = {i : cb.get_cb_var_fields(i).difference_variable.replace("*", ".*") for i in cb.get_all_cost_factor_variables().output_variable_name if i in cb_variables_computadas}

vars_to_update = {i:mapping_cb_diff_var_to_test[i] for i,j in mapping_cb_diff_var.items() if j[0] != mapping_cb_diff_var_to_test[i]}

for i,j in vars_to_update.items():
    mapping_cb_diff_var[i] = [string for string in cb.ssp_list_of_vars if  re.match(re.compile(j), string)]

mapping_cb_benefits_aggregated = {i:cb_data.query(f"cb_type=='{i}'").variable.unique().tolist() for i in cb_chars.cb_type.unique()}


### Agregamos valores de emisiones

additional_ssp_var = ["time_period"]

for i,j in mapping_cb_diff_var_to_test.items():
    additional_ssp_var.extend(mapping_cb_diff_var[i])

additional_ssp_var = list(set(additional_ssp_var))

#additional_ssp_var = ["time_period", "energy_consumption_inen_total", 
#                      "energy_consumption_scoe_total", "area_lndu_improved_croplands", 
#                      "energy_consumption_trns_rail_passenger_electricity", "vehicle_distance_traveled_trns_road_heavy_freight_electricity",
#                      "nemomod_entc_discounted_capital_investment_fp_ammonia_production", "nemomod_entc_discounted_capital_investment_fp_hydrogen_electrolysis"]

data_baseline = cb.ssp_data.query("strategy_code=='BASE'")[[i for i in cb.ssp_data.columns if "emission_co2e_subsector_total_" in i] + additional_ssp_var].set_index("time_period")

### Agregramos variables de cb
#all_cb_diff_var = []

#for i in mapping_cb_diff_var.values():
#    all_cb_diff_var.extend(i)

#data_baseline_cb = cb_data[cb_data.difference_variable.isin(all_cb_diff_var)]\
#                                    .query("strategy_code=='PFLO:M8_EC'")[["time_period", "difference_variable", 'variable_value_baseline']]\
#                                    .pivot_table(index = ["time_period"], columns = ["difference_variable"], values = ["variable_value_baseline"])

#data_baseline_cb.columns = data_baseline_cb.columns.droplevel()

#data_baseline = pd.concat([data_baseline, data_baseline_cb], axis = 1)


### Agregamos valores de costos y beneficios
cb_cost_factors = pd.DataFrame({ i: [cb.get_cb_var_fields(i).multiplier, cb.get_cb_var_fields(i).multiplier_unit, cb.get_cb_var_fields(i).annual_change] for i in mapping_cb_diff_var.keys()})


qa_builder = QAExcelBuilder(
                    time_init = 7,
                    time_end = 35,
                    mapping_cb_diff_var = mapping_cb_diff_var,
                    cb_cost_factors = cb_cost_factors
                    )


for strategy_ssp in cb_data.strategy_code.unique():

    print(strategy_ssp)
    ### Obten las variables de costo de technical cost
    ## Get cb variables that will be evaluated on system cost
    technical_cost_cb = cb.session.query(TransformationCost).all()
            
    ## Get mapping between cb_var by technical cost and transformation 
    cb_tech_cost_mapping_to_tx = pd.read_sql(cb.session.query(TransformationCost).statement, cb.session.bind) 
    cb_tech_cost_mapping_to_tx = dict(cb_tech_cost_mapping_to_tx[["output_variable_name", "transformation_code"]].to_records(index = False))
            
    ## Get all transformations in technical cost
    all_tx_in_technical_cost = [i.transformation_code for i in technical_cost_cb]

    ## Get transformation inside on strategy_code_tx
    tx_technical_cost_in_strategy = list(set(all_tx_in_technical_cost).intersection(cb.strategy_to_txs[strategy_ssp]))
    excluye_cb_variables = [i for i,j  in cb_tech_cost_mapping_to_tx.items() if not j in tx_technical_cost_in_strategy]

    mapping_cb_benefits_aggregated_strategy = copy.deepcopy(mapping_cb_benefits_aggregated)

    for i,j in mapping_cb_benefits_aggregated_strategy.items():
        for excluye in excluye_cb_variables:
            if excluye in j:
                j.remove(excluye)


    ## Construye dataframes de comparación
    data_pathway = cb.ssp_data.query(f"strategy_code=='{strategy_ssp}'")[[i for i in cb.ssp_data.columns if "emission_co2e_subsector_total_" in i] + additional_ssp_var].set_index("time_period")


    #data_pathway_cb = cb_data[cb_data.difference_variable.isin(all_cb_diff_var)]\
    #                                    .query(f"strategy_code=='{strategy_ssp}'")[["time_period", "difference_variable", 'variable_value_pathway']]\
    #                                    .pivot_table(index = ["time_period"], columns = ["difference_variable"], values = ["variable_value_pathway"])

    #data_pathway_cb.columns = data_pathway_cb.columns.droplevel()

    #data_pathway = pd.concat([data_pathway, data_pathway_cb], axis = 1)
    data_pathway = data_pathway.loc[:,~data_pathway.columns.duplicated()].copy()

    strategy_ssp =  strategy_ssp.split(":")[-1]

    df_cumulative_categories = data.query(f"strategy == '{strategy_ssp}'")[mapping_cb_benefits_aggregated.keys()]

    emission_co2e_total_diff = data.query(f"strategy == '{strategy_ssp}'")["emission_co2e_total_diff"].values[0]

    qa_builder.set_mapping_cb_benefits_aggregated(mapping_cb_benefits_aggregated_strategy)

    qa_builder.compute_strategy_sheet(strategy_ssp, data_baseline, data_pathway, df_cumulative_categories, emission_co2e_total_diff)


### Agregamos los datos del QA de python

qa_builder.wb.active = qa_builder.wb.sheetnames.index("Sheet")
qa_builder.ws = qa_builder.wb.active


qa_builder.ws.append(list(data.columns))

for row in data.values.tolist():
    qa_builder.ws.append(row)

ss_sheet = qa_builder.wb['Sheet']
ss_sheet.title = 'QA_python'

qa_builder.wb.save("QA_QC_mexico.xlsx")


