
import numpy as np
import os, os.path
import pandas as pd
import pathlib
import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_examples as sxl
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.utilities._toolbox as sf
from numpy import arange
from typing import *





    

################################
#    SETUP GLOBAL VARIABLES    #
################################

def get_file_structure(
    y0: int = 2015,
    y1: int = 2070,
) -> Tuple[sfs.SISEPUEDEFileStructure, att.AttributeTable]:
    """Get the SISEPUEDE File Structure and update the attribute table
        with new years.
    """
    # setup some SISEPUEDE variables and update time period
    file_struct = sfs.SISEPUEDEFileStructure(
        initialize_directories = False,
    )

    # get some keys
    key_time_period = file_struct.model_attributes.dim_time_period
    key_year = file_struct.model_attributes.field_dim_year


    ##  BUILD THE ATTRIBUTE AND UPDATE

    # setup the new attribute table
    ra = arange(0, y1 - y0 + 1, ).astype(int)
    attribute_time_period = att.AttributeTable(
        pd.DataFrame(
            {
                key_time_period: ra,
                key_year: y0 + ra,
            }
        ),
        key_time_period,
        
    )

    # finally, update the ModelAttributes inside the file structure
    (
        file_struct
        .model_attributes
        .update_dimensional_attribute_table(
            attribute_time_period,
        )
    )

    # return the tuple
    out = (file_struct, attribute_time_period, )

    return out



    
# set up some paths
_PATH_CUR = pathlib.Path(__file__).parents[0]
_PATH_PROJ = _PATH_CUR.parents[0]
_PATH_INPUTS = _PATH_PROJ.joinpath("input_data")
_PATH_OUTPUTS = _PATH_PROJ.joinpath("output_data")
_PATH_BASE_RAW_DATA = _PATH_INPUTS.joinpath("sisepuede_raw_global_inputs_uganda.csv")

# model attributes and associated support classes
_SISEPUEDE_EXAMPLES = sxl.SISEPUEDEExamples()
_SISEPUEDE_FILE_STRUCTURE, _ATTRIBUTE_TABLE_TIME_PERIOD = get_file_structure()
_SISEPUEDE_MODEL_ATTRIBUTES = _SISEPUEDE_FILE_STRUCTURE.model_attributes
_SISEPUEDE_REGIONS = sc.Regions(_SISEPUEDE_MODEL_ATTRIBUTES, )
_SISEPUEDE_TIME_PERIODS = sc.TimePeriods(_SISEPUEDE_MODEL_ATTRIBUTES, )

# setup models
_SISEPUEDE_MODELS = sm.SISEPUEDEModels(
    _SISEPUEDE_MODEL_ATTRIBUTES,
    allow_electricity_run = True,
    fp_julia = _SISEPUEDE_FILE_STRUCTURE.dir_jl,
    fp_nemomod_reference_files = _SISEPUEDE_FILE_STRUCTURE.dir_ref_nemo,
    initialize_julia = True, 
)







##########################
#    DEFINE FUNCTIONS    #
##########################

class MissingValuesError(Exception):
    pass

    
