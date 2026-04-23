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
_BIOMASS_SHIFT_IMPLEMENTATION_TP_END = 55
_BIOMASS_SHIFT_IMPLEMENTATION_WINDOW = (-2, 6)


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



def _update_inen_fuel_mix_from_by(
    df_input: pd.DataFrame,
    time_periods: 'TimePeriods',
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

    return df_input



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
    field_mining = modvar.build_fields(category_restrictions = "mining", )
    field_tp = time_periods.field_time_period

    ##  MANUALLY SET

    df_out = df_input.copy()

    # cement is defined up to 2022
    w = np.where(df_out[field_tp].to_numpy() >= 8)
    df_out[field_cement][w] = 1.0

    # mining is defined up to 2023
    w = np.where(df_out[field_tp].to_numpy() >= 9)
    df_out[field_mining][w] = 0.5

    # dump output
    sf._optional_log(
        logger,
        "Completed cement and mining elasticity updates.",
        type_log = "info",
    )
    
    return df_out




def _update_scoe_base_elec_to_biomass(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    cat: str = "residential",
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

    return df_input



def _update_scoe_baseline_electrification_rates(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttribuets',
) -> pd.DataFrame:
    """Update baseline electrification for appliances in line with
        Vision 2040. 
    """

    # 
    rate_elec_base = 0.



def _update_scoe_fuel_mix_from_by(
    df_input: pd.DataFrame,
    time_periods: 'TimePeriods',
) -> pd.DataFrame:
    """Update the SCOE energy fuel mixes by mixing from base year
        to a future target
    """
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

    return df_input



def _update_scoe_shift_biomass_to_elec(
    df_input: pd.DataFrame,
    model_attributes: 'ModelAttributes',
    factor_shift: float = 0.82,
    tp_end_shift_out_of_biomass: int = _BIOMASS_SHIFT_IMPLEMENTATION_TP_END,
    window_logistic: int = _BIOMASS_SHIFT_IMPLEMENTATION_WINDOW,
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

    return df_input

    


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

    # initialize some objects
    model_attributes = model_afolu.model_attributes


    ##  INITIAL MODS

    # baseline shift of 50% of elec back to bmass
    df_input = _update_scoe_base_elec_to_biomass(
        df_input,
        model_attributes,
    )
    
    # mix from base year to a future--INEN
    df_input = _update_inen_fuel_mix_from_by(
        df_input,
        time_periods,
    )

    # mix from base year to a future--SCOE
    df_input = _update_scoe_fuel_mix_from_by(
        df_input,
        time_periods,
    )


    ##  ADDITIONAL MODIFICATIONS

    # stationary combustion
    df_input = _update_enfu_stationary_combustion_factors(
        df_input,
        model_attributes,
        logger = _LOGGER,
    )
    
    # cement elasticities
    df_input = _update_ippu_elasticities(
        df_input,
        model_attributes,
        time_periods,
        logger = _LOGGER,
    )

    # transportation electrification rates
    df_input = _update_trns_electrification_rates(
        df_input,
        model_afolu,
        logger = _LOGGER,
    )
    

    ##  FINAL PIECES

    _update_scoe_shift_biomass_to_elec(
        df_input,
        model_attributes,
    )

    return df_input
    
    
    
