"""Store some dummy classes for easier navigation and figure tracing
"""
from typing import *


class Dataset:
    """Add datasets from figures
    """
    def __init__(self,
        dict_figures: Dict[str, Dict[str, Any]],
    ) -> None:

        figures = []
        if isinstance(dict_figures, dict):
            for k, v in dict_figures.items():
                fig = Figure(v, )
                figures.append(k)
                
                setattr(self, k, fig)


        ##  SET PROPERTIES

        self.figures = figures
        
        return None


        
class Figure: 
    """Wrapped for data from figures
    """
    def __init__(self,
        dict_vals: Dict[Any, Any],
    ) -> None:

        all_variables = []
        
        if isinstance(dict_vals, dict):
            for k, v in dict_vals.items():
                all_variables.append(k)
                setattr(self, k, v)


        ##  SET PROPERTIES

        self.all_variables = all_variables
                
        return None