"""Shared helpers for the RDM tools: group names, rounding, and the error the agent sees."""

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from backend.rdm.runs import Run


class ToolError(ValueError):
    """A request the tool refuses (bad id, missing argument, broken rule). The message goes to the agent; the code
    goes to the log only, so failure modes can be counted (e.g. X_AS_LEVER, X_FIXED, LEVEL_OUT_OF_RANGE)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@lru_cache(maxsize=4)
def groups(run: Run) -> dict:
    """group_id → {"kind": "L"|"X", "name", "sector"} from the registry."""
    reg = json.loads(run.registry.read_text())
    out = {}
    for block, kind in (("lever_features", "L"), ("exogenous_features", "X")):
        for f in reg[block].values():
            out[int(f["group_id"])] = {"kind": kind, "name": f["display_name"], "sector": f["sector"]}
    return out


def group_id(run: Run, value, kind: str) -> int:
    """Validate a lever (kind "L") or uncertainty (kind "X") id given by the agent ("25", 25 or "L25")."""
    if isinstance(value, str) and value.strip()[:1].upper() in ("L", "X") and value.strip()[1:].strip().isdigit():
        value = value.strip()[1:]
    try:
        gid = int(value)
    except (TypeError, ValueError):
        raise ToolError("BAD_ID", f"{value!r} is not a group id; use the numeric id from the catalogue")
    g = groups(run).get(gid)
    if g is None or g["kind"] != kind:
        what = "lever" if kind == "L" else "uncertainty"
        valid = sorted(i for i, v in groups(run).items() if v["kind"] == kind)
        code = "BAD_ID" if g is None else "X_AS_LEVER" if kind == "L" else "LEVER_AS_X"
        raise ToolError(code, f"{gid} is not a {what} id; valid {what} ids: {valid[0]}–{valid[-1]}")
    return gid


def num(x, nd: int = 3):
    """JSON-safe rounded float (None for NaN)."""
    if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x):
        return None
    return round(float(x), nd)


def spread(s: pd.Series, nd: int = 3) -> dict:
    s = pd.Series(s).dropna()
    if s.empty:
        return {"median": None, "p10": None, "p90": None}
    return {"median": num(s.median(), nd), "p10": num(s.quantile(0.10), nd), "p90": num(s.quantile(0.90), nd)}
