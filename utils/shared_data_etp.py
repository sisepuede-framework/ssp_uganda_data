"""Shared data from the IEA Energy Transition Plan
https://www.iea.org/reports/uganda-energy-transition-plan
"""
from typing import *
import utils.classes as cl





#######################
#   BUILD DATASETS    #
#######################

_DICT_MODVARS_OUTPUT_ACTIVITY_RATIOS_PETROLEUM_FIG_2_27 = {
    "Fuel Production NemoMod OutputActivityRatio Diesel": 0.22,
    "Fuel Production NemoMod OutputActivityRatio Gasoline": 0.46,
    "Fuel Production NemoMod OutputActivityRatio Hydrocarbon Gas Liquids": 0.07,
    "Fuel Production NemoMod OutputActivityRatio Kerosene": 0.04,
    "Fuel Production NemoMod OutputActivityRatio Oil": 0.04,   
}

ETPData = cl.Dataset(
    {
        "figure_2_27": {
            "dict_output_activity_ratios": _DICT_MODVARS_OUTPUT_ACTIVITY_RATIOS_PETROLEUM_FIG_2_27,
        }
    }
)
     

        