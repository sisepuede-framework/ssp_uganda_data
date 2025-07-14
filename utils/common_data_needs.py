
import os, os.path
import pandas as pd
import pathlib
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.utilities._toolbox as sf
from typing import *



################################
#    SETUP GLOBAL VARIABLES    #
################################


# set up some paths
_PATH_CUR = pathlib.Path(__file__).parents[0]
_PATH_PROJ = _PATH_CUR.parents[0]
_PATH_INPUTS = _PATH_PROJ.joinpath("input_data")
_PATH_OUTPUTS = _PATH_PROJ.joinpath("output_data")
_PATH_BASE_RAW_DATA = _PATH_INPUTS.joinpath("sisepuede_raw_global_inputs_uganda.csv")


# setup some SISEPUEDE variables
_SISEPUEDE_FILE_STRUCTURE = sfs.SISEPUEDEFileStructure()

# model attributes and associated support classes
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
    extension_read: str = "csv",
    merge_type: str = "outer",
    path_csvs: pathlib.Path = _PATH_OUTPUTS,
    stop_on_error: bool = False,
    **kwargs
) -> pd.DataFrame:
    """Build an input table for from data outputs stored in the output
        data repo.

    Function Arguments
    ------------------

    Keyword Arguments
    -----------------
    extension_read : str
        Default extension to read
    merge_type : str
        Merge type to pass to pd.merge as 'how = merge_type'
    path_csvs : pathlib.Path
        Directory storing CSVs
    stop_on_error : bool
        Stop if there's a read error? If False, skips files that produce 
        errors.
    **kwargs :
        Passed to pd.read_csv()
    """
    # init
    global _DF_OVERWRITE
    _DF_OVERWRITE = None
    
    # get raw inputs
    df_base = get_raw_ssp_inputs()


    # check for available files
    df_overwrite = None
    for path in path_csvs.iterdir():
        # skip non-csvs
        if path.suffix != f".{extension_read}": continue

        # try reading the file
        try:
            df_cur = pd.read_csv(path, **kwargs)
        except Exception as e:
            msg = f"Error reading {extension_read} file at {path}: {e}"
            if stop_on_error:
                raise RuntimeError(msg)

            warnings.warn(msg)
            continue

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


    ##  CHECKS AND FINAL OVERWRITE

    # check for NAs
    if df_overwrite.dropna().shape != df_overwrite.shape:
        _DF_OVERWRITE = df_overwrite
        raise MissingValuesError(f"NAs found in df_overwite. Check the dataframe at _DF_OVERWRITE")

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









    