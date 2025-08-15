import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression

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
    
    @staticmethod
    def extend_years_backward(df, year_col, template_year, new_years):
        """
        Extend a DataFrame by prepending rows for new_years using the values from template_year.
        Args:
            df (pd.DataFrame): The DataFrame to extend.
            year_col (str): The name of the year column.
            template_year (int): The year to use as a template for new rows.
            new_years (list): List of years (int) to add.
        Returns:
            pd.DataFrame: Extended DataFrame with new years prepended and sorted.
        """
        df[year_col] = df[year_col].astype(int)
        row_template = df[df[year_col] == template_year].iloc[0]
        new_rows = []
        for year in new_years:
            new_row = row_template.copy()
            new_row[year_col] = int(year)
            new_rows.append(new_row)
        df_extended = pd.concat([pd.DataFrame(new_rows), df], ignore_index=True)
        df_extended[year_col] = df_extended[year_col].astype(int)
        df_extended = df_extended.sort_values(by=year_col).reset_index(drop=True)
        return df_extended
    
    @staticmethod
    def check_row_sums_to_one(df, exclude_columns=["year"], tol=1e-6):
        """
        Checks whether each row in the DataFrame sums to 1, excluding specified columns.

        Parameters:
        - df (pd.DataFrame): The DataFrame to check.
        - exclude_columns (list): List of column names to exclude from the sum.
        - tol (float): Tolerance for floating point comparison.

        Returns:
        - pd.Series: Boolean Series indicating if each row sums to 1 within the tolerance.
        - bool: Whether all rows pass the check.
        """
        cols_to_check = df.columns.difference(exclude_columns)
        row_sums = df[cols_to_check].sum(axis=1)
        is_valid = np.isclose(row_sums, 1.0, atol=tol)
        all_valid = is_valid.all()
        return is_valid, all_valid
    
    @staticmethod
    def check_duplicates(df, year_col='year'):
        # Check for duplicated years
        if df[year_col].duplicated().any():
            print("Duplicated years found in the DataFrame.")
            print(df[df[year_col].duplicated()])
        else:
            print("No duplicated years found in the DataFrame.")

        # Check for duplicated rows
        if df.duplicated().any():
            print("Duplicated rows found in the DataFrame.")
            print(df[df.duplicated()])
        else:
            print("No duplicated rows found in the DataFrame.")
    
    @staticmethod
    def smooth_timeseries_df(
        df: pd.DataFrame,
        year_col: str = "year",
        method: str = "hp",                 # 'hp' | 'lowess' | 'savgol' | 'ma'
        hp_lambda: float = 100.0,           # common lambda for annual data; try 6.25–100
        lowess_frac: float = 0.15,          # smoothing span (~% of data) for LOWESS
        savgol_window: int = 9,             # must be odd and >= polyorder+2
        savgol_polyorder: int = 2,
        ma_window: int = 5,                 # centered moving average window
        clip_01: bool = True,               # clip values to [0,1]
        enforce_simplex: bool = True        # row-wise renormalization to sum to 1 (excl. year)
    ) -> pd.DataFrame:
        """
        Smooth all numeric columns except `year_col` using the selected method.
        Preserves the input structure/order of rows.
        """

        df = df.copy()
        if year_col not in df.columns:
            raise ValueError(f"`{year_col}` not found in df")

        # sort by year so filters see a proper time order, then unsort at the end
        order_idx = df.index
        df = df.sort_values(year_col).reset_index(drop=True)

        # target columns: numeric & not year
        value_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != year_col]

        # optional imports per method
        if method == "hp":
            try:
                import statsmodels.api as sm
                hpfilter = sm.tsa.filters.hpfilter
            except Exception as e:
                raise ImportError("statsmodels is required for HP filter. Install via `pip install statsmodels`") from e

        elif method == "lowess":
            try:
                import statsmodels.api as sm
                lowess = sm.nonparametric.lowess
            except Exception as e:
                raise ImportError("statsmodels is required for LOWESS. Install via `pip install statsmodels`") from e

        elif method == "savgol":
            try:
                from scipy.signal import savgol_filter
            except Exception as e:
                raise ImportError("scipy is required for Savitzky–Golay. Install via `pip install scipy`") from e

            # ensure valid window
            n = len(df)
            if savgol_window > n:
                savgol_window = n if n % 2 == 1 else n - 1
            if savgol_window < (savgol_polyorder + 2):
                savgol_window = savgol_polyorder + 3
            if savgol_window % 2 == 0:
                savgol_window += 1

        # apply smoothing
        x = df[year_col].to_numpy()

        for col in value_cols:
            y = df[col].to_numpy(dtype=float)

            # if NaNs exist, fill softly (linear) so filters don't break
            if np.isnan(y).any():
                s = pd.Series(y).interpolate("linear", limit_direction="both").to_numpy()
            else:
                s = y

            if method == "hp":
                # returns (cycle, trend) — we use the trend component
                _, trend = hpfilter(s, lamb=hp_lambda)
                y_sm = trend

            elif method == "lowess":
                # return_sorted=False gives aligned array
                y_sm = lowess(s, x, frac=lowess_frac, it=1, return_sorted=False)

            elif method == "savgol":
                # Savitzky-Golay preserves shapes/peaks reasonably well
                y_sm = savgol_filter(s, window_length=savgol_window, polyorder=savgol_polyorder, mode="interp")

            elif method == "ma":
                # centered moving average with edge handling
                y_sm = pd.Series(s).rolling(ma_window, center=True, min_periods=1).mean().to_numpy()

            else:
                raise ValueError("Unknown method. Use 'hp', 'lowess', 'savgol', or 'ma'.")

            # clip to [0,1] if desired (fractions)
            if clip_01:
                y_sm = np.clip(y_sm, 0.0, 1.0)

            df[col] = y_sm

        # optionally renormalize rows so the fraction columns sum to 1
        if enforce_simplex and value_cols:
            row_sums = df[value_cols].sum(axis=1).replace(0, np.nan)
            scale = 1.0 / row_sums
            # only scale rows with positive sum; leave zero-sum rows as-is
            for col in value_cols:
                df.loc[row_sums.notna(), col] = df.loc[row_sums.notna(), col] * scale[row_sums.notna()].values
            # final safety clip
            if clip_01:
                df[value_cols] = df[value_cols].clip(lower=0.0, upper=1.0)

        # restore original row order
        df.index = order_idx
        return df

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
    

