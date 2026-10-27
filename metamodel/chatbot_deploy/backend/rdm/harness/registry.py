"""
The six tools as the agent sees them, and the harness that runs them.

Schemas and descriptions are identical in v0 and v1; only what the run-based information
tool returns differs (``Harness(version=…)``). The agent decides which tool to call; the harness
never does. It keeps the state, checks the rules in code (inside each tool), and logs every call:
tool, arguments, status, duration, size and the full reply — the final actions the experiment
measures.
"""

import json
import time
from pathlib import Path

from backend.rdm.data.store import Store
from backend.rdm.harness.state import State
from backend.rdm.runs import Run, get_run
from backend.rdm.surrogate import get_surrogate
from backend.rdm.tools import information, technical
from backend.rdm.tools.common import ToolError
from backend.rdm.tools.context import TOPICS, country_context

_POLICIES = {
    "type": "array",
    "description": "Policies to test. Each: {name, levers: {lever_id: level}}, each level within the range the "
                   "system prompt gives for that lever. Levers left out stay at 0 "
                   "(BAU). BAU itself is added automatically on the same futures.",
    "items": {"type": "object",
              "properties": {"name": {"type": "string"},
                             "levers": {"type": "object", "additionalProperties": {"type": "number"}}},
              "required": ["name", "levers"]},
}

