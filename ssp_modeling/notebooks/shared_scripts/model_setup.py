"""
model_setup.py
--------------
Initializes the SISEPUEDE file structure and model attributes.
"""

import numpy as np
import pandas as pd
from typing import Tuple

import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_file_structure as sfs


def get_file_structure(
    y0: int = 2015,
    y1: int = 2070,
) -> Tuple[sfs.SISEPUEDEFileStructure, att.AttributeTable]:
    """
    Build a SISEPUEDEFileStructure with a custom time-period attribute table
    covering years [y0, y1] inclusive.
    """
    file_struct = sfs.SISEPUEDEFileStructure(initialize_directories=False)

    key_time_period = file_struct.model_attributes.dim_time_period
    key_year        = file_struct.model_attributes.field_dim_year

    years = np.arange(y0, y1 + 1).astype(int)
    attribute_time_period = att.AttributeTable(
        pd.DataFrame({
            key_time_period: range(len(years)),
            key_year: years,
        }),
        key_time_period,
    )

    file_struct.model_attributes.update_dimensional_attribute_table(attribute_time_period)

    return file_struct, attribute_time_period


def initialize_model(y0: int = 2015, y1: int = 2070):
    """
    Initialize SISEPUEDE model and return
    (file_structure, attribute_table, model_attributes, regions).
    """
    file_structure, attribute_table = get_file_structure(y0=y0, y1=y1)
    matt    = file_structure.model_attributes
    regions = sc.Regions(matt)
    return file_structure, attribute_table, matt, regions
