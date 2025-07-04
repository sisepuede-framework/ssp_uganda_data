import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class EDAUtils:

    @staticmethod
    def compare_variables(new_df, old_df, var_names, title=None):
        """
        Compare variables from two dataframes using line plots.

        Parameters:
        df_1 (pd.DataFrame): First dataframe.
        df_2 (pd.DataFrame): Second dataframe.
        var_names (list): List of variable names to compare (must exist in both dataframes).
        title (str): Title of the plot.
        """
        n_vars = len(var_names)
        plt.figure(figsize=(6 * n_vars, 5))
        for i, var in enumerate(var_names):
            plt.subplot(1, n_vars, i + 1)
            plt.plot(new_df[var].values, label=f"{var} new data")
            plt.plot(old_df[var].values, label=f"{var} old data")
            plt.xlabel("Index")
            plt.ylabel(var)
            plt.title(f"Comparison of new and old data")
            plt.legend()
            plt.grid()
        if title:
            plt.suptitle(title)
        plt.tight_layout(rect=[0, 0, 1, 0.95] if title else None)
        plt.show()