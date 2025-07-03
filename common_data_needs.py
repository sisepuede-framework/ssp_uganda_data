
import os, os.path
import pandas as pd
import pathlib
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
from typing import *



################################
#    SETUP GLOBAL VARIABLES    #
################################


# set up some paths
_PATH_CUR = pathlib.Path(__file__).parents[0]
_PATH_INPUTS = _PATH_CUR.joinpath("input_data")
_PATH_OUTPUTS = _PATH_CUR.joinpath("output_data")
_PATH_BASE_RAW_DATA = _PATH_INPUTS.joinpath("sisepuede_raw_global_inputs_uganda.csv")


# setup some SISEPUEDE variables
_SISEPUEDE_FILE_STRUCTURE = sfs.SISEPUEDEFileStructure()

# model attributes and associated support classes
_SISEPUEDE_MODEL_ATTRIBUTES = _SISEPUEDE_FILE_STRUCTURE.model_attributes
_SISEPUEDE_REGIONS = sc.Regions(_SISEPUEDE_MODEL_ATTRIBUTES, )
_SISEPUEDE_TIME_PERIODS = sc.TimePeriods(_SISEPUEDE_MODEL_ATTRIBUTES, )

# setup models--don't create julia connect
_SISEPUEDE_MODELS = sm.SISEPUEDEModels(
    _SISEPUEDE_MODEL_ATTRIBUTES,
    allow_electricity_run = False,
    initialize_julia = False, 
)





##########################
#    DEFINE FUNCTIONS    #
##########################

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






    