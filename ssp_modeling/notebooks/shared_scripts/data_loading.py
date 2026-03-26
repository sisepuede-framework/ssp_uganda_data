"""
data_loading.py
---------------
Functions to load run outputs and enrich the strategy attribute table.
"""

import pandas as pd
from pathlib import Path
from typing import List, Tuple


def load_attribute_tables(
    run_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load ATTRIBUTE_PRIMARY.csv and ATTRIBUTE_STRATEGY.csv from *run_dir*.
    Returns (att_primary, att_strategy).
    """
    att_primary  = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")
    return att_primary, att_strategy


def parse_strategy_metadata(att_strategy: pd.DataFrame) -> pd.DataFrame:
    """
    Derive sector, transformation_code, transformation_name, and
    transformation_name_sector columns from strategy_code / strategy text.

    strategy_code patterns:
      Singleton  : "TORNADO_BASE:TX:AGRC:DEC_CH4_RICE_STRATEGY_NZ"
      WHIRLPOOL  : "WHIRLPOOL_PFLO_HBLE:TX:AGRC:DEC_CH4_RICE_STRATEGY_NZ"
      Composite  : "AF:ALL"
      BASE       : "BASE"
    """
    df = att_strategy.copy()

    df['sector'] = (
        df['strategy_code']
        .str.extract(r'(?:[A-Z0-9_]+:TX:)?([A-Z]+):[A-Z0-9_]+$', expand=False)
    )

    df['transformation_code'] = (
        df['strategy_code']
        .str.extract(r':([A-Z0-9_]+)$', expand=False)
        .str.replace(r'_STRATEGY_NZ$', '', regex=True)
    )

    df['transformation_name'] = (
        df['strategy']
        .str.extract(r'-\s*[A-Z]+:\s*(.+)$', expand=False)
    )

    df['transformation_name_sector'] = (
        df['sector'].fillna('') + ': ' + df['transformation_name'].fillna('')
    ).where(df['transformation_name'].notna())

    return df


def load_wide_export(
    run_dir: Path,
    primary_ids_filter: List[int],
) -> pd.DataFrame:
    """
    Glob for the wide-format CSV in *run_dir*, load it and filter to the
    requested primary_ids.  The file is identified by the fixed UUID suffix.
    """
    pattern = "*c585e7e9-e32f-4131-999b-ee7fc5ec014e.csv"
    matches = list(run_dir.glob(pattern))
    assert matches, f"No wide-format CSV ({pattern}) found in {run_dir}"

    df = pd.read_csv(matches[0])
    df = df[df["primary_id"].isin(primary_ids_filter)].reset_index(drop=True)
    return df
