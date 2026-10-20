"""
Session state: ensembles stored by id, so the technical tools chain without the agent copying data.

An ensemble is one set of futures (X values) with every policy evaluated on the same futures,
BAU included. vulnerability_analysis adds pass / fail labels to it; scenario_discovery and
trade_off_analysis read it.
"""

import itertools
from dataclasses import dataclass, field

import pandas as pd

from backend.rdm.tools.common import ToolError


@dataclass
class Ensemble:
    id: str
    futures: pd.DataFrame                 # one row per future: X_<id> in [0, 1]
    x_ranges: dict                        # x_id → (lo, hi) actually sampled
    policies: dict                        # name → {lever_id: level}; "BAU" is all levers at 0
    predictions: dict                     # name → DataFrame (futures × surrogate outputs)
    seed: int
    labels: dict = field(default_factory=dict)   # label_id → {"policy", "metric", …, "fail": Series}


class State:
    def __init__(self):
        self.ensembles: dict = {}
        self._ids = itertools.count(1)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}{next(self._ids)}"

    def add(self, ens: Ensemble) -> Ensemble:
        self.ensembles[ens.id] = ens
        return ens

    def get(self, ensemble_id: str) -> Ensemble:
        if ensemble_id not in self.ensembles:
            known = ", ".join(self.ensembles) or "none yet"
            raise ToolError("NO_ENSEMBLE", f"No ensemble {ensemble_id!r}; known: {known}. Run exploratory_modeling first.")
        return self.ensembles[ensemble_id]
