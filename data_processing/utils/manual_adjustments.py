"""Perform manual adjustments to input data to align with data
    and/or information from UGOV.
"""
import data_processing.utils.common_data_needs as cdn
import logging 
import numpy as np
import os, os.path
import pandas as pd
import pathlib
import sisepuede.utilities._classes as suc
import sisepuede.utilities._toolbox as sf

from typing import *




def get_path(
) -> pathlib.Path:
    """Get current directory
    """

    path_cur = pathlib.Path(os.path.abspath(__file__))
    path_utils = path_cur.parents[0]
    path_repo = path_utils.parents[1]

    out = (
        path_utils,
        path_repo,
    )
    
    return out



def _setup_logger(
    format_str: str = "%(asctime)s - %(levelname)s - %(message)s",
    namespace: str = __name__,
) -> None:
    """Setup the logger namespace
    """
    _, path_repo = get_path()
    path_out = path_repo.joinpath(_FILE_NAME_LOG, )


    # setup logger
    logging.basicConfig(
        filename = str(path_out),
        filemode = "w",
        format = format_str,
        level = logging.DEBUG, 
    )

    logger = logging.getLogger(namespace, )
    if logger.hasHandlers():
        return logger

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter, add to console handler, and add the handler to logger
    formatter = logging.Formatter(format_str)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger




##########################
#    GLOBAL VARIABLES    #
##########################

# file names
_FILE_NAME_LOG = "log_manual_adjustments.log"

# logging
_LOGGER = _setup_logger()

# biomass shift
_BIOMASS_SHIFT_IMPLEMENTATION_TP_END = 45
_BIOMASS_SHIFT_IMPLEMENTATION_WINDOW = (-2, 6)

# some dates
_YEAR_0_NEW_STEEL = 2028



###################
#    FUNCTIONS    #
###################

def get_arrays_for_fuel_shift(
    df_input: pd.DataFrame,
    model_afolu: 'AFOLU',
    subsec: str,
    cats_in: Union[str, None] = None,
) -> Dict[str, np.ndarray]:
    """Retrieve array of fuel fractions by category within a subsector. Used
        for setting target allocations in the time series simplex shifter 
        for biomass. 
    """

    ##  INITIALIZATION

    # shortcuts and dictionary mapping fuels to model variables
    matt = model_afolu.model_attributes
    attr = matt.get_attribute_table(subsec, )
    attr_enfu = matt.get_attribute_table(matt.subsec_name_enfu, )

    dict_fuel_to_frac = model_afolu.model_enercons.get_subsec_dict_fuel_to_fuel_modvar(
        subsec, 
    )


    # all categories to build for
    cats = sorted(
        list(
            set(
                sum(
                    [matt.get_variable_categories(x) for x in dict_fuel_to_frac.values()],
                    []
                )
            )
        )
    )

    cats = (
        [x for x in cats if x in cats_in]
        if sf.islistlike(cats_in)
        else cats
    )

    dict_out = {}
    
    
    # iterate over each category/fuel combo
    for cat in cats:

        # initialize the array
        arr = np.zeros((df_input.shape[0], attr_enfu.n_key_values), )
        
        for j, fuel in enumerate(attr_enfu.key_values):

            # get associated variable
            modvar = matt.get_variable(dict_fuel_to_frac.get(fuel, ), )
            skip = modvar is None
            skip |= (
                cat not in matt.get_variable_categories(modvar, )
                if not skip
                else skip
            )
            
            if skip: continue
            
            # get field and add
            field = modvar.build_fields(category_restrictions = cat, )
            arr[:, j] = df_input[field].to_numpy()
        
        dict_out.update({cat: arr, })

    return dict_out



