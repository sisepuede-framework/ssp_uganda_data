"""Shared data from MEMD
"""
from typing import *
import numpy as np
import os, os.path
import pandas as pd
import pathlib
import utils.classes as cl





#########################
#   GLOBAL VARIABLES    #
#########################

##  FIELDS 

# consumption by fuel
_FIELD_CBF_SECTOR = "Sector"

# fuel shares map
_FIELD_FSM_AGG_GROUP = "aggregation_group"
_FIELD_FSM_FUEL = "fuel"
_FIELD_FSM_FUEL_TABLE = "fuel_table"



# current
_PATH_CUR = pathlib.Path(os.path.abspath(__file__))
_PATH_DATA_MEMD = _PATH_CUR.parents[1].joinpath("input_data", "memd")

# dependent paths
_PATH_CONSUMP_BY_FUEL = _PATH_DATA_MEMD.joinpath("final_energy_consumption_by_fuel_uganda_2023.csv")
_PATH_TABLE_40 = _PATH_DATA_MEMD.joinpath("memd_sa2023_table_40.csv")




###################
#    FUNCTIONS    #
###################


def get_df_consump_by_fuel(
) -> pd.DataFrame:
    """Get and prepare the final consumption by fuel data frame.
    """
    df_out = (
        pd.read_csv(_PATH_CONSUMP_BY_FUEL, )
        .rename(
            columns = {
                "Gas/Diesel Oil": "Diesel"
            }
        )
    )

    # ADD SOME COMPOSITE FIELDS

    dict_new_fields = {
        "Electricity_and_hydro": ["Electricity", "Hydro"],
        "Kerosene": ["Jet Kerosene", "Other Kerosene"],
        "Solid biomass": ["Wood fuel", "Bagasse", "Rice husks", "Other vegetal waste", "Animal waste", "Biomass briquettes", "Charcoal"],
    }

    for k, v in dict_new_fields.items():
        df_out[k] = df_out[v].sum(axis = 1, )

    return df_out
    
     



def get_dict_fuel_shares_map(
) -> pd.DataFrame:
    """Get the dictionary that maps fuels to fuel groups
    """
    df = [
        ["Diesel", "Diesel", "Oil Products Total"],
        ["Kerosene", "Kerosene", "Oil Products Total"],
        ["Oil", "Fuel oil", "Oil Products Total"],
        ["Gasoline", "Gasoline", "Oil Products Total"],
        ["Hydrocarbon_Gas_Liquids", "LPG", "Oil Products Total"],
        ["Electricity", "Electricity_and_hydro", "Electricity Total"],
        ["Solar", "Solar PV", "Electricity Total"],
        ["Solid Biomass", "Solid biomass", "Solid Biofuels Total"],
    ]

    df = pd.DataFrame(
        df,
        columns = [
            _FIELD_FSM_FUEL, 
            _FIELD_FSM_FUEL_TABLE, 
            _FIELD_FSM_AGG_GROUP
        ],
    )

    return df



def get_dict_fuel_type_shares(
    subsector_element: str,
    df_consumption_by_fuel: Union[pd.DataFrame, None] = None,
) -> Dict[str, float]:
    """Get the dictionary mapping each SSP-fuel group (not category, but 1:1 to cat)
        to its share within the appropriate group.
    """
    
    ##  INITIALIZATION

    # get consumption by fuel and filter to subsector element
    df_consumption_by_fuel = (
        get_df_consump_by_fuel()
        if not isinstance(df_consumption_by_fuel, pd.DataFrame)
        else df_consumption_by_fuel
    )

    df_consump_by_fuel_filt = df_consumption_by_fuel[
        df_consumption_by_fuel[_FIELD_CBF_SECTOR] == subsector_element
    ]
    
    # get fuel shares map
    df_fsm = get_dict_fuel_shares_map()
    df_fsmg = df_fsm.groupby([_FIELD_FSM_AGG_GROUP])
    dict_fuel_type_shares = {}
    

    for grp, df in df_fsmg:
        for i, row in df.iterrows():
            # some fields         
            fuel = row[_FIELD_FSM_FUEL]
            field_from_table = row[_FIELD_FSM_FUEL_TABLE]
            field_agg_group = row[_FIELD_FSM_AGG_GROUP]

            # appropriate shares
            num = float(df_consump_by_fuel_filt[field_from_table].iloc[0])
            denom = float(df_consump_by_fuel_filt[field_agg_group].iloc[0])
            
            # set share to uniform if no info is available
            share = num/denom if denom != 0 else 1/df.shape[0]
            dict_fuel_type_shares.update({fuel: share, })
    
    return dict_fuel_type_shares



def get_dict_table_40(
    model_attributes: 'ModelAttributes',
    delim: str = "|",
    df_table_40: Union[pd.DataFrame, None] = None,
    flag_all_except: str = "all_except",
    field_cat: str = "cat",
    field_sector: str = "sector",
) -> dict:
    """Get dictionary to allocate petroleum product shares. 

    Function Arguments
    ------------------
    df_table_40 : pd.DataFrame
        DataFrame of Table40 from input_data
    model_attributes : ModelAttributes
        ModelAttributes for managing sectors and categories
    
    Keyword Arguments
    -----------------
    df_table_40 : Union[pd.DataFrame, None]
        Optional specification of table. If None, reads
    flag_all_except : str
        Flag for identifying categories applied to all EXCEPT for others
        that are specified.
    """

    ##  INITIALIZATION

    # get the 
    df_table_40 = (
        get_table_40()
        if not isinstance(df_table_40, pd.DataFrame)
        else df_table_40
    )
    
    # get the ENFU attribute
    attr_enfu = model_attributes.get_attribute_table(
        model_attributes.subsec_name_enfu,
    )

    # get fuel fields
    fields_fuel = [x for x in attr_enfu.key_values if x in df_table_40.columns]
    for field in fields_fuel:
        df_table_40[field] = df_table_40[field].astype(float)

    

    ##  ITERATE TO BUILD DICT
    
    dfg = (
        df_table_40
        .fillna(0.0)
        .groupby([field_sector])
    )

    # initialize output dictionary
    dict_out = {}

    for tup, df in dfg:
        subsec = tup[0]
        attr_cur = model_attributes.get_attribute_table(subsec, )
        if attr_cur is None: continue
            
        # iterate over rows
        vec_cats = df[field_cat].to_numpy()
        w = np.where(vec_cats == flag_all_except)[0]

        dict_cur = {}
        
        if len(w) > 0:
            if len(w) > 1:
                raise KeyError(f"Multiple specifications of '{flag_all_except}' in subsector {subsec}")

            # get row and normalize
            row = df.iloc[w[0]][fields_fuel]

            row2 = row/row.sum()
            dict_new = row2.to_dict()

            dict_cur = dict(
                (k, dict_new) for k in attr_cur.key_values
            )

        # then, update
        for i, row in df.iterrows():
            if i in w: continue

            cats = row[field_cat].split(delim)
            cats = [x for x in attr_cur.key_values if x in cats]
            
            row2 = row[fields_fuel]/row[fields_fuel].sum()
            dict_new = row2.to_dict()
            
            dict_cur.update(
                dict(
                    (k, dict_new) for k in cats
                )
            )
        
        dict_out.update({subsec: dict_cur})

    return dict_out



def get_table_40(
) -> pd.DataFrame:
    """Get Table 40 data (written to csv and formatted for SSP use)
    """
    df_out = pd.read_csv(_PATH_TABLE_40)

    return df_out