def _build_from_outputs(
    years_required: tuple, 
    extension_read: str = "csv",
    fns_exclude: Union[List[str], None] = None,
    force_complete_build: bool = False,
    merge_type: str = "outer",
    path_csvs: pathlib.Path = _PATH_OUTPUTS,
    print_info: bool = False,
    stop_on_error: bool = False,
    **kwargs
) -> pd.DataFrame:
    """Build an input table for from data outputs stored in the output
        data repo.

    Function Arguments
    ------------------
    years_required : Tuple[int, int]
        Tuple giving years that are required to run the analysis. Will
        confirm these years are present.
        
    Keyword Arguments
    -----------------
    extension_read : str
        Default extension to read
    fns_exclude : Union[List[str], None]
        Optional list of file names to exclude
    force_complete_build : bool
        If any fields are missing, pull from examples df?
    merge_type : str
        Merge type to pass to pd.merge as 'how = merge_type'
    path_csvs : pathlib.Path
        Directory storing CSVs
    print_info : bool
        Print info while iterating?
    stop_on_error : bool
        Stop if there's a read error? If False, skips files that produce 
        errors.
    **kwargs :
        Passed to pd.read_csv()
    """
    # init
    global _DF_OVERWRITE
    global _DF_CUR
    global _PATHS_ITER
    _DF_OVERWRITE = None
    _DF_CUR = None
    _PATHS_ITER = []
    
    # get raw inputs
    df_examples = _SISEPUEDE_EXAMPLES("input_data_frame")
    df_base = get_raw_ssp_inputs()

    
    ##  DEAL WITH MISSING FIELDS
    
    fields_missing = [
        x for x in _SISEPUEDE_MODEL_ATTRIBUTES.all_variable_fields_input
        if x not in df_base.columns
    ]

    if len(fields_missing) > 0:
        if not force_complete_build:
            fields_missing = sf.format_print_list(fields_missing, )
            raise RuntimeError(f"Cannot proceed: fields {fields_missing} not found.")

        # add in values from examples
        df_base = (
            pd.merge(
                df_base,
                df_examples
                .get(
                    [_SISEPUEDE_MODEL_ATTRIBUTES.dim_time_period] + fields_missing
                ),
                how = "left",
            )
            .interpolate()
            .bfill()
            .reset_index(drop = True)
        )
        

    
    shp = None

    # check for available files
    df_overwrite = None
    for path in path_csvs.iterdir():

        # skip?
        if isinstance(fns_exclude, list):
            if path.parts[-1] in fns_exclude:
                continue
        
        # skip non-csvs
        if path.suffix != f".{extension_read}": continue

        # try reading the file
        try:
            df_cur = (
                pd.read_csv(path, **kwargs)
                .drop_duplicates()
            )
            
        except Exception as e:
            msg = f"Error reading {extension_read} file at {path}: {e}"
            if stop_on_error:
                raise RuntimeError(msg)

            warnings.warn(msg)
            continue

        shp = df_cur.shape
        
        # if successful, update the df
        df_overwrite = (
            df_cur
            if df_overwrite is None
            else pd.merge(
                df_overwrite,
                df_cur,
                how = merge_type,
            )
        )

        _PATHS_ITER.append(path)
        if print_info: print(f"Shape after path {path}: {df_overwrite.shape}\n")


    ##  CHECKS AND FINAL OVERWRITE

    df_overwrite = df_overwrite.dropna()
    
    # check that all needed years are included
    set_years_req = set(range(years_required[0], years_required[1] + 1))
    proceed = set_years_req.issubset(set(df_overwrite[_SISEPUEDE_TIME_PERIODS.field_year]))
    if not proceed:
        _DF_OVERWRITE = df_overwrite
        raise MissingValuesError(f"Years missing from the dataframe. Check the dataframe at _DF_OVERWRITE")

    # merge df_base to set of years available and fill
    df_base = (
        pd.merge(
            df_overwrite[
                df_overwrite[_SISEPUEDE_TIME_PERIODS.field_year]
                .isin(set_years_req)
            ][[_SISEPUEDE_TIME_PERIODS.field_year]],
            df_base,
            how = "left",
        )
        .interpolate()
        .bfill()
        .ffill()
    )
    
    # overwrite fields in base to prouce output
    df_out = sf.match_df_to_target_df(
        df_base,
        df_overwrite,
        [
            _SISEPUEDE_TIME_PERIODS.field_year,
        ],
        overwrite_only = False,
    )
    
    df_out = (
        _SISEPUEDE_TIME_PERIODS
        .years_to_tps(df_out)
        .drop(
            columns = _SISEPUEDE_TIME_PERIODS.field_year,
        )
    )

    if _SISEPUEDE_REGIONS.key in df_out.columns:
        df_out.drop(columns = _SISEPUEDE_REGIONS.key, inplace = True, )
        
    
    
    return df_out



def get_files_from_matchstr(
    matchstr: str,
) -> pd.DataFrame:
    """Read output files that start with matchstr
    """
    dfs_read = [
        x for x in sorted(os.listdir(_PATH_OUTPUTS))
        if x.startswith(matchstr)
    ]

    # get some data
    df_data = None
    
    for fn in dfs_read:
        path = os.path.join(_PATH_OUTPUTS, fn)
        df_cur = pd.read_csv(path, )

        df_data = (
            df_cur
            if df_data is None
            else pd.merge(df_cur, df_data, how = "inner", )
        )

    return df_data




