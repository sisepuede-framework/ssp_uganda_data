"""Some basic functions that are repeated in a number of places.
"""
import numpy as np
import os





def isnumber(
    x: Any,
    integer: bool = False,
    skip_nan: bool = True,
) -> bool:
    """Check if x is an integer or float. Set integer = True to force integer
        only checks. skip_nan = True will return False if x is np.nan
    """
    types_check = (
        (int, float, np.int64, np.int32, np.float64, np.float32)
        if not integer
        else (int, np.int64, np.int32)
    )

    # check type and verify whether or not np.nan matters
    out = isinstance(x, types_check)
    out = (not np.isnan(x)) if (out & skip_nan) else out

    return out