"""
postprocessing.py
-----------------
Intertemporal decomposition / rescaling of SSP simulation output.
"""

import sys
import pandas as pd
from pathlib import Path


def run_decomposition(
    df_export: pd.DataFrame,
    project_dir: Path,
    targets_path: Path,
    iso_code3: str,
    year_ref: int,
    region: str,
    output_path: Path,
) -> pd.DataFrame:
    """
    Rescale *df_export* against historical inventory targets and return
    the decomposed DataFrame.  Also writes the result to *output_path*.

    Parameters
    ----------
    df_export    : wide-format SSP simulation output (filtered primary_ids)
    project_dir  : repo root (added to sys.path so the module resolves)
    targets_path : path to emission_targets CSV
    iso_code3    : 3-letter ISO country code (e.g. "UGA")
    year_ref     : reference / base year for rescaling (e.g. 2019)
    region       : region label used inside the model (e.g. "uganda")
    output_path  : where to write the decomposed CSV (None = skip)
    """
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    from ssp_modeling.output_postprocessing.intertemporal_decomposition import (
        run_postprocessing,
    )

    df_decomposed = run_postprocessing(
        df_ssp_output         = df_export,
        targets_path          = targets_path,
        iso_code3             = iso_code3,
        year_ref              = year_ref,
        region                = region,
        initial_conditions_id = "_0",
        output_path           = output_path,
    )

    return df_decomposed
