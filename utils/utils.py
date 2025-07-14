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

class GeneralUtils:

    @staticmethod
    def extend_projection(df, start_year, end_year):
        """
        Extend a dataframe by repeating the last row's values for future years.

        Parameters:
            df (pd.DataFrame): Input dataframe with a 'year' column.
            start_year (int): The first year to extend (inclusive).
            end_year (int): The last year to extend (inclusive).

        Returns:
            pd.DataFrame: Extended dataframe.
        """
        last_values = df.iloc[-1, 1:]
        future_years = range(start_year, end_year + 1)
        future_rows = pd.DataFrame({'year': future_years})
        for col in last_values.index:
            future_rows[col] = last_values[col]
        df_extended = pd.concat([df, future_rows], ignore_index=True)
        df_extended = df_extended.sort_values('year').reset_index(drop=True)
        return df_extended



class TransportUtils:

    @staticmethod
    def compute_passenger_km(
        domestic_arrivals: dict,
        domestic_departures: dict,
        international_departures: dict,
        factor_domestic: int = 300,
        factor_international: int = 2500
    ) -> dict:
        """
        Computes total passenger-kilometers (pkm) for aviation, applying separate distance factors
        for domestic and international passengers.

        Args:
            domestic_arrivals (dict): {year: count}
            domestic_departures (dict): {year: count}
            international_departures (dict): {year: count}
            factor_domestic (int): Distance multiplier for domestic trips (default: 300 km)
            factor_international (int): Distance multiplier for international trips (default: 2500 km)

        Returns:
            dict: {year: total_passenger_km}
        """
        years = set(domestic_arrivals) | set(domestic_departures) | set(international_departures)
        result = {}
        for year in sorted(years):
            dom_arr = domestic_arrivals.get(year, 0)
            dom_dep = domestic_departures.get(year, 0)
            intl_dep = international_departures.get(year, 0)

            domestic_pkm = (dom_arr + dom_dep) * factor_domestic
            international_pkm = intl_dep * factor_international

            result[year] = domestic_pkm + international_pkm
        return result
    
    @staticmethod
    def compute_freight_mtkm(
        domestic_cargo: dict,
        international_exports: dict,
        factor_domestic: int = 300,
        factor_international: int = 2500
    ) -> dict:
        """
        Computes total freight in million tonne-kilometers (mtkm) for aviation,
        using separate distance factors for domestic and international cargo.

        Args:
            domestic_cargo (dict): {year: tonnes of domestic cargo}
            international_exports (dict): {year: tonnes of international exports}
            factor_domestic (int): Avg distance in km for domestic cargo (default: 300 km)
            factor_international (int): Avg distance in km for international exports (default: 2500 km)

        Returns:
            dict: {year: total_freight_mtkm}
        """
        years = set(domestic_cargo) | set(international_exports)
        result = {}
        for year in sorted(years):
            dom_tonnes = domestic_cargo.get(year, 0)
            intl_tonnes = international_exports.get(year, 0)

            dom_mtkm = (dom_tonnes * factor_domestic) / 1_000_000
            intl_mtkm = (intl_tonnes * factor_international) / 1_000_000

            result[year] = dom_mtkm + intl_mtkm
        return result
    

