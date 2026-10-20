"""
The run-level store: every run's L and X values joined to its emissions and variables, and the
(L_i, X_j) summaries the knowledge tools return.

Backed today by the cached sample (``sample.py``); the full store will be written in the same
format (Parquet indexed by primary_id and year, one file per role), so switching is a change of
``source`` and nothing else. Values keep their original units; only L and X are 0–1.
"""

from functools import cached_property

import numpy as np
import pandas as pd

from backend.rdm.data import lhc, sample
from backend.rdm.runs import Run

QUANTILES = {"p10": 0.10, "median": 0.50, "p90": 0.90}

# SISEPUEDE writes 1e10 as a fill value. In a few fields it is the model's convention in almost
# every run (e.g. NemoMod storage capacity = "unbounded"); elsewhere it marks a broken run
# (2026-05-30 run: 9 sampled runs in one id block have every light-duty vkm-by-fuel field at
# 1e10). A field's 1e10 values count as missing when they occur in fewer than RARE_SHARE of runs.
SENTINEL = 1e10
RARE_SHARE = 0.05


def clean_sentinels(frame: pd.DataFrame) -> tuple:
    """Set rare 1e10 fill values to NaN. Returns (clean frame, {field: [primary_ids]})."""
    hits = (frame == SENTINEL).groupby(level="primary_id").any()
    n_runs = len(hits)
    rare = [c for c in hits.columns if 0 < hits[c].sum() < RARE_SHARE * n_runs]
    report = {c: sorted(int(i) for i in hits.index[hits[c]]) for c in rare}
    if rare:
        frame = frame.copy()
        frame[rare] = frame[rare].mask(frame[rare] == SENTINEL)
    return frame, report


def bin_edges(n_bins: int) -> np.ndarray:
    return np.linspace(0.0, 1.0, n_bins + 1)


def _bin(values: pd.Series, n_bins: int) -> pd.Series:
    """Equal-width bins over [0, 1]; returns the bin index 0 … n_bins-1."""
    return np.minimum((values.to_numpy() * n_bins).astype(int), n_bins - 1)


class Store:
    def __init__(self, run: Run, source: str = "sample", n: int = 5000, seed: int = 0):
        if source != "sample":
            raise NotImplementedError("Only the cached sample exists so far (build plan step 0.4)")
        self.run = run
        self.source = source
        emissions, variables = sample.load_sample(run, n, seed)
        _, rep_e = clean_sentinels(emissions)
        _, rep_v = clean_sentinels(variables)
        self.fill_values_removed = {**rep_e, **rep_v}     # field → runs with a rare 1e10 fill value
        # A run with a rare fill value is broken as a whole, not only in that field (2026-05-30 run: the same 9
        # runs also have light-duty vehicle-km ≈ 1 instead of billions), so those runs are dropped entirely.
        self.broken_runs = sorted({i for ids in self.fill_values_removed.values() for i in ids})
        keep = lambda f: f[~f.index.get_level_values("primary_id").isin(self.broken_runs)]
        self._emissions, self._variables = keep(emissions), keep(variables)
        self.design = lhc.load_design(run).drop(index=self.broken_runs, errors="ignore")

    # ── catalogue of fields ───────────────────────────────────────────────────
    @cached_property
    def emission_fields(self) -> list:
        return list(self._emissions.columns)

    @cached_property
    def variable_fields(self) -> list:
        return list(self._variables.columns)

    def kind(self, field: str) -> str:
        if field in self._emissions.columns:
            return "emission"
        if field in self._variables.columns:
            return "variable"
        raise KeyError(f"{field!r} is neither an emission nor a variable in run {self.run.name!r}")

    # ── raw values ───────────────────────────────────────────────────────────
    def values(self, field: str, year: int) -> pd.Series:
        """One output in original units, indexed by primary_id; runs where it is missing are dropped."""
        if year not in self.run.years:
            raise ValueError(f"Year {year} not available; anchor years are {self.run.years}")
        frame = self._emissions if self.kind(field) == "emission" else self._variables
        return frame.xs(year, level="year")[field].dropna()

    def total(self, fields: list, year: int) -> pd.Series:
        """Sum of several emission fields (e.g. one inventory category), indexed by primary_id.
        A field missing in a run counts as 0; a run missing every field is dropped."""
        if year not in self.run.years:
            raise ValueError(f"Year {year} not available; anchor years are {self.run.years}")
        unknown = [f for f in fields if f not in self._emissions.columns]
        if unknown:
            raise KeyError(f"Not emission fields in run {self.run.name!r}: {unknown[:5]}")
        return self._emissions.xs(year, level="year")[list(fields)].sum(axis=1, min_count=1).dropna()

    def with_groups(self, field: str, year: int, group_ids: list) -> pd.DataFrame:
        """The output next to the 0–1 values of the given groups, one row per run."""
        cols = [f"{'L' if f'L_{g}' in self.design.columns else 'X'}_{g}" for g in group_ids]
        missing = [c for c in cols if c not in self.design.columns]
        if missing:
            raise KeyError(f"Unknown groups {missing}")
        y = self.values(field, year).rename("value")
        return self.design.loc[y.index, cols].join(y)

    # ── summaries the tools return ───────────────────────────────────────────
    @staticmethod
    def _summarise(df: pd.DataFrame, by: list) -> pd.DataFrame:
        g = df.groupby(by)["value"]
        out = g.size().rename("n").to_frame()
        for name, q in QUANTILES.items():
            out[name] = g.quantile(q)
        return out.reset_index()

    def curve(self, group_id: int, field: str, year: int, n_bins: int = 5) -> pd.DataFrame:
        """How the output responds across one group's range, every other input varying."""
        df = self.with_groups(field, year, [group_id])
        col = df.columns[0]
        df["bin"] = _bin(df[col], n_bins)
        out = self._summarise(df, ["bin"])
        edges = bin_edges(n_bins)
        out.insert(1, "from", edges[out.bin])
        out.insert(2, "to", edges[out.bin + 1])
        return out.drop(columns="bin")

    def pair(self, lever_id: int, x_id: int, field: str, year: int, n_bins: int = 5) -> pd.DataFrame:
        """The (L_i, X_j) object for one output: summary per cell of the L × X grid."""
        df = self.with_groups(field, year, [lever_id, x_id])
        lcol, xcol = df.columns[:2]
        df["L_bin"], df["X_bin"] = _bin(df[lcol], n_bins), _bin(df[xcol], n_bins)
        out = self._summarise(df, ["L_bin", "X_bin"])
        edges = bin_edges(n_bins)
        out.insert(0, "L_from", edges[out.L_bin])
        out.insert(1, "L_to", edges[out.L_bin + 1])
        out.insert(2, "X_from", edges[out.X_bin])
        out.insert(3, "X_to", edges[out.X_bin + 1])
        return out.drop(columns=["L_bin", "X_bin"])
