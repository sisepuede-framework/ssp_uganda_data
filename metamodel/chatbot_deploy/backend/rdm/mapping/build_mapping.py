"""
Build the group → output mapping: which emissions and variables each lever (L) and
uncertainty (X) moves.

Two sources, kept side by side:

  structural  SISEPUEDE's own map: lever → transformation(s) → output fields it affects
              (levers only; joined on the transformation code without the run's
              _STRATEGY_NZ / _NZ suffix).
  empirical   the runs: Spearman correlation between the group's 0–1 value and the output,
              per anchor year, over a cached sample with every other L and X varying.
              The group "moves" the output when the largest |rho| across years reaches
              RHO_MOVES.

Emissions come from the run's ``emissions`` table (decomposed_emissions), variables from its
``variables`` table (model_output). Output values keep their original units.

Writes (paths from the run manifest):
  backend/rdm/mapping/maps/<run>.csv   one row per (group, output) linked by either source
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data import groups, lhc, sample
from backend.rdm.runs import Run

RHO_MOVES = 0.10          # |Spearman rho| at which a group counts as moving an output
MAPS_DIR = Path(__file__).parent / "maps"

_strip = lambda code: re.sub(r"(_STRATEGY_NZ|_NZ)$", "", code)


def group_names(run: Run) -> pd.DataFrame:
    reg = json.loads(run.registry.read_text())
    rows = [{"group_id": int(f["group_id"]), "group_kind": kind, "group_name": f["display_name"],
             "sector": f["sector"]}
            for kind, block in (("L", "lever_features"), ("X", "exogenous_features"))
            for f in reg[block].values()]
    return pd.DataFrame(rows)


def structural_links(run: Run, emission_fields: set, variable_fields: set) -> pd.DataFrame:
    """(group_id, output_field, output_label) from SISEPUEDE's transformation → output map."""
    smap = pd.read_csv(run.structural_map)
    smap["tx"] = smap.transformation_code.map(_strip)
    lev = groups.lever_groups(run)[["group_id", "transformation_code"]].drop_duplicates()
    lev["tx"] = lev.transformation_code.map(_strip)
    links = lev.merge(smap[["tx", "variable", "variable_field"]], on="tx")
    links = links.rename(columns={"variable_field": "output_field", "variable": "output_label"})
    links = links[links.output_field.isin(emission_fields | variable_fields)]
    return links[["group_id", "output_field", "output_label"]].drop_duplicates(["group_id", "output_field"])


def empirical_rho(run: Run, outputs: pd.DataFrame) -> pd.DataFrame:
    """Spearman rho of every group against every output, per year. Long: group, output, year, rho."""
    design = lhc.load_design(run)
    gcols = lhc.lever_columns(run) + lhc.uncertainty_columns(run)
    # Runs with a missing output (e.g. a NemoMod failure) are left out of the correlations.
    bad = outputs.isna().any(axis=1).groupby(level="primary_id").any()
    if bad.any():
        print(f"[mapping] {int(bad.sum())} runs with missing outputs left out of the empirical pass")
        outputs = outputs[~outputs.index.get_level_values("primary_id").isin(bad[bad].index)]
    frames = []
    for year, block in outputs.groupby(level="year"):
        block = block.droplevel("year")
        g = design.loc[block.index, gcols]
        gr = (g.rank() - g.rank().mean()) / g.rank().std(ddof=0)
        orank = block.rank()
        orank = orank.loc[:, orank.std(ddof=0) > 0]             # constant outputs carry no signal
        orr = (orank - orank.mean()) / orank.std(ddof=0)
        # numpy 2.2 on macOS (Accelerate) raises spurious matmul warnings even on random data;
        # the result is finite and equals np.einsum, so they are silenced here.
        with np.errstate(all="ignore"):
            rho = gr.T.to_numpy() @ orr.to_numpy() / len(block)
        df = pd.DataFrame(rho, index=[int(c[2:]) for c in gcols], columns=orank.columns)
        df = df.stack().rename("rho").reset_index()
        df.columns = ["group_id", "output_field", "rho"]
        df["year"] = year
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarise_rho(rho: pd.DataFrame, years: tuple) -> pd.DataFrame:
    """One row per (group, output): rho per year, the largest |rho|, its year and sign."""
    wide = rho.pivot_table(index=["group_id", "output_field"], columns="year", values="rho")
    wide = wide.reindex(columns=list(years))
    absmax_year = wide.abs().idxmax(axis=1)
    out = pd.DataFrame({
        "rho_max_abs": wide.abs().max(axis=1),
        "rho_year": absmax_year,
        "rho_sign": np.sign([wide.loc[i, y] for i, y in absmax_year.items()]).astype(int),
    }, index=wide.index)
    for y in years:
        out[f"rho_{y}"] = wide[y]
    return out.reset_index()


def build(run: Run, n: int = 5000, seed: int = 0) -> pd.DataFrame:
    emissions, variables = sample.load_sample(run, n, seed)
    kind_of = {**{c: "emission" for c in emissions.columns}, **{c: "variable" for c in variables.columns}}
    table_of = {"emission": run.table("emissions"), "variable": run.table("variables")}

    struct = structural_links(run, set(emissions.columns), set(variables.columns))
    struct["structural"] = True

    summary = summarise_rho(empirical_rho(run, emissions.join(variables)), run.years)
    summary["empirical"] = summary.rho_max_abs >= RHO_MOVES

    linked = summary[summary.empirical].merge(struct, on=["group_id", "output_field"], how="outer")
    linked = linked.drop(columns=[c for c in linked.columns if c.startswith("rho")])
    df = linked.merge(summary.drop(columns="empirical"), on=["group_id", "output_field"], how="left")
    df["structural"] = df.structural.astype("boolean").fillna(False).astype(bool)
    df["empirical"] = df.rho_max_abs.ge(RHO_MOVES).fillna(False)
    df["status"] = np.select(
        [df.structural & df.empirical, df.structural & df.rho_max_abs.isna(), df.structural],
        ["both", "structural, output constant in runs", "structural only"], "empirical only")
    df["output_kind"] = df.output_field.map(kind_of)
    df["source_table"] = df.output_kind.map(table_of)
    df["n_runs"] = int((~emissions.join(variables).isna().any(axis=1)
                        .groupby(level="primary_id").any()).sum())

    df = df.merge(group_names(run), on="group_id", how="left")
    cols = ["group_id", "group_kind", "group_name", "sector", "output_field", "output_label", "output_kind",
            "source_table", "structural", "empirical", "status", "rho_max_abs", "rho_year", "rho_sign",
            *[f"rho_{y}" for y in run.years], "n_runs"]
    return df[cols].sort_values(["group_id", "output_kind", "rho_max_abs"], ascending=[True, True, False],
                                ignore_index=True)


def write(run: Run, df: pd.DataFrame) -> Path:
    MAPS_DIR.mkdir(exist_ok=True)
    path = MAPS_DIR / f"{run.name}.csv"
    df.round(4).to_csv(path, index=False)
    return path


if __name__ == "__main__":
    from backend.rdm.runs import get_run

    r = get_run()
    m = build(r)
    p = write(r, m)
    print(f"{len(m)} links → {p}")
    print(m.groupby(["group_kind", "output_kind", "status"]).size().unstack(fill_value=0))
