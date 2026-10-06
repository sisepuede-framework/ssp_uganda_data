"""
Group definitions: which input variables each lever (L) and uncertainty (X) group sets.

Read from the run's VARIABLE_TRAJECTORY_GROUPS_L / _X files, so group ids and their
variables always come from the run, never from code.
"""

from functools import lru_cache

import pandas as pd

from backend.rdm.runs import Run


@lru_cache(maxsize=4)
def lever_groups(run: Run) -> pd.DataFrame:
    """One row per (lever group, input variable): group_id, transformation_code, variable, variable_field."""
    df = pd.read_csv(run.local("groups_l"))
    return (df.rename(columns={"variable_trajectory_group": "group_id"})
              [["group_id", "transformation_code", "variable", "variable_field"]]
              .sort_values(["group_id", "variable_field"], ignore_index=True))


@lru_cache(maxsize=4)
def uncertainty_groups(run: Run) -> pd.DataFrame:
    """One row per (uncertainty group, input variable): group_id, variable_field."""
    df = pd.read_csv(run.local("groups_x"))
    return (df.rename(columns={"variable_trajectory_group": "group_id", "variable": "variable_field"})
              [["group_id", "variable_field"]]
              .sort_values(["group_id", "variable_field"], ignore_index=True))


def lever_ids(run: Run) -> list:
    return sorted(int(g) for g in lever_groups(run).group_id.unique())


def uncertainty_ids(run: Run) -> list:
    return sorted(int(g) for g in uncertainty_groups(run).group_id.unique())


def group_kind(run: Run, group_id: int) -> str:
    """'L' for a lever group, 'X' for an uncertainty group."""
    if group_id in lever_ids(run):
        return "L"
    if group_id in uncertainty_ids(run):
        return "X"
    raise KeyError(f"Group {group_id} is neither a lever nor an uncertainty in run {run.name!r}")


def input_variables(run: Run, group_id: int) -> list:
    """Input variable fields a group sets."""
    df = lever_groups(run) if group_kind(run, group_id) == "L" else uncertainty_groups(run)
    return df.loc[df.group_id == group_id, "variable_field"].tolist()


def transformations(run: Run, lever_id: int) -> list:
    """SISEPUEDE transformation codes bundled in a lever group (one, except e.g. lever 15)."""
    df = lever_groups(run)
    return sorted(df.loc[df.group_id == lever_id, "transformation_code"].unique())
