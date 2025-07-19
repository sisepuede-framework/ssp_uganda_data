
import os, os.path
import pandas as pd
import pathlib
import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
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
    file_struct = sfs.SISEPUEDEFileStructure()

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
    df_base = get_raw_ssp_inputs()

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



def get_raw_ssp_inputs(
) -> pd.DataFrame:
    """Retrieve the base, raw Uganda inputs for SISEPUEDE,
        which are composed of the V0 database. 
    """
    df = pd.read_csv(_PATH_BASE_RAW_DATA, )
    df = (
        _SISEPUEDE_TIME_PERIODS
        .tps_to_years(df, )
        .drop(columns = _SISEPUEDE_TIME_PERIODS.field_time_period, )
    )
    
    return df



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










    