def get_raw_ssp_inputs(
) -> pd.DataFrame:
    """Retrieve the base, raw Uganda inputs for SISEPUEDE,
        which are composed of the V0 database. 
    """
    df = pd.read_csv(_PATH_BASE_RAW_DATA, )

    if _SISEPUEDE_TIME_PERIODS.field_year not in df.columns:
        df = (
            _SISEPUEDE_TIME_PERIODS
            .tps_to_years(df, )
            .drop(columns = _SISEPUEDE_TIME_PERIODS.field_time_period, )
        )
    
    return df



def mix_from_base_year_future(
    df: pd.DataFrame,
    fields_ind: List[str],
    alpha_original: float,
    time_periods: 'TimePeriods',
    year_base: int,
    fields: Union[List[str], None] = None,
) -> pd.DataFrame:
    """Using a base year to project forward with final value, mix 
        the base year projected trajectory with the defined trajectory.

    Function Arugments
    ------------------
    df : pd.DataFrame
        DataFrame to access information from. Must include 
        time_periods.field_year
    fields_ind : List[str]
        Index fields. Should include time_periods.field_year, but if not,
        the field is added
    alpha_original : float
        Fraction of original trajectory to keep; 0 will return only the
        flat projection
    time_periods : TimePeriods
        TimePeriods object used for managing time periods
    year_base : int
        Year from which to continue the flat trajectory
        
    Keyword Arugments
    -----------------
    fields : Union[List[str], None]
        Optional subset of fields in the DataFrame to apply to. Will only
        return those fields.

    """

    # check index fields
    fields_ind = [] if not sf.islistlike(fields_ind) else list(fields_ind)
    if time_periods.field_year not in fields_ind:
        fields_ind.append(time_periods.field_year)
    fields_ind = [x for x in fields_ind if x in df.columns and x]

    # check data fields
    fields = (
        [x for x in fields if (x in df.columns)]
        if sf.islistlike(df)
        else [x for x in df.columns if x not in fields_ind]
    )

    # get all years
    df_inds = df[fields_ind].copy()

    # get data only from base year on
    df_from_base_year = df[
        df[time_periods.field_year] <= year_base
    ][fields_ind + fields]

    df_from_base_year = (
        pd.merge(
            df_inds,
            df_from_base_year,
            how = "left"
        )
        .ffill()
    )


    ##  BUILD A RAMP VECTOR AND MIX

    w = np.where(df_inds[time_periods.field_year].to_numpy() == year_base, )[0]
    vec_ramp = sf.ramp_vector(
        df.shape[0],
        0.0,
        0,
        r_0 = w,
        r_1 = min(w + 10, df.shape[0])
    )
    vec_mix = 1 - vec_ramp*alpha_original
    
    # mix?
    # arr_new = sf.do_array_mult(df[fields].to_numpy(), vec_mix, )
    # arr_new += sf.do_array_mult(df_from_base_year[fields].to_numpy(), 1 - vec_mix, )

    arr_new = df[fields].to_numpy().copy()*alpha_original
    arr_new += df_from_base_year[fields].to_numpy()*(1 - alpha_original)
    df_out = df[fields_ind].copy()
    df_out[fields] = arr_new

    return df_out



def _read_output_csv(
    nm: str,
    **kwargs,
) -> Union[pd.DataFrame, None]:
    """Read an output CSV file quickly. **kwargs are passed to 
        pd.read_csv()
    """
    path_try = pathlib.Path(_PATH_OUTPUTS.joinpath(f"{nm}.csv"))
    if not path_try.is_file():
        return None

    df_out = pd.read_csv(path_try, **kwargs, )
    
    return df_out
    
        
    
def _setup_sisepuede_elements(
) -> Dict:
    """Call SISEPUEDE elements for use in other contexts. Basically
        returns pointers to the objects in this module.
    """

    dict_out = {
        "model_attributes": _SISEPUEDE_MODEL_ATTRIBUTES,
        "models": _SISEPUEDE_MODELS,
        "regions": _SISEPUEDE_REGIONS,
        "time_periods": _SISEPUEDE_TIME_PERIODS,
    }

    return dict_out



def spawn_years_space_df(
    year_range: Tuple[int, int],
) -> pd.DataFrame:
    """Shortcut to spawn a dataframe of years
    """
    # build a dataframe with the universe of years
    df_space_years = pd.DataFrame(
        {
            _SISEPUEDE_TIME_PERIODS.field_year: range(*year_range),
        }
    )

    return df_space_years

















    