"""
Tornado process: merge emissions + CBA, compute marginal abatement cost, write tornado_plot.csv.

Country-agnostic. Run from project root or pass paths.

Usage:
  python ssp_modeling/cb/tornado_plot/scr/process_tornado.py \\
    --country uganda \\
    --input-dir ssp_modeling/cb/tornado_plot/data/input/tornado \\
    --output-dir ssp_modeling/cb/tornado_plot/data/output/tornado \\
    [--emissions-year 2019]
"""

import argparse
import pathlib
import numpy as np
import pandas as pd


MAC_COL = "marginal_total_abatement_cost_(USD/tCO2e)"


def add_sector_and_transformation_fields_tornado(
    df: pd.DataFrame, strategy_col: str = "strategy"
) -> pd.DataFrame:
    """Tornado-style: sector from '- XXX:' pattern, transformation_name after ':'."""
    df = df.copy()
    df["sector"] = df[strategy_col].str.extract(r"-\s*([A-Z]{3,6})\s*:", expand=False)
    df.loc[
        df[strategy_col].str.contains(r"^Strategy\s+TX:BASE", regex=True, na=False),
        "sector",
    ] = "BASE"
    df["transformation_name"] = df[strategy_col].str.extract(r":\s*(.*)$", expand=False)
    base_mask = df[strategy_col].str.contains(r"^Strategy\s+TX:BASE", regex=True, na=False)
    df.loc[base_mask, "transformation_name"] = "BASE"
    df["transformation_name"] = df["transformation_name"].fillna("").str.strip()
    return df


def run(
    input_dir: pathlib.Path,
    output_dir: pathlib.Path,
    country: str,
    emissions_year: int = 2019,
) -> None:
    input_dir = pathlib.Path(input_dir).resolve()
    output_dir = pathlib.Path(output_dir).resolve()

    emissions_file = input_dir / f"raw_emissions_{country}_{emissions_year}_tornado_data_raw.csv"
    cba_file = input_dir / f"cba_results_ssp_modeling_tornado_{country}.csv"
    att_strategy_file = input_dir / "ATTRIBUTE_STRATEGY.csv"

    for f in (emissions_file, cba_file, att_strategy_file):
        if not f.exists():
            raise FileNotFoundError(f"Required input not found: {f}")

    # Load emissions, drop Historical
    emissions_df = pd.read_csv(emissions_file)
    emissions_df = emissions_df.loc[~emissions_df["strategy"].isin(["Historical"])].copy()
    tornado_emissions_df = emissions_df

    # Aggregate by strategy_id, primary_id, strategy
    tornado_emissions_agg_df = (
        tornado_emissions_df.groupby(["strategy_id", "primary_id", "strategy"])["value"]
        .sum()
        .reset_index()
    )
    tornado_emissions_agg_df = tornado_emissions_agg_df.rename(columns={"value": "emission_total"})

    base_emission_total = tornado_emissions_agg_df.loc[
        tornado_emissions_agg_df["strategy_id"] == 0, "emission_total"
    ].values[0]
    tornado_emissions_agg_df["base_emission_total"] = base_emission_total
    tornado_emissions_agg_df["emission_diff"] = (
        tornado_emissions_agg_df["emission_total"] - tornado_emissions_agg_df["base_emission_total"]
    )

    tornado_emissions_agg_extended_df = add_sector_and_transformation_fields_tornado(
        tornado_emissions_agg_df
    )

    # Load CBA
    cb_raw_df = pd.read_csv(cba_file)
    cb_data = cb_raw_df.copy()
    cb_chars = cb_data["variable"].astype(str).str.split(":", n=4, expand=True)
    cb_chars.columns = ["name", "sector", "cb_type", "item_1", "item_2"]
    cb_data = pd.concat([cb_data, cb_chars], axis=1)
    cb_data["Year"] = cb_data["time_period"] + 2015

    attribute_strategy_df = pd.read_csv(att_strategy_file)
    cb_data = cb_data.merge(attribute_strategy_df, on="strategy_code", how="left")

    cb_data = (
        cb_data.groupby(["strategy_id", "cb_type"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "cumulative"})
    )
    wide_cb = (
        cb_data.pivot(index="strategy_id", columns="cb_type", values="cumulative")
        .reset_index()
    )
    wide_cb.columns.name = None

    df_merged = pd.merge(
        tornado_emissions_agg_extended_df,
        wide_cb,
        on="strategy_id",
        how="inner",
    )

    df_merged["technical_cost"] = df_merged["technical_cost"] * -1
    df_merged[MAC_COL] = (df_merged["technical_cost"] / df_merged["emission_diff"]) * 1000
    df_merged[MAC_COL] = df_merged[MAC_COL].abs() * np.sign(df_merged["technical_cost"])

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "tornado_plot.csv"
    df_merged.to_csv(out_path, index=False)
    print(f"[tornado] Results saved to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tornado process: emissions + CBA -> tornado_plot.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--country", type=str, default="uganda", help="Country code for file names.")
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Path to input folder (contains emissions CSV, CBA CSV, ATTRIBUTE_STRATEGY.csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Path to output folder (tornado_plot.csv will be written here).",
    )
    parser.add_argument(
        "--emissions-year",
        type=int,
        default=2019,
        help="Year used in emissions filename (default: 2019).",
    )
    args = parser.parse_args()
    run(
        input_dir=pathlib.Path(args.input_dir),
        output_dir=pathlib.Path(args.output_dir),
        country=args.country,
        emissions_year=args.emissions_year,
    )


if __name__ == "__main__":
    main()
