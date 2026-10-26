"""
The XGBoost surrogate, batched: many futures per call, for the technical tools.

``services/predictor.py`` serves the deployed agent one scenario at a time; this module reads the
same pipeline through the run manifest and predicts whole ensembles. Inputs are a frame with
columns ``L_<id>`` and ``X_<id>`` (0–1, the LHC design's names); outputs are the surrogate's 258
targets plus derived totals, one row per future.

Derived metrics, per year (``<metric>_yr<year>``):
  emissions_total   sum of the 23 inventory categories            Mt CO₂e
  cost_total        sum of the 3 cost types: money spent > 0         billion USD
  benefit_total     sum of the 16 benefit types                     billion USD
  net_benefit       benefit_total − cost_total                      billion USD
  cost_pct_gdp      cost_total / GDP × 100                          %

Signs: every cost_* is money spent (> 0 = more spending); every benefit_* and net_benefit is good for the
country (> 0). Cost and benefit LEVELS are differences against one fixed reference run, so only their change
against BAU on the same futures is a policy effect; the tools report only that change (for cost_pct_gdp, in
percentage points of GDP). Audit: docs/archive/review_cost_signs.md.
"""

import json
import re
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from backend.rdm.runs import Run

UNITS = {"emission": "Mt CO₂e", "cost": "billion USD", "benefit": "billion USD", "gdp": "billion international $, PPP, constant prices",
         "net": "billion USD", "pct": "%"}
_TARGET = re.compile(r"^(emission|benefit|cost)_(.+)_yr(\d{4})$")


class Surrogate:
    def __init__(self, run: Run):
        self.run = run
        self.model = joblib.load(run.surrogate_path)
        self.features = [str(c) for c in self.model.feature_names_in_]
        reg = json.loads(run.registry.read_text())
        self.lever_ids = sorted(int(f["group_id"]) for f in reg["lever_features"].values())
        self.x_ids = sorted(int(f["group_id"]) for f in reg["exogenous_features"].values())
        column = {}
        for block, kind in (("lever_features", "L"), ("exogenous_features", "X")):
            for f in reg[block].values():
                column[f["training_column"]] = f"{kind}_{int(f['group_id'])}"
        missing = [c for c in self.features if c not in column]
        if missing:
            raise ValueError(f"Surrogate features with no registry group: {missing}")
        self._design_col = [column[c] for c in self.features]
        self.targets = json.loads(run.surrogate_targets.read_text())["target_columns"]
        self.years = sorted({int(m.group(3)) for t in self.targets if (m := _TARGET.match(t))})
        self.categories = sorted({m.group(2) for t in self.targets
                                  if (m := _TARGET.match(t)) and m.group(1) == "emission"})
        self.cost_types = sorted({m.group(2) for t in self.targets if (m := _TARGET.match(t)) and m.group(1) == "cost"})
        self.benefit_types = sorted({m.group(2) for t in self.targets
                                     if (m := _TARGET.match(t)) and m.group(1) == "benefit"})

    def predict(self, design: pd.DataFrame) -> pd.DataFrame:
        """One row per row of ``design`` (columns L_<id>, X_<id> in [0, 1]): 258 targets + derived."""
        absent = [c for c in self._design_col if c not in design.columns]
        if absent:
            raise KeyError(f"Design lacks columns {absent}")
        X = pd.DataFrame(design[self._design_col].to_numpy(dtype=float), columns=self.features)
        raw = self.model.predict(X)
        if raw.shape[1] != len(self.targets):
            raise ValueError(f"Surrogate returned {raw.shape[1]} outputs; target list has {len(self.targets)}")
        out = pd.DataFrame(raw, columns=self.targets, index=design.index)
        # SISEPUEDE's cost-benefit fields are signed "good for the country > 0" (docs/archive/review_cost_signs.md), so a
        # cost is negative there. Flip the cost types so that every cost_* reads "money spent > 0".
        cost_cols = [f"cost_{c}_yr{y}" for c in self.cost_types for y in self.years]
        out[cost_cols] = -out[cost_cols]
        derived = {}
        for y in self.years:
            emis = out[[f"emission_{c}_yr{y}" for c in self.categories]].sum(axis=1)
            cost = out[[f"cost_{c}_yr{y}" for c in self.cost_types]].sum(axis=1)
            ben = out[[f"benefit_{c}_yr{y}" for c in self.benefit_types]].sum(axis=1)
            gdp = out[f"gdp_mmm_usd_yr{y}"]
            derived[f"emissions_total_yr{y}"] = emis
            derived[f"cost_total_yr{y}"] = cost
            derived[f"benefit_total_yr{y}"] = ben
            derived[f"net_benefit_yr{y}"] = ben - cost
            derived[f"cost_pct_gdp_yr{y}"] = np.where(gdp > 0, 100 * cost / gdp, np.nan)
        return pd.concat([out, pd.DataFrame(derived, index=design.index)], axis=1)

    # ── metric names the tools accept ─────────────────────────────────────────
    def metrics(self) -> list:
        """Metric names without year: derived totals, emissions_<category>, cost_<type>, benefit_<type>."""
        return (["emissions_total", "cost_total", "benefit_total", "net_benefit", "cost_pct_gdp"]
                + [f"emissions_{c}" for c in self.categories]
                + [f"cost_{c}" for c in self.cost_types] + [f"benefit_{c}" for c in self.benefit_types])

    def column(self, metric: str, year: int) -> str:
        """Prediction column for a metric name and year; raises with the valid names otherwise."""
        if year not in self.years:
            raise ValueError(f"Year {year} not available; the surrogate reports {self.years}")
        if metric not in self.metrics():
            raise ValueError(f"Unknown metric {metric!r}. Valid: {', '.join(self.metrics())}")
        if metric.startswith("emissions_") and metric != "emissions_total":
            return f"emission_{metric[len('emissions_'):]}_yr{year}"
        return f"{metric}_yr{year}"

    @staticmethod
    def unit(metric: str) -> str:
        if metric.startswith("emissions"):
            return UNITS["emission"]
        if metric == "cost_pct_gdp":
            return UNITS["pct"]
        return "billion USD"


@lru_cache(maxsize=2)
def get_surrogate(run: Run) -> Surrogate:
    return Surrogate(run)