TOOLS = [
    {"name": "exploratory_modeling",
     "description": "RDM step 1 — explore and stress-test. Runs one or more policies across many futures (all 13 "
                    "uncertainties sampled; optionally restricted to a range) on the surrogate, with BAU on the same "
                    "futures. Returns, per policy, metric and year: median and p10–p90, and the change vs BAU. "
                    "Returns an ensemble_id for the other technical tools. Use it to evaluate policies, and again "
                    "after revising a policy. To compare alternatives, run them in one call, then use "
                    "trade_off_analysis on its ensemble. Do not use it to learn what a lever moves (use "
                    "model_network).",
     "input_schema": {"type": "object", "properties": {
         "policies": _POLICIES,
         "x_ranges": {"type": "object", "description": "Optional: {uncertainty_id: [low, high]} within 0–1 to restrict "
                      "an uncertainty (e.g. [0.2, 0.6]). Never a single value.",
                      "additionalProperties": {"type": "array", "items": {"type": "number"}}},
         "n_futures": {"type": "integer", "description": "Number of futures (default 500, 50–5000)."},
         "metrics": {"type": "array", "items": {"type": "string"},
                     "description": "Default [emissions_total, cost_total]. Also emissions_<category>, cost_<type>, "
                                    "benefit_<type>, benefit_total, net_benefit, cost_pct_gdp. Costs and benefits "
                                    "are reported only as changes vs BAU."},
         "years": {"type": "array", "items": {"type": "integer"}, "description": "Default all: 2025–2070."}},
         "required": ["policies"]}},
    {"name": "vulnerability_analysis",
     "description": "RDM step 2 — vulnerability. Labels each future of an ensemble pass or fail for one policy "
                    "against a threshold, and reports how often it fails. If no threshold is given it returns "
                    "status needs_threshold with the distribution: ask the user which value counts as failure, "
                    "then call again. Do not invent the threshold.",
     "input_schema": {"type": "object", "properties": {
         "ensemble_id": {"type": "string"}, "policy": {"type": "string"},
         "metric": {"type": "string", "description": "e.g. emissions_total, emissions_transportation, cost_total"},
         "year": {"type": "integer"},
         "threshold": {"type": "number", "description": "The user's failure threshold: in the metric's unit, in % "
                                                         "reduction vs BAU, or as a change vs BAU (see threshold_type)."},
         "threshold_type": {"type": "string", "enum": ["absolute", "reduction_vs_bau_pct", "change_vs_bau"],
                            "description": "Default: absolute for emissions; change_vs_bau for costs and benefits "
                                           "(the only type they accept)."},
         "pass_if": {"type": "string", "enum": ["above", "below"],
                     "description": "Default: below for emissions and costs (money spent), above for reductions, "
                                    "benefits and net benefit."}},
         "required": ["ensemble_id", "policy", "metric", "year"]}},
    {"name": "scenario_discovery",
     "description": "RDM step 2 — scenario discovery. After vulnerability_analysis: finds the two uncertainties that "
                    "best explain when the policy fails, the conditions (boxes) where failures concentrate, and a "
                    "pass-rate map over the pair. These are decision-relevant scenarios, not predictions.",
     "input_schema": {"type": "object", "properties": {
         "ensemble_id": {"type": "string"},
         "label_id": {"type": "string", "description": "From vulnerability_analysis; default the latest."},
         "pair": {"type": "array", "items": {"type": "integer"}, "description": "Optional: two uncertainty ids to show."}},
         "required": ["ensemble_id"]}},
    {"name": "trade_off_analysis",
     "description": "RDM step 3 — trade-offs. Use it whenever the user compares two or more alternatives. "
                    "Compares the policies of an ensemble on emissions vs costs in the same futures: change vs BAU, cost per tonne abated, how often one has lower emissions, lower cost or "
                    "both, and which are dominated. Describe trade-offs; do not name a best policy.",
     "input_schema": {"type": "object", "properties": {
         "ensemble_id": {"type": "string"}, "year": {"type": "integer"},
         "policies": {"type": "array", "items": {"type": "string"}}},
         "required": ["ensemble_id"]}},
    {"name": "model_network",
     "description": "Information. Navigate the SISEPUEDE model as a network, read from the model code: levers and "
                    "uncertainties set input variables; in-between variables are computed from them; emission "
                    "variables are computed from those; emissions sum into the 23 inventory categories the technical "
                    "tools report. A link means \"used to compute\". Give one node and get it, its attributes (unit, "
                    "sector, gas, category), what it is computed from (one step back) and what it is used to compute "
                    "(one step forward). Any name in a reply can be the next node, so walk the network step by step: "
                    "from a lever forward to see what its level means and what it changes, down to the categories; "
                    "from a category or variable back to find the levers and uncertainties that reach it (candidates "
                    "for a target, then test them with exploratory_modeling). The electricity system (NemoMod) is one "
                    "box. Do not use it to evaluate a policy across futures (use exploratory_modeling).",
     "input_schema": {"type": "object", "properties": {
         "node": {"type": "string", "description": "A lever (\"L35\"), an uncertainty (\"X57\"), a category metric "
                                                   "(\"emissions_transportation\"), a variable name as listed in a "
                                                   "reply, or one of its fields."},
         "year": {"type": "integer", "description": "2025, 2035, 2040, 2050, 2060 or 2070"},
         "lever": {"type": "integer", "description": "Optional: look at the node by this lever's level (low, middle "
                                                     "or high third of its range)."},
         "uncertainty": {"type": "integer", "description": "Optional, with third: look at the node only in futures "
                                                           "where this uncertainty is in that third of its range."},
         "third": {"type": "string", "enum": ["low", "mid", "high"],
                   "description": "With uncertainty: low = 0–⅓, mid = ⅓–⅔, high = ⅔–1 of its range. "
                                  "A lever is always shown for all three of its thirds."}},
         "required": ["node", "year"]}},
    {"name": "country_context",
     "description": "Uganda's modelled baseline (2025–2050) for one topic. Modelling assumptions, not present-day "
                    "statistics.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "enum": list(TOPICS)}},
                      "required": ["topic"]}},
]
TOOL_NAMES = [t["name"] for t in TOOLS]


