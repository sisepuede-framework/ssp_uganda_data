"""
features.py
-----------
Build the model FEATURES (the `group_*` columns) keyed by primary_id.

Features are NOT pulled via Athena: they live as a handful of flat CSVs under
transfers/<run>/ (one file per prefix, so they don't fit the partitioned-table
model cleanly), and the final step is a column *rename* that is pure pandas. So
we download those CSVs once and reproduce the exact logic from
data_prep_sector.ipynb:

  1. Load the LHC samples (X = exogenous uncertainties, L = lever effects),
     suffix their columns `_X` / `_L`, and merge on [region, design_id, future_id].
  2. Bridge to primary_id via ATTRIBUTE_PRIMARY (join on [design_id, future_id]).
  3. Keep only the trajectory groups that actually vary (VARIABLE_TRAJECTORY_GROUPS_*).
  4. Rename each group column to `group_<id>_<common-prefix-of-its-variables>`.

Returns a DataFrame: [future_id, primary_id, group_*...].
"""

import os

import pandas as pd

# Files we need from transfers/<run>/ (everything else, incl. the huge
# transformations/ dir, is skipped to save bandwidth).
TRANSFER_FILES = [
    "ATTRIBUTE_LHC_SAMPLES_EXOGENOUS_UNCERTAINTIES.csv",
    "ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv",
    "ATTRIBUTE_PRIMARY.csv",
    "ATTRIBUTE_STRATEGY.csv",
    "VARIABLE_TRAJECTORY_GROUPS_X.csv",
    "VARIABLE_TRAJECTORY_GROUPS_L.csv",
]


def download_transfer_files(session, cfg) -> None:
    """Download the 5 needed transfers CSVs into cfg.ssp_dir (skip if present)."""
    os.makedirs(cfg.ssp_dir, exist_ok=True)
    s3 = session.client("s3")
    for name in TRANSFER_FILES:
        dest = os.path.join(cfg.ssp_dir, name)
        if os.path.exists(dest):
            print(f"  have {name}")
            continue
        key = f"{cfg.transfers_prefix}{name}"
        print(f"  downloading {name} ...")
        s3.download_file(cfg.bucket, key, dest)


def _process_variable_prefix(df, var_col="variable", group_col="variable_trajectory_group_w_suffix"):
    """For each trajectory group, the column label is `group_<id>_<prefix>` where
    <prefix> is the common prefix of all variable names in the group."""
    result = []
    for group, group_df in df.groupby(group_col):
        variables = group_df[var_col].tolist()
        prefix = variables[0] if len(variables) == 1 else os.path.commonprefix(variables).rstrip("_")
        result.append({"variable_trajectory_group_w_suffix": group, "variable_prefix": f"group_{group}_{prefix}"})
    return pd.DataFrame(result)


def build_features(session, cfg) -> pd.DataFrame:
    download_transfer_files(session, cfg)
    d = cfg.ssp_dir

    # 1. LHC samples -> suffixed + merged on the shared index keys.
    lhs_x = pd.read_csv(os.path.join(d, "ATTRIBUTE_LHC_SAMPLES_EXOGENOUS_UNCERTAINTIES.csv")).add_suffix("_X")
    lhs_x = lhs_x.rename(columns={"region_X": "region", "design_id_X": "design_id", "future_id_X": "future_id"})
    lhs_l = pd.read_csv(os.path.join(d, "ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv")).add_suffix("_L")
    lhs_l = lhs_l.rename(columns={"region_L": "region", "design_id_L": "design_id", "future_id_L": "future_id"})
    lhs = pd.merge(lhs_x, lhs_l, on=["region", "design_id", "future_id"], how="inner")

    # 2. Bridge LHC space (design_id, future_id) -> primary_id.
    attr_primary = pd.read_csv(os.path.join(d, "ATTRIBUTE_PRIMARY.csv"))
    lhs = pd.merge(lhs, attr_primary, on=["design_id", "future_id"], how="inner")
    lhs = lhs.drop(columns=[c for c in ["region", "design_id", "strategy_id"] if c in lhs.columns])
    front = ["future_id", "primary_id"]
    lhs = lhs[front + [c for c in lhs.columns if c not in front]]

    # 3. Which trajectory groups to keep (the ones that vary in this run).
    vt_x = pd.read_csv(os.path.join(d, "VARIABLE_TRAJECTORY_GROUPS_X.csv"))
    vt_l = pd.read_csv(os.path.join(d, "VARIABLE_TRAJECTORY_GROUPS_L.csv"))
    vt_x["variable_trajectory_group_w_suffix"] = vt_x["variable_trajectory_group"].astype(str) + "_X"
    vt_l["variable_trajectory_group_w_suffix"] = vt_l["variable_trajectory_group"].astype(str) + "_L"
    groups_all = set(vt_x["variable_trajectory_group_w_suffix"]) | set(vt_l["variable_trajectory_group_w_suffix"])
    relevant = [c for c in lhs.columns if c in groups_all]
    lhs = lhs[front + relevant]

    # 4. Rename group columns to readable `group_<id>_<prefix>` labels.
    cols = ["variable", "variable_trajectory_group_w_suffix"]
    vt_all = pd.concat([vt_x[cols], vt_l[cols]], ignore_index=True)
    vt_all = vt_all[vt_all["variable_trajectory_group_w_suffix"].isin(relevant)]
    prefix_df = _process_variable_prefix(vt_all)
    group_to_prefix = dict(zip(prefix_df["variable_trajectory_group_w_suffix"], prefix_df["variable_prefix"]))
    lhs = lhs.rename(columns={c: group_to_prefix[c] for c in lhs.columns if c in group_to_prefix})

    dup = lhs.columns[lhs.columns.duplicated()].tolist()
    if dup:
        raise ValueError(f"Duplicate feature column names after rename: {dup}")
    print(f"  features: {lhs.shape[0]} rows x {lhs.shape[1] - 2} group_* columns")
    return lhs
