"""Use this file to construct an inventory for decomposition with estimates from
    SISEPUEDE where files are incomplete.
"""

import numpy as np
import pandas as pd
import pathlib
import sisepuede.utilities._toolbox as sf


##########################
#    GLOBAL VARIABLES    #
##########################

# delimiter for emissions fields
_DELIM_FIELDS_EMISSION = ":"

# inventory fields
_FIELD_INV_EST_FLAG = "estimated_from_sisepuede"
_FIELD_INV_GAS = "Gas"
_FIELD_INV_SECTOR = "Sector"
_FIELD_INV_SOURCE = "Source"
_FIELD_INV_SUBSECTOR = "Subsector"
_FIELD_INV_VALUE = "Value"
_FIELD_INV_VALUE_CO2E = "emission_co2e"
_FIELD_INV_YEAR = "Year"



# crosswalk fields
_FIELD_CW_ACCOUNTED = "accounted"
_FIELD_CW_SUBSECTOR = "cats_inv"
_FIELD_CW_DISPLAY_SUBSECTOR = "display_subsector"
_FIELD_CW_GAS = "gas"
_FIELD_CW_SECTOR = "sector"
_FIELD_CW_VARIABLE_FIELDS = "variable_fields"

# flag for splitting GHGs
_FLAG_ALL_GHG = "all ghg"       # note that the upper case flag is set to lower on import





###########################
#    PRIMARY FUNCTIONS    #
###########################

def aggregate_cw_to_display(
    df_cw: pd.DataFrame,
    delim: str = _DELIM_FIELDS_EMISSION,
) -> pd.DataFrame:
    """Aggregate the crosswalk to only show elements associated with the display subsector?
    """

    df_out = []

    dfg = (
        df_cw
        .drop(columns = [_FIELD_CW_SUBSECTOR, _FIELD_CW_ACCOUNTED])
        .groupby(
            [
                _FIELD_CW_SECTOR,
                _FIELD_CW_DISPLAY_SUBSECTOR,
                _FIELD_CW_GAS
            ]
        )
    )

    for _, df in dfg:
        fields = sum([x.split(delim) for x in list(df[_FIELD_CW_VARIABLE_FIELDS])], [])
        fields = delim.join(sorted(fields))

        df = df.iloc[0:1]
        df[_FIELD_CW_VARIABLE_FIELDS] = fields
        df_out.append(df)

    df_out = sf._concat_df(df_out, )

    return df_out