def _ids(d: dict) -> dict:
    out = {}
    for k, v in (d or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[str(k)] = v
    return out


def _params(name: str, a: dict, result: dict) -> dict:
    """The arguments that matter for the failure-mode checks, in one shape whatever the agent wrote."""
    if name == "exploratory_modeling":
        return {"policies": {str(p.get("name")): _ids(p.get("levers")) for p in (a.get("policies") or [])
                             if isinstance(p, dict)},
                "x_ranges": _ids(a.get("x_ranges")), "metrics": a.get("metrics"),
                "ensemble_created": result.get("ensemble_id")}
    if name == "vulnerability_analysis":
        return {"ensemble": a.get("ensemble_id"), "policy": a.get("policy"), "metric": a.get("metric"),
                "year": a.get("year"), "threshold": a.get("threshold"), "threshold_type": a.get("threshold_type"),
                "asked_for_threshold": result.get("status") == "needs_threshold"}
    if name in ("scenario_discovery", "trade_off_analysis"):
        return {"ensemble": a.get("ensemble_id"), "policies": a.get("policies")}
    if name == "model_network":
        return {"node": a.get("node"), "year": a.get("year"), "lever": a.get("lever"),
                "uncertainty": a.get("uncertainty"), "third": a.get("third"), "node_kind": result.get("kind")}
    return dict(a)


class Harness:
    def __init__(self, version: str = "v1", run: Run | None = None, log_path: Path | None = None):
        if version not in information.VERSIONS:
            raise ValueError(f"version must be one of {information.VERSIONS}")
        self.version = version
        self.run = run or get_run()
        self.state = State()
        self.log: list = []
        self.log_path = log_path
        self.user_turn = 0          # set by the agent loop: how many user messages came before this call
        self._sur = self._store = None

    @property
    def surrogate(self):
        if self._sur is None:
            self._sur = get_surrogate(self.run)
        return self._sur

    @property
    def store(self):
        if self._store is None:
            self._store = Store(self.run)
        return self._store

    def _dispatch(self, name: str, a: dict):
        if name == "exploratory_modeling":
            return technical.exploratory_modeling(self.state, self.surrogate, a.get("policies"), a.get("x_ranges"),
                                                  a.get("n_futures", technical.DEFAULT_FUTURES), 0,
                                                  a.get("metrics"), a.get("years"))
        if name == "vulnerability_analysis":
            return technical.vulnerability_analysis(self.state, self.surrogate, a["ensemble_id"], a["policy"],
                                                    a["metric"], a["year"], a.get("threshold"),
                                                    a.get("threshold_type"), a.get("pass_if"))
        if name == "scenario_discovery":
            return technical.scenario_discovery(self.state, self.surrogate, a["ensemble_id"], a.get("label_id"),
                                                a.get("pair"))
        if name == "trade_off_analysis":
            return technical.trade_off_analysis(self.state, self.surrogate, a["ensemble_id"], a.get("year", 2050),
                                                a.get("policies"))
        if name == "model_network":
            return information.model_network(self.run, a["node"], a["year"], self.version, a.get("lever"),
                                             a.get("uncertainty"), a.get("third"))
        if name == "country_context":
            return country_context(a["topic"])
        raise ToolError("UNKNOWN_TOOL", f"Unknown tool {name!r}; tools: {TOOL_NAMES}")

    def call(self, name: str, args: dict) -> dict:
        """Run one tool call. Errors the agent can fix come back as {"error": …}; every call is logged.

        Besides the raw arguments and reply, each log entry carries what the failure-mode checks read
        (backend/rdm/eval/failure_modes.py): the error code, the user turn the call came after, and the
        parameters in a fixed shape (levers and levels per policy, uncertainty ranges, threshold, ensemble).
        """
        t0 = time.time()
        code = None
        try:
            result, status = self._dispatch(name, dict(args or {})), "ok"
        except ToolError as e:
            result, status, code = {"error": str(e)}, "error", e.code
        except KeyError as e:
            result, status, code = {"error": f"Missing argument {e}"}, "error", "MISSING_ARGUMENT"
        entry = {"turn": len(self.log) + 1, "user_turn": self.user_turn, "tool": name, "args": args,
                 "status": status, "error_code": code, "params": _params(name, args or {}, result),
                 "seconds": round(time.time() - t0, 3), "version": self.version,
                 "reply_chars": len(json.dumps(result, ensure_ascii=False, default=str)), "reply": result}
        self.log.append(entry)
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return result
