"""
The LHC design: the 0–1 value every lever (L) and uncertainty (X) group took in each run.

Joins ATTRIBUTE_PRIMARY (primary_id → design_id, future_id) with the LHC sample files on
(design_id, future_id). Columns are named ``L_<id>`` and ``X_<id>``; which ids exist comes
from the group definitions (``groups.py``).

Two things the join reports rather than hides:
  * runs whose (design_id, future_id) has no LHC row (in the 2026-05-30 run: future 0),
    which are left out of the design;
  * LHC columns with no group definition (in the 2026-05-30 run: 1682, 1707, 1725, 1734,
    1740), which are left out and listed by ``unmapped_lhc_columns``.
"""

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from backend.rdm.data.groups import lever_ids, uncertainty_ids
from backend.rdm.runs import Run

_KEYS = ["design_id", "future_id"]


@dataclass(frozen=True)
class DesignReport:
    n_runs_total: int
    n_runs_in_design: int
    runs_without_lhc: tuple      # primary_ids left out
    unmapped_lhc_columns: tuple  # LHC columns with no group definition


def _read_lhc(run: Run, file_name: str, ids: list, prefix: str) -> tuple:
    df = pd.read_csv(run.local(file_name))
    sample_cols = [c for c in df.columns if c not in ("region", *_KEYS)]
    wanted = [str(i) for i in ids]
    missing = [c for c in wanted if c not in sample_cols]
    if missing:
        raise ValueError(f"{file_name}: no LHC column for groups {missing} in run {run.name!r}")
    unmapped = tuple(c for c in sample_cols if c not in wanted)
    df = df[_KEYS + wanted].rename(columns={c: f"{prefix}_{c}" for c in wanted})
    return df, unmapped


@lru_cache(maxsize=2)
def _design(run: Run) -> tuple:
    primary = pd.read_csv(run.local("primary"))
    levers, unmapped_l = _read_lhc(run, "lhc_levers", lever_ids(run), "L")
    uncs, unmapped_x = _read_lhc(run, "lhc_uncertainties", uncertainty_ids(run), "X")

    df = (primary[["primary_id", *_KEYS]]
          .merge(levers, on=_KEYS, how="left")
          .merge(uncs, on=_KEYS, how="left"))
    value_cols = [c for c in df.columns if c[:2] in ("L_", "X_")]
    no_lhc = df[value_cols].isna().all(axis=1)

    design = df.loc[~no_lhc].set_index("primary_id").sort_index()
    if design[value_cols].isna().any().any():
        raise ValueError(f"Run {run.name!r}: some runs have only part of their L/X values")

    report = DesignReport(
        n_runs_total=len(df),
        n_runs_in_design=len(design),
        runs_without_lhc=tuple(int(i) for i in df.loc[no_lhc, "primary_id"]),
        unmapped_lhc_columns=unmapped_l + unmapped_x,
    )
    return design, report


def load_design(run: Run) -> pd.DataFrame:
    """Index primary_id; columns design_id, future_id, L_<id>…, X_<id>… (values in [0, 1])."""
    return _design(run)[0]


def design_report(run: Run) -> DesignReport:
    return _design(run)[1]


def lever_columns(run: Run) -> list:
    return [f"L_{i}" for i in lever_ids(run)]


def uncertainty_columns(run: Run) -> list:
    return [f"X_{i}" for i in uncertainty_ids(run)]