def _update_enfu_factors(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update biofuel factors. Assume 10% ethanol. 

        Assume:
            - CO2 factors are biogenic (sugarcane), so LC emissions
                are 0
            - CH4 and N2O are from V2.C3 Table 3.2.2 of IPCC GNGHGI
    """

    ##  INITIALIZATION

    # categories
    cat_enfu_biofuels = "fuel_biofuels"
    cat_enfu_gasoline = "fuel_gasoline"
    cat_trns_light = "road_light"
    
    # model variables
    modvar_co2 = model_attributes.get_variable(":math:\\text{CO}_2 Combustion Emission Factor")
    modvar_ch4 = model_attributes.get_variable(":math:\\text{CH}_4 Biofuels Mobile Combustion Emission Factor")
    modvar_ch4_gas = model_attributes.get_variable(":math:\\text{CH}_4 Gasoline Mobile Combustion Emission Factor")
    modvar_n2o = model_attributes.get_variable(":math:\\text{N}_2\\text{O} Biofuels Mobile Combustion Emission Factor")
    modvar_n2o_gas = model_attributes.get_variable(":math:\\text{N}_2\\text{O} Gasoline Mobile Combustion Emission Factor")

    # get biofuel categories
    cats_trns_ch4 = model_attributes.get_variable_categories(modvar_ch4, )
    cats_trns_n2o = model_attributes.get_variable_categories(modvar_n2o, )
    
    # some fields
    field_co2_biofuels = modvar_co2.build_fields(category_restrictions = cat_enfu_biofuels, )
    field_co2_gasoline = modvar_co2.build_fields(category_restrictions = cat_enfu_gasoline, )
    fields_ch4 = modvar_ch4.fields
    fields_ch4_gas = modvar_ch4_gas.build_fields(category_restrictions = cats_trns_ch4, )
    fields_n2o = modvar_n2o.fields
    fields_n2o_gas = modvar_n2o_gas.build_fields(category_restrictions = cats_trns_n2o, )

    # some special fields
    field_ch4_light = modvar_ch4.build_fields(category_restrictions = cat_trns_light, )
    field_ch4_gas_light = modvar_ch4_gas.build_fields(category_restrictions = cat_trns_light, )
    

    ##  UPDATE OUTPUT

    df_out = df_input.copy()
    share_gas = 0.9
    
    # co2 is assumed to be 10% biogenic (net zero) from gasoline
    df_out[field_co2_biofuels] = df_out[field_co2_gasoline]*share_gas

    # use CH4 direct from 3.2.2
    df_out[fields_ch4] = share_gas*df_out[fields_ch4_gas] + 260*(1 - share_gas)
    df_out[field_ch4_light] = share_gas*df_out[field_ch4_gas_light] + 18*(1 - share_gas)

    # use N2O direct from 3.2.2
    df_out[fields_n2o] = share_gas*df_out[fields_n2o_gas] + 41*(1 - share_gas)
    

    # dump output
    sf._optional_log(
        logger,
        "Completed adjustmnt of biofuels (E10) emission factors.",
        type_log = "info",
    )

    return df_out



def _update_enfu_stationary_combustion_factors(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update stationary combustion factors for biomass, which are primarily 
        driven by stationary combustion in residential/commercial contexts,
        not other industrial sectors. 

        - Pull from Tables 2.4 and 2.5 instead of 2.2
    """
    modvar_ef_stat_ch4 = model_attributes.get_variable(
        ":math:\\text{CH}_4 Stationary Combustion Emission Factor"
    )
    modvar_ef_stat_n2o = model_attributes.get_variable(
        ":math:\\text{N}_2\\text{O} Stationary Combustion Emission Factor"
    )

    # get fields
    cat_biomass = "fuel_biomass"
    field_ef_stat_ch4 = modvar_ef_stat_ch4.build_fields(
        category_restrictions = cat_biomass
    )
    field_ef_stat_n2o = modvar_ef_stat_n2o.build_fields(
        category_restrictions = cat_biomass
    )
    
    # update
    df_input[field_ef_stat_ch4] = 0.3
    df_input[field_ef_stat_n2o] = 0.004

    # dump output
    sf._optional_log(
        logger,
        "Completed stationary combustion factors (CH4 and N2O) adjustment.",
        type_log = "info",
    )

    return df_input



def _update_enst_annual_storage_capacities(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Set max and min storage capacites. Ensures that batteries
        are built, not other storage.
    """
    ##  INITIALIZATION
    
    # get things from ModelAttributes
    modvar_max = model_attributes.get_variable("NemoMod TotalAnnualMaxCapacityStorage")
    modvar_max_inv = model_attributes.get_variable("NemoMod TotalAnnualMaxCapacityInvestmentStorage")
    modvar_min = model_attributes.get_variable("NemoMod TotalAnnualMinCapacityStorage")
    modvar_min_inv = model_attributes.get_variable("NemoMod TotalAnnualMinCapacityInvestmentStorage")

    # unit manager for batteries
    um_energy = model_attributes.get_unit("energy")
    
    # categories
    cat_storage_min = "st_batteries"
    cats_storage_max = [
        "st_compressed_air",
        "st_flywheels",
        "st_pumped_hydro"
    ]
    cats_st = cats_storage_max + [cat_storage_min]

    # set fields
    fields_to_cap = modvar_max.build_fields(
        category_restrictions = cats_storage_max,
    )
    field_to_min_bound = modvar_min.build_fields(
        category_restrictions = cat_storage_min,
    )

    # investment fields
    fields_max_inv = modvar_max_inv.build_fields(
        category_restrictions = cats_st,
    )
    fields_min_inv = modvar_min_inv.build_fields(
        category_restrictions = cats_st,
    )

    # indices for time periods
    w = np.where(
        df_input[model_attributes.dim_time_period].isin(cdn._TIME_PERIODS_BASE)
    )[0]
    

    ##  UPDATE INPUTS
    
    df_out = df_input.copy()

    # cap certain storage types, and cap everything in the baseline
    df_out[fields_to_cap] = 0.0
    df_out[fields_max_inv].iloc[w] = 0.0

    # use Table 13.3 (candidate generation projects) to set minimum capacity from BESS
    # assume 50% by 2035, 100% by 2040
    n = df_out.shape[0]
    cap_target = 1.55132*um_energy.convert("gwy", "pj")

    vec_ramp_min_prod_st = 0.5*sf.ramp_vector(
        n,
        r_0 = 12,
        r_1 = 20,
    )
    vec_ramp_min_prod_st += 0.5*sf.ramp_vector(
        n,
        r_0 = 20,
        r_1 = 25,
    )

    # set min capacity ramp
    df_out[field_to_min_bound] = cap_target*vec_ramp_min_prod_st


    # dump log
    sf._optional_log(
        logger,
        "Completed adjustment of storage capacity constraints.",
        type_log = "info",
    )

    return df_out



def _update_entc_annual_maxcapacity(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Set max and min storage capacites. Ensures that batteries
        are built, not other storage.
    """
    # get variable and fields
    modvar_max_cap = model_attributes.get_variable(
        "NemoMod TotalAnnualMaxCapacity"
    )

    # techs to cap
    field_coal = modvar_max_cap.build_fields(
        category_restrictions = "pp_ocean",
    )
    field_coal_ccs = modvar_max_cap.build_fields(
        category_restrictions = "pp_ocean",
    )
    field_gas_ccs = modvar_max_cap.build_fields(
        category_restrictions = "pp_gas_ccs",
    )
    field_ocean = modvar_max_cap.build_fields(
        category_restrictions = "pp_ocean",
    )

    # update values--start by basing at 0s
    df_out = df_input.copy()
    df_out[
        [
            field_coal,
            field_coal_ccs,
            field_gas_ccs,
            field_ocean
        ]
    ] = 0


    # dump log
    sf._optional_log(
        logger,
        "Updated maximum capacity for invalid power categories",
        type_log = "info",
    )

    return df_out



def _update_entc_annual_maxprod_inc(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    flag_none: float = -999,
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Set max and min storage capacites. Ensures that batteries
        are built, not other storage.
    """
    # get variable and fields
    modvar_max_prodinc_msp = model_attributes.get_variable(
        "Maximum Production Increase Fraction to Satisfy MinShareProduction Electricity"
    )

    field_biomass = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_biomass",
    )
    field_gas = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_gas",
    )
    field_geo = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_geothermal",
    )
    field_hydro = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_hydropower",
    )
    field_nuclear = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_nuclear",
    )
    field_oil = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_oil",
    )
    field_wind = modvar_max_prodinc_msp.build_fields(
        category_restrictions = "pp_wind",
    )


    # update values--start by basing at 0s
    df_out = df_input.copy()
    df_out[[field_geo, field_hydro, field_nuclear, field_wind,]] = flag_none

    # update individual caps
    w = np.where(df_out[model_attributes.dim_time_period] > 25)[0]

    df_out[field_biomass].iloc[w] = 5.0
    df_out[field_gas].iloc[w] = 5.0
    df_out[field_geo].iloc[w] = 5.0
    df_out[field_hydro].iloc[w] = 1.0
    df_out[field_nuclear].iloc[w] = 5.0
    df_out[field_oil].iloc[w] = 1.0
    df_out[field_wind].iloc[w] = 5.0


    # dump log
    sf._optional_log(
        logger,
        "Completed elimination of max production increase to meet MSP for hydro and nuclear.",
        type_log = "info",
    )

    return df_out



def _update_entc_capital_costs(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """get costs from least cost plan
        2019 -> 2024 is 1.2263: https://www.in2013dollars.com/us/inflation/2019?endYear=2024&amount=1
        costs are in 2024 USD$, come from Table 12 on page 35
    """

    ##  INITIALIZE VALUES

    # https://www.in2013dollars.com/us/inflation/2019?endYear=2024&amount=1
    factor_2019_to_2024 = 1.2263
    
    # costs from Table 12
    dict_costs = {
        "pp_biomass": (3000 + 4000)/2,
        "pp_gas": (688 + 1137)/2, 
        "pp_geothermal": 5583,
        "pp_hydropower": (3500 + 6000)/2,
        "pp_nuclear": 4454,
        "pp_oil": 1236,
        "pp_solar": 1000,
        "pp_wind": 1788,
    }
    
    dict_costs = dict(
        (k, v/factor_2019_to_2024) for k, v in dict_costs.items()
    )
    

    ##  ITERATE TO ADJUST (SCALE EXISTING PATHWAYS TO MATCH 2024)

    df_out = df_input.copy()
    
    # get model attribute
    modvar_capcost = model_attributes.get_variable("NemoMod CapitalCost")
    w = np.where(
        df_out[
            time_periods.field_time_period
        ].isin(
            [
                time_periods.year_to_tp(2024)
            ]
        )
    )[0][0]
     
    # 
    for cat, val in dict_costs.items():
        field = modvar_capcost.build_fields(
            category_restrictions = cat, 
        )
    
        # 
        val_cur = df_out[field].iloc[w]
        scalar = val/val_cur

        df_out[field] *= scalar

    # dump log
    sf._optional_log(
        logger,
        "Updated capital costs of technologies.",
        type_log = "info",
    )

    return df_out



def _update_frst_fraction_deforestation_avail(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update availability of forest conversion from deforestation available for
        biomass. Used to align targets.
    """
    ##  INITIALIZATION

    modvar_frst_frac = model_attributes.get_variable(
        "Fraction of Forest Conversions Available for Fuelwood"
    )
    field = modvar_frst_frac.fields[0]
    field_tp = time_periods.field_time_period

    df_out = df_input.copy()


    ##  ADJUST

    # some other info--assume it opens in 2027
    year_0 = 2019
    tp_0 = time_periods.year_to_tp(year_0, )
    w = np.where(df_out[field_tp].to_numpy() == tp_0)[0]

    # basis for the adjustment--has to be manually set 
    frac_cur = df_out[field].iloc[w[0]]
    v_cur = 0.477596 # could write as a function, but easier to just set here
    v_target = 1.491104

    # get scalar to apply
    frac_new = 1 - (1 - frac_cur)*v_target/v_cur
    scalar = frac_new/frac_cur
    
    # set as a vector and adjust
    vec_ramp = sf.ramp_vector(
        df_out.shape[0],
        alpha_logistic = 1.0,
        r_0 = 11,
        r_1 = _BIOMASS_SHIFT_IMPLEMENTATION_TP_END,
        window_logistic = (-3, 3),
    )
    vec_scalar = scalar*(1 - vec_ramp) + vec_ramp

    df_out[field] = df_out[field].to_numpy()*vec_scalar
    

    # dump log
    sf._optional_log(
        logger,
        "Updated fraction of forest conversions available for use.",
        type_log = "info",
    )

    return df_out


def _update_inen_fuel_mix_from_by(
    df_input: pd.DataFrame,
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update the Industrial energy fuel mixes by mixing from base year
        to a future target
    """
    # INEN
    df_inen_fuel_mix = cdn.get_files_from_matchstr("frac_inen", )
    df_inen_fuel_mix = cdn.mix_from_base_year_future(
        df_inen_fuel_mix,
        [time_periods.field_year],
        0.0,
        time_periods,
        2023,
    )
    df_inen_fuel_mix = (
        time_periods.years_to_tps(df_inen_fuel_mix)
        .drop(columns = time_periods.field_year, )
    )
    
    df_input = sf.match_df_to_target_df(
        df_input,
        df_inen_fuel_mix,
        [time_periods.field_time_period],
    )

    # dump log
    sf._optional_log(
        logger,
        "Updated INEN fuel mix from baseline years.",
        type_log = "info",
    )

    return df_input



def _update_inen_fuel_mix_metals(
    df_input: pd.DataFrame,
    time_periods: 'TimePeriods',
    model_enercons: 'EnergyConsumption',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update the Industrial energy fuel mixes by mixing from base year
        to a future target. Current production is about 500,000 Tonne of steel;
        a 1 MT plant gives 2/3 to 1/3. 

    Assume that it is a blast furnace:
    https://ugandainvest.go.ug/presidents-museveni-ruto-break-ground-for-500-million-mega-steel-mill-in-eastern-uganda/

    """

    ##  INITIALIZATION

    cat = "metals"
    dict_fuel_to_var = model_enercons.get_inen_dict_fuel_categories_to_fuel_variables()[0]
    field_tp = time_periods.field_time_period
    matt = model_enercons.model_attributes

    # some fuels
    fuel_coal = "fuel_coke"
    fuel_elec = model_enercons.cat_enfu_electricity
    

    ##  GET FIELDS

    # initialize df out, will set everything to zero
    df_out = df_input.copy()

    fields = []
    field_coal = None
    field_elec = None

    # some other info--assume it opens in 2027
    year_0 = _YEAR_0_NEW_STEEL
    tp_0 = time_periods.year_to_tp(year_0, )
    w = np.where(df_out[field_tp] >= tp_0)[0]
    
    # assume all electricity will be replaced with coke ovens
    vec_new_elec = np.ones(df_out.shape[0], )
    vec_new_elec[w] = float(1/3)
    vec_new_coal = 1 - vec_new_elec

    for k, v in dict_fuel_to_var.items():

        modvar = matt.get_variable(v.get("fuel_fraction"), )
        if modvar is None: continue

        field = modvar.build_fields(category_restrictions = cat, )
        if (field is None): continue

        df_out[field] = 0.0

        # update
        if k == fuel_coal:
            df_out[field] = vec_new_coal
        elif k == fuel_elec:
            df_out[field] = vec_new_elec


    # dump log
    sf._optional_log(
        logger,
        "Updated INEN fuel mix of metals to represent shift to DRI/Coke Furnaces.",
        type_log = "info",
    )

    return df_out



def _update_ippu_efs_metal(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    ef_eaf: float = 0.08,
    ef_mean: float = 1.06,
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Current steel production has been primary scrap metal (see NPA steel 
        report, 2018, availabile in repository), which is primary done with 
        Electric Arc Furnaces. This is reflected in the 2023 energy balance, 
        which shows electricity as the only fuel consumed.

    This is expected to change, however, with new direct reduced iron (DRI)
        plants (noted in the ETP). These are far more emission intensive.

    The Torono steel mill is expected to produce 1 MT of steel annually with
        blast furnaces, which emit a lot of CO2.
    https://en.wikipedia.org/wiki/Tororo_Steel_Mill
    https://yieh.com/es/News/devki-steel-to-build-new-steel-plant-in-eastern-uganda/158153
    (blast furnace)
    https://ugandainvest.go.ug/presidents-museveni-ruto-break-ground-for-500-million-mega-steel-mill-in-eastern-uganda/
    (also blast furnace)


    To represent this, we adjust emission factors from EAF-based steel making,
        early on, to be mixed with 2/3 by 2028 the emission factor global 
        average. Emission factors are from Table 4.1 of IPCC V3 C4 (Metals)
        (page 4.25 in 2006 GNGHG Inventories)

    """

    ##  INITIALIZATION

    # model variable pieces
    modvar = model_attributes.get_variable(
        ":math:\\text{CO}_2 Production Process Emission Factor",
    )
    field = modvar.build_fields(
        category_restrictions = "metals",
    )
    field_tp = time_periods.field_time_period

    # some other info--assume it opens in 2027
    year_0 = _YEAR_0_NEW_STEEL
    tp_0 = time_periods.year_to_tp(year_0, )

    # initialize
    df_out = df_input.copy()
    df_out[field] = ef_eaf
    w = np.where(df_out[field_tp] >= tp_0)[0]
    if len(w) == 0:
        return df_out
    
    
    ##  MANUALLY SET

    df_out[field][w] = (1/3)*ef_eaf + (2/3)*ef_mean

    # dump output
    sf._optional_log(
        logger,
        "Completed adjustment to steel/metals emission factors in IPPU.",
        type_log = "info",
    )
    
    return df_out



def _update_ippu_elasticities(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update elasticities of 
        
        (1) cement to better represent economic growth in construction;

        (2) mining to represent expected growth in industry (from MEMD)
    """

    ##  INITIALIZATION

    # model variable pieces
    modvar = model_attributes.get_variable("Elasticity of Industrial Production to GDP")

    # some fields
    field_cement = modvar.build_fields(category_restrictions = "cement", )
    field_metals = modvar.build_fields(category_restrictions = "metals", )
    field_mining = modvar.build_fields(category_restrictions = "mining", )
    field_tp = time_periods.field_time_period

    ##  MANUALLY SET

    df_out = df_input.copy()

    
    # cement is defined up to 2022
    tp_cement = time_periods.year_to_tp(2022, )
    w = np.where(df_out[field_tp].to_numpy() >= tp_cement)[0]

    # try building a ramp vector
    vec_ramp = sf.ramp_vector(
        w.shape[0],
        alpha_logistic = 1,
        r_0 = 0,
        r_1 = 6,
    )
    vec_ramp2 = sf.ramp_vector(
        w.shape[0],
        alpha_logistic = 1,
        r_0 = 14,
        r_1 = 36,
        window_logistic = (-3, 6),
    )

    vec_ramp *= 0.7 
    vec_ramp += 1
    vec_ramp = (1 - vec_ramp2)*vec_ramp + vec_ramp2*0.5

    # apply
    df_out[field_cement][w] = vec_ramp

    # metals is are defined up to 2022
    tp_metals = time_periods.year_to_tp(2022, )
    w = np.where(df_out[field_tp].to_numpy() >= tp_metals)[0]
    df_out[field_metals][w] = 1.5

    # mining is defined up to 2023
    tp_mining = time_periods.year_to_tp(2023, )
    w = np.where(df_out[field_tp].to_numpy() >= tp_mining)[0]
    df_out[field_mining][w] = 0.5

    # dump output
    sf._optional_log(
        logger,
        "Completed cement and mining elasticity updates.",
        type_log = "info",
    )
    
    return df_out



def _update_ippu_net_imports_clinker(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Net imports of clinker will drop drastically when a new clinker 
        production plant is completed in 2027 (assumed).

    https://www.gcic.go.ug/president-museveni-to-launch-new-cement-and-clinker-factory-in-karamoja/

    """

    ##  INITIALIZATION

    # model variable pieces
    modvar = model_attributes.get_variable("Net Imports of Cement Clinker")
    field = modvar.fields[0]
    field_tp = time_periods.field_time_period

    # some other info--assume it opens in 2027
    year_0 = 2027
    tp_0 = time_periods.year_to_tp(year_0, )

    w = np.where(df_input[field_tp] >= tp_0)[0]
    if len(w) == 0:
        return df_input
    
    
    ##  MANUALLY SET

    df_out = df_input.copy()
    df_out[field][w] -= 6000*365.25

    # dump output
    sf._optional_log(
        logger,
        "Completed adjustment to net imports of clinker to reflct Karamoja plant.",
        type_log = "info",
    )
    
    return df_out



def _update_lndu_reallocation_factor(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Specify a land use reallocation factor directly.
    """
    
    ##  INITIALIZATION

    modvar_lurf = model_attributes.get_variable(
        "Land Use Yield Reallocation Factor"
    )
    field = modvar_lurf.fields[0]

    df_out = df_input.copy()


    ##  ADJUST

    # build a vector that I know aligns
    v1 = 0.25*sf.ramp_vector(
        df_input.shape[0],
        r_0 = 13,
    )

    v2 = sf.ramp_vector(
        df_input.shape[0],
        r_0 = 11,
    )

    # mix, shift, and clip
    out = (v1*(1 - v2) + 0.275*v2)
    out = np.clip(out - 0.05, 0, 1, )

    # update and return
    df_out[field] = out


    # dump log
    sf._optional_log(
        logger,
        "Updated land use reallocation factor.",
        type_log = "info",
    )
    
    return df_out



def _update_lndu_suprema(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Specify any suprema for land use classes.
    """
    
    ##  INITIALIZATION

    modvar_max_area = model_attributes.get_variable(
        "Maximum Area"
    )

    # specify directly
    dict_caps = {
        "wetlands": 1650000,
    }

    
    ##  ITERATE OVER DICT ITEMS TO SPECIFY

    df_out = df_input.copy()

    for k, v in dict_caps.items():

        field = modvar_max_area.build_fields(
            category_restrictions = k,
        )
        if field is None: continue

        df_out[field] = v



    # dump log
    sf._optional_log(
        logger,
        "Updated land use suprema.",
        type_log = "info",
    )
    
    return df_out



def _update_scoe_base_elec_to_biomass(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    cat: str = "residential",
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Adjust high estimate of residential electricity by shifting 50% into 
        baseline. Manual calib
    """
    # some model variables
    modvar_scoe_frac_elec = model_attributes.get_variable(
        "SCOE Fraction Heat Energy Demand Electricity"
    )
    modvar_scoe_frac_biomass = model_attributes.get_variable(
        "SCOE Fraction Heat Energy Demand Solid Biomass"
    )

    # fields
    field_biomass = modvar_scoe_frac_biomass.build_fields(category_restrictions = cat, )
    field_elec = modvar_scoe_frac_elec.build_fields(category_restrictions = cat, )
    
    # get shift out of elec to biomass
    vec_shift = df_input[field_elec].to_numpy()/2
    df_input[field_elec] = df_input[field_elec] - vec_shift
    df_input[field_biomass] = df_input[field_biomass] + vec_shift


    # dump output
    sf._optional_log(
        logger,
        "Updated SCOE electric to biomass",
        type_log = "info",
    )

    return df_input




def _update_scoe_fuel_mix_from_by(
    df_input: pd.DataFrame,
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update the SCOE energy fuel mixes by mixing from base year
        to a future target
    """
    return df_input
    df_scoe_fuel_mix = cdn.get_files_from_matchstr("frac_scoe", )
    df_scoe_fuel_mix = cdn.mix_from_base_year_future(
        df_scoe_fuel_mix,
        [time_periods.field_year],
        0.0,
        time_periods,
        2021,
    )
    df_scoe_fuel_mix = (
        time_periods.years_to_tps(df_scoe_fuel_mix)
        .drop(columns = time_periods.field_year, )
    )

    df_input = sf.match_df_to_target_df(
        df_input,
        df_scoe_fuel_mix,
        [time_periods.field_time_period],
    )


    # dump output
    sf._optional_log(
        logger,
        "Updated SCOE fuel mix from the base year",
        type_log = "info",
    )

    return df_input



def _update_scoe_shift_biomass_to_elec(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    factor_shift: float = 0.925,#0.95
    tp_end_shift_out_of_biomass: int = _BIOMASS_SHIFT_IMPLEMENTATION_TP_END,
    window_logistic: int = _BIOMASS_SHIFT_IMPLEMENTATION_WINDOW,
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Adjust high estimate of residential electricity by shifting 50% into 
        baseline. Manual calib
    """
    ##  INITIALIZATION

    attr_scoe = model_attributes.get_attribute_table(
        model_attributes.subsec_name_scoe,
    )

    # some model variables
    modvar_scoe_frac_elec = model_attributes.get_variable(
        "SCOE Fraction Heat Energy Demand Electricity"
    )
    modvar_scoe_frac_biomass = model_attributes.get_variable(
        "SCOE Fraction Heat Energy Demand Solid Biomass"
    )

    
    ##  SETUP IMPLEMENTATION RAMP AND SHIFT
    
    vec_implementation_ramp = sf.ramp_vector(
        df_input.shape[0],
        alpha_logistic = 1.0,
        r_0 = 11, 
        r_1 = tp_end_shift_out_of_biomass,
        window_logistic = window_logistic,
    )


    for cat in attr_scoe.key_values:
        
        # fields
        field_src = modvar_scoe_frac_biomass.build_fields(category_restrictions = cat, )
        field_target = modvar_scoe_frac_elec.build_fields(category_restrictions = cat, )

        # allocation vector
        vec_orig = df_input[field_src].values
        vec_reallocate = vec_orig*vec_implementation_ramp*factor_shift

        df_input[field_target] += vec_reallocate
        df_input[field_src] -= vec_reallocate


    # dump output
    sf._optional_log(
        logger,
        "Updated SCOE fuel shift into electric (clean-cooking) from biomass.",
        type_log = "info",
    )

    return df_input



def _update_soil_frac_mineral(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update soil fractions mineral, which are for some reason off.
    """

    ##  INITIALIZATION

    attr_lndu = model_attributes.get_attribute_table(
        model_attributes.subsec_name_lndu,
    )
    modvar = model_attributes.get_variable("Fraction of Soils Mineral", )


    ##  UPDATE OUTPUT FIELDS

    df_out = df_input.copy()
    df_out[modvar.fields] = 0.98

    field_crops = modvar.build_fields(
        category_restrictions = "croplands",
    )
    df_out[field_crops] = 0.97


    # dump output
    sf._optional_log(
        logger,
        "Updated SOIL Fractions mineral",
        type_log = "info",
    )

    return df_out



def _update_soil_initial_fertilizer(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update soil fractions mineral, which are for some reason off.
    """

    ##  INITIALIZATION


    modvar = model_attributes.get_variable("Initial Synthetic Fertilizer Use", )


    ##  UPDATE OUTPUT FIELDS

    # for now, build the dataframe--based on FAO data (in tonnes)
    df_fertilizer = pd.DataFrame(
        {
            time_periods.field_year: list(range(2015, 2022)),
            modvar.fields[0]: [
                2079.39,
                8538.46,
                7607.73,
                11209.00,
                11952.80,
                7724.80,
                7724.80
            ]
        }
    )

    # divide to get KT
    df_fertilizer[modvar.fields[0]] /= 1000

    df_fertilizer = (
        pd.merge(
            df_input[[time_periods.field_year]],
            df_fertilizer,
            how = "left",
        )
        .bfill()
        .ffill()
    )

    # match to output and overwrite
    df_out = sf.match_df_to_target_df(
        df_input,
        df_fertilizer,
        [time_periods.field_year],
    )

    # dump output
    sf._optional_log(
        logger,
        "Updated SOIL fertilizer from FAO",
        type_log = "info",
    )

    return df_out
    


def _update_trns_diesel_rail_efficiency(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update diesel rail efficiency in-line with BAU assumptions of 12% 
        increase from 2015-2030 (see page 41)
    """

    ##   SOME INITIALIZATION
    
    # categories to apply disel efficiency boost to
    cats_apply = [
        "rail_freight",
        "rail_passenger"
    ]

    # variable
    modvar = model_attributes.get_variable("Fuel Efficiency Diesel")
    

    ##  GET SHIFTS FOR TRANSPORTATION

    df_out = df_input.copy()
    field_tp = time_periods.field_time_period

    # some other info--assume this baseline increase starts in 2026 instead of 2015
    year_0 = 2026
    tp_0 = time_periods.year_to_tp(year_0, )
    w = np.where(df_out[field_tp].to_numpy() == tp_0)[0]

    # get rate
    n = df_out.shape[0]
    n_ramp = n - w[0]
    r_final = 0.12*(n_ramp - 1)/15

    vec_ramp = sf.ramp_vector(n = n, r_0 = w[0], )
    vec_ramp = 1 + vec_ramp*r_final

    # now, scale output fields
    fields = modvar.build_fields(
        category_restrictions = cats_apply,
    )
    for field in fields:
        df_out[field] *= vec_ramp

    # dump output
    sf._optional_log(
        logger,
        "Completed transportation baseline improvements in diesel rail efficiency.",
        type_log = "info",
    )


    return df_out



def _update_trns_electrification_rates(
    df_input: pd.DataFrame,
    model_afolu: pd.DataFrame,
    cat: str = "road_light",
    logger: Union[logging.Logger, None] = None,
) -> pd.DataFrame:
    """Update electrification in Transportation to align with 50% LDV by 2050.
    """

    ##   
    
    # home 
    matt = model_afolu.model_attributes
    attr_enfu = matt.get_attribute_table("Energy Fuels")
    ind_biofuels = attr_enfu.get_key_value_index("fuel_biofuels")
    ind_elec = attr_enfu.get_key_value_index("fuel_electricity")
    
    # get shifts shares
    fuels_shift_out = ["fuel_diesel", "fuel_gasoline"]
    arr_shift_shares = np.ones((df_input.shape[0], attr_enfu.n_key_values), )/(attr_enfu.n_key_values - 1)
    arr_shift_shares[:, ind_elec] = 0
    

    ##  GET SHIFTS FOR TRANSPORTATION

    subsec = "Transportation"
    
    arr = (
        get_arrays_for_fuel_shift(
            df_input,
            model_afolu,
            subsec,
        )
        .get(cat)
    )

    # set scalar to 
    scalar = 0.5/arr[35, ind_elec]
    vec_scalar = np.concatenate(
        [
            scalar*np.ones(36),
            scalar - np.arange(20)/40
        ]
    )
    
    dict_scale = {
        ind_elec: vec_scalar,
    }

    # use a shifter to set elec target
    tsss = suc.TimeSeriesSimplexShifter(arr, )

    # set to new array
    arr_tmp = arr.copy()
    arr_tmp[:, ind_elec] = 0
    arr_tmp[:, ind_biofuels] = 0
    
    arr_new = tsss.shift_mass_scalar_vectors(
        arr_tmp,
        dict_scale,
    )


    ##  ITERATE OVER VARS TO BUILD FIELDS
    
    inds_extract = []
    fields = []

    dict_fuel_to_frac = (
        model_afolu
        .model_enercons
        .get_subsec_dict_fuel_to_fuel_modvar(
            subsec, 
            values_as_modvars = True,
        )
    )
    
    for j, fuel in enumerate(attr_enfu.key_values):
        
        modvar = dict_fuel_to_frac.get(fuel, )
        if modvar is None: continue

        # build field
        field = modvar.build_fields(category_restrictions = cat, )
        if field is None: continue
        
        fields.append(field)
        inds_extract.append(j)

    # convert to an output dataframe
    df_cur = pd.DataFrame(
        arr_new[:, inds_extract], 
        columns = fields, 
    )

    df_input[df_cur.columns] = df_cur
    

    # dump output
    sf._optional_log(
        logger,
        "Completed transportation electrification of light-duty vehicle.",
        type_log = "info",
    )


    return df_input








##########################
#    PRIMARY FUNCTION    #
##########################

def adjust_inputs(
    df_input: pd.DataFrame,
    model_afolu: 'ModelAttributes',
    time_periods: 'TimePeriods',
) -> pd.DataFrame:
    """Implement all manual adjustments
    """

    # initialize model attributes and add year
    model_attributes = model_afolu.model_attributes
    df_input = time_periods.tps_to_years(df_input, )


    ##  INITIAL MODS

    # baseline shift of 50% of elec back to bmass
    df_input = _update_scoe_base_elec_to_biomass(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )
    
    # mix from base year to a future--INEN
    df_input = _update_inen_fuel_mix_from_by(
        df_input,
        time_periods,
        logger = _LOGGER,
    )

    # mix from base year to a future--SCOE
    df_input = _update_scoe_fuel_mix_from_by(
        df_input,
        time_periods,
        logger = _LOGGER,
    )


    ##  ADDITIONAL MODIFICATIONS

    ##  AFOLU

    df_input = _update_frst_fraction_deforestation_avail(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    df_input = _update_lndu_reallocation_factor(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_lndu_suprema(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_soil_frac_mineral(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_soil_initial_fertilizer(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )


    ##  ENERGY

    df_input = _update_enfu_factors(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_enfu_stationary_combustion_factors(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )
    
    df_input = _update_entc_capital_costs(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    df_input = _update_entc_annual_maxcapacity(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )
    
    df_input = _update_entc_annual_maxprod_inc(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_enst_annual_storage_capacities(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_trns_diesel_rail_efficiency(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    df_input = _update_trns_electrification_rates(
        df_input,
        model_afolu,
        logger = _LOGGER,
    )


    ##  IPPU

    df_input = _update_ippu_efs_metal(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    df_input = _update_ippu_elasticities(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    df_input = _update_ippu_net_imports_clinker(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )



    ##  FINAL PIECES

    df_input = _update_scoe_shift_biomass_to_elec(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )

    df_input = _update_inen_fuel_mix_metals(
        df_input,
        time_periods,
        model_afolu.model_enercons,
        logger = _LOGGER,
    )

    # remove year
    df_input = df_input.drop(columns = [time_periods.field_year], )

    return df_input
    
    
    