def aggregate_inv_to_display(
    df_inv_synthetic: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate the inventory to only show the display subsector?
    """

    df_out = (
        df_inv_synthetic
        .drop(
            columns = [
                _FIELD_INV_SUBSECTOR,
                _FIELD_INV_EST_FLAG
            ], 
        )
        .groupby(
            [
                _FIELD_INV_SECTOR,
                _FIELD_CW_DISPLAY_SUBSECTOR,
                _FIELD_INV_GAS,
                _FIELD_INV_YEAR
            ]
        )
        .sum()
        .reset_index()
    )

    return df_out



def allocate_accounted_all_ghgs_using_ssp(
    df_base_sisepuede: pd.DataFrame,
    df_inventory: pd.DataFrame,
    df_cw_ssp: pd.DataFrame,
    time_periods: 'TimePeriods',
    delim_variable_fields: str = _DELIM_FIELDS_EMISSION,
) -> pd.DataFrame:
    """Allocate All GHG inventory elements using estimatated shares from SSP

    Merges emissions from df_base_sisepuede into df_years to create base 
        emissions.
    """

    ##  INITIALIZATION
    
    # add in years to SISEPUEDE
    df_base = (
        time_periods
        .tps_to_years(
            df_base_sisepuede, 
            field_year = _FIELD_INV_YEAR,
        )
    )

    inds_split = df_inventory[_FIELD_INV_GAS].isin([_FLAG_ALL_GHG])
    

    # iterate over subsectors
    df_allocated = []
    dfg = df_inventory[inds_split].groupby([_FIELD_INV_SUBSECTOR])
    

    for subsec, df in dfg:

        # some crosswalk elements
        rows = df_cw_ssp[
            df_cw_ssp[_FIELD_CW_SUBSECTOR].isin([subsec[0]])
        ]
        subsec_disp = rows[_FIELD_CW_DISPLAY_SUBSECTOR].unique()
        if subsec_disp.shape[0] > 1:
            raise RuntimeError(f"Multiple display subsectors found!")

        # initialize only as years; merge SSP values into this
        df_allocate = df[[_FIELD_INV_YEAR, _FIELD_INV_VALUE]].copy()
        gasses = []

        
        # get fields from SISEPUEDE
        for i, row in rows.iterrows():

            # some cw attributes
            fields = [
                x for x in 
                str(row[_FIELD_CW_VARIABLE_FIELDS]).split(delim_variable_fields, )
                if x in df_base.columns
            ]
            gas = row[_FIELD_CW_GAS]
            gasses.append(gas)
            

            df_tmp = df_base[[_FIELD_INV_YEAR] + fields].copy()
            df_tmp[gas] = df_tmp[fields].sum(axis = 1, )
            df_allocate = (
                pd.merge(
                    df_allocate,
                    df_tmp[[_FIELD_INV_YEAR, gas]],
                    how = "left",
                )
                .interpolate()
                .bfill()
            )

        # this will renormalize to 1
        arr_allocate = sf.check_row_sums(
            df_allocate[gasses],
            sum_restriction = 1,
            thresh_correction = None,
        )

        # multiply by fractions from SSP
        arr_allocate = sf.do_array_mult(
            arr_allocate,
            df_allocate[_FIELD_INV_VALUE].to_numpy()
        )

        # 
        df_allocate[gasses] = arr_allocate
        
        df_allocate = (
            pd.melt(
                df_allocate,
                id_vars = [_FIELD_INV_YEAR],
                value_vars = gasses,
                var_name = _FIELD_INV_GAS,
            )
            .rename(columns = {"value": _FIELD_INV_VALUE, })
        )

        # get sectors
        df_allocate[_FIELD_INV_SECTOR] = str(df[_FIELD_INV_SECTOR].iloc[0])
        df_allocate[_FIELD_INV_SUBSECTOR] = str(df[_FIELD_INV_SUBSECTOR].iloc[0])
        df_allocate[_FIELD_CW_DISPLAY_SUBSECTOR] = subsec_disp[0]

        df_allocated.append(df_allocate, )

    # join together
    df_allocated = sf._concat_df(df_allocated)

    #df_unallocated = df_inventory[~inds_split].reset_index(drop = True, )
    df_unallocated = pd.merge(
        df_inventory[~inds_split]
            .reset_index(drop = True, ),
        df_cw_ssp
            .get([_FIELD_CW_SUBSECTOR, _FIELD_CW_GAS, _FIELD_CW_DISPLAY_SUBSECTOR])
            .rename(
                columns = {
                    _FIELD_CW_GAS: _FIELD_INV_GAS,
                    _FIELD_CW_SUBSECTOR: _FIELD_INV_SUBSECTOR,
                }
            ),
        how = "left",
    )

    
    out = (df_allocated, df_unallocated, )

    return out



def build_synthetic_sectors(
    df_base_sisepuede: pd.DataFrame,
    time_periods: 'TimePeriods',
    model_attributes: 'ModelAttributes',
    df_inventory: pd.DataFrame,
    df_ssp_cw_accounted: pd.DataFrame,
    df_ssp_cw_unaccounted: pd.DataFrame,
    df_years: pd.DataFrame,
    delim_variable_fields: str = _DELIM_FIELDS_EMISSION,
    interpolate_from_zero: bool = True,
) -> pd.DataFrame:
    """Build synthetic historical emissions using data from SSP.

    Merges emissions from df_base_sisepuede into df_years to create base 
        emissions.
    """

    ##  ESTIMATE FROM SISEPUEDE 
    
    df_estimated = []

    # add in years
    df_base = (
        time_periods
        .tps_to_years(
            df_base_sisepuede, 
            field_year = _FIELD_INV_YEAR,
        )
    )
    
    for i, row in df_ssp_cw_unaccounted.iterrows():

        # get fields to sum over
        fields = str(row[_FIELD_CW_VARIABLE_FIELDS]).split(delim_variable_fields, )
        query = [x in df_base_sisepuede.columns for x in fields]
        if not all(query):
            fields_missing = sf.format_print_list([x for x in fields if x not in df_base.columns])
            raise RuntimeError(f"Emission fields {fields_missing} not found.")

        
        df_new = pd.merge(
            df_years,
            df_base[[_FIELD_INV_YEAR] + fields],
            how = "left",
        )

        # interpolate--leave separate in case we want to set to align with 0
        df_new = (
            df_new
            .interpolate()
        )
        
        # add some fields 
        df_new[_FIELD_CW_DISPLAY_SUBSECTOR] = row[_FIELD_CW_DISPLAY_SUBSECTOR]
        df_new[_FIELD_CW_GAS] = row[_FIELD_CW_GAS]
        df_new[_FIELD_CW_SUBSECTOR] = row[_FIELD_CW_SUBSECTOR]
        df_new[_FIELD_INV_EST_FLAG] = 1
        df_new[_FIELD_INV_VALUE] = df_new[fields].sum(axis = 1)

        df_new = df_new.drop(columns = fields, )
        
        df_estimated.append(df_new, )

    df_estimated = (
        sf._concat_df(df_estimated, )
        .rename(
            columns = {
                _FIELD_CW_GAS: _FIELD_INV_GAS,
                _FIELD_CW_SUBSECTOR: _FIELD_INV_SUBSECTOR,
            }
        )
    )


    
    ##  ADJUST INVENTORY THAT IS NOT ESTIMATED

    df_allocated, df_unallocated = allocate_accounted_all_ghgs_using_ssp(
        df_base_sisepuede,
        df_inventory, 
        df_ssp_cw_accounted,
        time_periods,
    )

    # set some flags
    df_unallocated[_FIELD_INV_EST_FLAG] = 0
    df_allocated[_FIELD_INV_EST_FLAG] = 2   # 2 means gasses were allocated proportionally from SSP

    # convert "unallocated" to co2e
    vec_new = df_unallocated[_FIELD_INV_GAS].apply(model_attributes.get_gwp)
    #df_unallocated[_FIELD_INV_VALUE] = df_unallocated[_FIELD_INV_VALUE].to_numpy()*vec_new
    

    ##  FORMATTING

    df_estimated = pd.merge(
        df_estimated,
        df_ssp_cw_unaccounted[[_FIELD_CW_SECTOR, _FIELD_CW_DISPLAY_SUBSECTOR]]
            .drop_duplicates()
            .rename(
                columns = {
                    _FIELD_CW_SECTOR: _FIELD_INV_SECTOR,
                }
            ),
        how = "left"
    )


    fields_ord = [
        _FIELD_INV_SECTOR,
        _FIELD_CW_DISPLAY_SUBSECTOR,
        _FIELD_INV_SUBSECTOR,
        _FIELD_INV_GAS,
        _FIELD_INV_YEAR,
        _FIELD_INV_VALUE,
        _FIELD_INV_EST_FLAG,
    ]


    df_out = (
        sf._concat_df(
            [
                df_allocated[fields_ord],
                df_estimated[fields_ord],
                df_unallocated[fields_ord]
            ]
        )
        .sort_values(
            by = [
                _FIELD_INV_SECTOR,
                _FIELD_CW_DISPLAY_SUBSECTOR,
                _FIELD_INV_GAS,
                _FIELD_INV_YEAR,
            ]
        )
        .reset_index(drop = True, )
        .rename(
            columns = {
                _FIELD_INV_VALUE: _FIELD_INV_VALUE_CO2E,
            }
        )
    )

    return df_out



def get_inventory_and_cw_dfs(
    path_inventory: pathlib.Path,
    path_crosswalk: pathlib.Path,
    source: str = "National Communication 3",
) -> pd.DataFrame:
    """Get the NDC inventory trajectories. Returns a tuple of the form:

        (
            df_inventory,             # DataFrame storing the inventory
            df_ssp_cw_accounted,      # crosswalk between SSP and the inventory (accounted values)
            df_ssp_cw_unaccounted,    # crosswalk between SSP and the inventory (unaccounted values)
            df_years,                 # all years in the inventory
            ## df_sector_map,            # mapping of display subsectors to SSP sectors
        )
    """

    # get inventory
    df_inventory = pd.read_csv(path_inventory, )
    df_inventory = (
        df_inventory[
            df_inventory[_FIELD_INV_SOURCE].isin([source])
            & ~df_inventory[_FIELD_INV_GAS].isin(["CO", "NOx"])
        ]
        .reset_index(drop = True, )
        .drop(columns = [_FIELD_INV_SOURCE])
    )

    df_inventory[_FIELD_INV_GAS] = [x.lower() for x in list(df_inventory[_FIELD_INV_GAS])]
    

    # get all years
    df_years = pd.DataFrame(
        {
            _FIELD_INV_YEAR: np.arange(
                df_inventory[_FIELD_INV_YEAR].min(),
                df_inventory[_FIELD_INV_YEAR].max() + 1,
            )
            .astype(int)
        }
    )

    # get the crosswalk--split into accounted and unaccounted
    df_ssp_cw = pd.read_csv(path_crosswalk, )
    inds_accounted = df_ssp_cw[_FIELD_CW_ACCOUNTED] == 1

    df_ssp_cw_accounted = df_ssp_cw[inds_accounted].reset_index(drop = True, )
    df_ssp_cw_unaccounted = df_ssp_cw[~inds_accounted].reset_index(drop = True, )
    # df_sector_map = df_ssp_cw[[_FIELD_CW_SECTOR, _FIELD_CW_SUBSECTOR]].drop_duplicates()
    

    out = (
        df_inventory, 
        df_ssp_cw_accounted,
        df_ssp_cw_unaccounted,
        df_years, 
    )
    
    return out



def get_inventory_tables(
    df_base_ssp: pd.DataFrame,
    path_inventory: pathlib.Path,
    path_crosswalk: pathlib.Path,
    model_attributes: 'ModelAttributes',
    time_periods: 'TimePeriods',
    agg_to_display: bool = True,
) -> pd.DataFrame:
    """Retrieve the inventory tables. Returns the modified inventory and the 
        crosswalk in a tuple, i.e.

        (
            df_inventory_synthetic,
            df_cw_to_ssp_field
        )

    Function Arguments
    ------------------
    df_base_ssp : pd.DataFrame
        Base outputs from SISEPUEDE to use for filling in gaps and allocating
    path_inventory : pathlib.Path
        Path to the inventory file (unadjusted)
    path_crosswalk : pathlib.Path
        Path to the crosswalk to SSP fields for decompositon
    model_attributes : ModelAttributes
        SISEPUEDE ModelAttributes object used for some assumptions around gasses
    time_periods : TimePeriods
        support_classes.TimePeriods object use for converting to and from years

    Keyword Arguments
    -----------------
    agg_to_display : bool
        Aggregate output files to only show display subsector?
    """

    tup_icdfs = get_inventory_and_cw_dfs(
        path_inventory,
        path_crosswalk,
    )

    (
        df_inventory, 
        df_ssp_cw_accounted, 
        df_ssp_cw_unaccounted, 
        df_years, 
    ) = tup_icdfs


    ##  BUILD THE SYNTHETIC SECTORS AND CW

    df_inv = build_synthetic_sectors(
        df_base_ssp,
        time_periods,
        model_attributes,
        *tup_icdfs,
    )

    df_cw = sf._concat_df(
        [
            df_ssp_cw_accounted,
            df_ssp_cw_unaccounted
        ]
    ) 
    
    if agg_to_display:
        df_cw = aggregate_cw_to_display(df_cw, )
        df_inv = aggregate_inv_to_display(df_inv, )

    out = (df_inv, df_cw, )

    return out