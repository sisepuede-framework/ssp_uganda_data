"""
Claude Agent Service
=====================
Orchestrates the conversation between the user and the Uganda climate model.

Flow
----
1. Receive conversation history from the API layer.
2. Build a system prompt containing full feature registry knowledge.
3. Send to Claude with tool definitions.
4. Claude may call run_simulation (possibly multiple times for comparison).
5. Execute tool calls using the predictor.
6. Return Claude's final text response + simulation data to the API layer.

Extending the agent
-------------------
- To add a new tool: define it in TOOLS list and handle it in _execute_tool_call().
- To change Claude's persona or add domain rules: edit _build_system_prompt().
- To add streaming: wrap _run() in an async generator and yield chunks.

Design note: The agent is stateless. The full conversation history is passed
in with every request (maintained on the client side). This makes the backend
horizontally scalable with no session state.
"""

import json
import logging
from functools import lru_cache
from typing import Any

import anthropic

from backend.config import settings
from backend.services import pathways_lookup
from backend.services.context import get_country_context
from backend.services.predictor import get_sector_predictor, SECTOR_DISPLAY_NAMES
from backend.services import sector_crosswalk
from backend.services.s3_lookup import (
    get_scenario_variable_trajectories,
    get_strategy_l_values,
    list_strategies as _list_strategies,
)

logger = logging.getLogger(__name__)

# The 6 officially named pathways served from REAL pre-run data (not the surrogate).
# Order + names come from the single source of truth in pathways_lookup so the tool
# enum, the triage list, and the reference lines never drift apart. These are the
# triage category-A pathways — a request naming one routes to get_pathway_results.
NAMED_PATHWAYS: list[str] = list(pathways_lookup.PATHWAY_REGISTRY.keys())

# ── Tool definitions ─────────────────────────────────────────────────────────
# Claude uses these to understand what it can call and with what parameters.
# Keep descriptions precise — they directly affect translation accuracy.

TOOLS: list[dict] = [
    {
        "name": "run_simulation",
        "description": (
            "Estimate a custom Uganda pathway with the live metamodel (a METAMODEL ESTIMATE, "
            "not an official CDPM simulation). "
            "Call this whenever the user asks 'what would happen if...', wants to "
            "compare scenarios, or requests a simulation. "
            "Returns, vs a BAU baseline: total net emissions per year and per-sector "
            "emissions for 2025/2035/2040/2050/2070, and cost & benefit disaggregated by type and year "
            "(with per-year totals, net, and cost/benefit as % of GDP). "
            "You may call this tool multiple times in one response (e.g., to compare "
            "two different policy combinations)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": "Short human-readable name for this scenario, e.g. 'High Renewables + Land Protection'",
                },
                "lever_overrides": {
                    "type": "object",
                    "description": (
                        "Policy lever settings to change from the baseline. "
                        "Keys are group IDs as strings (e.g. '7' for renewable electricity). "
                        "Values are floats in [0.0, 1.0]. "
                        "Omitted levers default to 0.1 (BAU — minimal policy action). "
                        "Use 0.9–1.0 for aggressive/HBLE (maximum) ambition, "
                        "0.4–0.6 for moderate, 0.1–0.2 for BAU/no action."
                    ),
                    "additionalProperties": {"type": "number"},
                },
                "exogenous_overrides": {
                    "type": "object",
                    "description": (
                        "Exogenous (external) factor settings. "
                        "Keys are group IDs as strings (55–67). "
                        "Values are floats in [0.0, 1.0] where 0.0 = low end of the uncertainty "
                        "range, 0.5 = median (central) future, 1.0 = high end. "
                        "Omitted factors default to 0.5 (median future)."
                    ),
                    "additionalProperties": {"type": "number"},
                },
                "compare_to_baseline": {
                    "type": "boolean",
                    "description": "If true, also run a BAU baseline and return the % change for each metric. Default true.",
                },
                "strategy_id": {
                    "type": "integer",
                    "description": (
                        "Optional. When provided, look up the predefined L group values for "
                        "this SISEPUEDE strategy from the LHS samples table and use them "
                        "instead of custom lever_overrides. Any lever_overrides supplied "
                        "alongside strategy_id are ignored for L groups. "
                        "Use list_strategies to discover available IDs. "
                        "Example: strategy_id=6009 runs the NDC_2.5 scenario."
                    ),
                },
            },
            "required": ["scenario_name"],
        },
    },
    {
        "name": "get_pathway_results",
        "description": (
            "Return REAL pre-run SISEPUEDE results for one of Uganda's 6 officially named "
            "pathways. ALWAYS call this (NEVER run_simulation) when the user names one of: "
            + ", ".join(NAMED_PATHWAYS) + " (Candidate NDC3 is also called HBLE). "
            "These are ACTUAL official CDPM simulations, not metamodel estimates — and they are the "
            "only accurate source for the aggressive pathways, which the metamodel cannot reproduce. "
            "Returns, vs a real BAU baseline: total net emissions per year and per-sector "
            "emissions for 2019/2025/2035/2040/2050/2070, and cost & benefit disaggregated by "
            "type and year (per-year totals, net, and cost/benefit as % of GDP). BAU itself has "
            "zero cost-benefit (it is the baseline the others are measured against). Every result "
            "also carries real BAU and HBLE reference lines for the charts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pathway": {
                    "type": "string",
                    "enum": NAMED_PATHWAYS,
                    "description": "Which named pathway to retrieve. Must be one of the 6 official pathways.",
                },
                "groups_changed": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": (
                        "Optional. L group IDs (1–54) to ALSO return this pathway's real driver / "
                        "downstream-output variable trajectories for — the physical 'how' behind "
                        "the levers, read from the pathway's own run (no nearest-neighbour match)."
                    ),
                },
            },
            "required": ["pathway"],
        },
    },
    {
        "name": "list_strategies",
        "description": (
            "Return all predefined SISEPUEDE strategy scenarios available for simulation. "
            "Each entry has a strategy_id (integer), strategy_code (short code), and "
            "description (human-readable name). Call this when the user asks what scenarios "
            "or strategies are available, or to look up the ID for a named strategy "
            "before calling run_simulation with strategy_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_scenario_variables",
        "description": (
            "Explain the physical 'how' behind a lever: the actual SISEPUEDE model variables "
            "each changed lever moves and how they evolve over time. Returns, per lever, the "
            "INPUT driver variables it directly changes (2015→2070, available for all groups) "
            "and the DOWNSTREAM OUTPUT variables it affects (2019→2070, where they exist), "
            "taken from the nearest pre-computed experiment matching the given L values. "
            "Call this AFTER run_simulation when the user asks WHY/HOW a lever works, what "
            "physically changes, or which variables move. Headline emissions/GDP/cost come "
            "from run_simulation, NOT this tool. Only valid for L groups (groups 1–54)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "groups_changed": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": (
                        "List of L group IDs (integers, 1–54) whose variables should be "
                        "retrieved. Only include groups the user actually changed."
                    ),
                },
                "l_values": {
                    "type": "object",
                    "description": (
                        "The full set of L override values used in the scenario, as a dict "
                        "mapping group_id (string) to float in [0.0, 1.0]. Used to find the "
                        "nearest matching pre-computed trial via Euclidean distance."
                    ),
                    "additionalProperties": {"type": "number"},
                },
            },
            "required": ["groups_changed", "l_values"],
        },
    },
    {
        "name": "get_country_context",
        "description": (
            "Return formatted baseline data about Uganda's current situation. "
            "Use when the user asks about Uganda's current situation, baseline values, "
            "energy mix, GDP, population, agriculture, transport, or country context. "
            "Also use to contextualise a scenario result with real baseline numbers. "
            "Never answer country fact questions from memory — always call this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["energy_mix", "gdp", "population", "agriculture", "transport"],
                    "description": (
                        "The context topic to retrieve. "
                        "'energy_mix' — electricity generation technology mix. "
                        "'gdp' — GDP trajectory in billion USD at 2025, 2030, 2040, 2050. "
                        "'population' — rural/urban population at 2025, 2030, 2040, 2050. "
                        "'agriculture' — crop areas (ha) and livestock head counts. "
                        "'transport' — passenger and freight mode share fractions."
                    ),
                },
            },
            "required": ["topic"],
        },
    },
]


def run(
    messages: list[dict[str, str]],
    locked_overrides: dict[int, float] | None = None,
) -> dict[str, Any]:
    """
    Run the agent for one conversation turn.

    Parameters
    ----------
    messages : full conversation history, each {"role": ..., "content": ...}
    locked_overrides : optional group_id → value overrides that are always applied
                       regardless of what Claude decides (e.g. from UI sliders)

    Returns
    -------
    {
        "reply": str,                          # Claude's final text
        "simulation": dict | None,            # SimulationResponse-shaped dict, if model was run
        "scenario_interpretation": dict | None # What Claude decided to change
    }
    """
    locked_overrides = locked_overrides or {}
    tool_calls_log: list[dict] = []
    sector_predictor = get_sector_predictor()
    # Pass None if key is empty so the Anthropic client falls back to the
    # ANTHROPIC_API_KEY environment variable (set via shell or .env file).
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)

    system_prompt = _build_system_prompt()

    # Convert messages to Anthropic format
    anthropic_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    simulation_result: dict | None = None
    interpretation: dict | None = None
    # Ordered, factual record of every tool the agent ran this turn — surfaced to
    # the user for transparency (see _build_trace_event). Ground truth, not narration.
    trace: list[dict] = []

    # Prompt caching: the system prompt + tools (~13k tokens) are identical on every
    # API call. Marking the system block with cache_control caches the whole static
    # prefix (tools + system, in request order), so cache hits are billed at ~10% of
    # input price. This matters because the agentic loop re-sends the prefix on each
    # iteration, and follow-up questions reuse it within the 5-minute cache window.
    cached_system = [
        {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
    ]

    # Agentic loop: Claude may call tools multiple times
    max_iterations = 5  # safety limit
    for iteration in range(max_iterations):
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=cached_system,
            tools=TOOLS,
            messages=anthropic_messages,
        )

        logger.debug("Claude response (iter %d): stop_reason=%s", iteration, response.stop_reason)

        # Collect text and tool use blocks
        text_blocks = []
        tool_use_blocks = []
        for block in response.content:
            if block.type == "text":
                text_blocks.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        if response.stop_reason == "end_turn":
            # Claude is done
            return {
                "reply": "\n".join(text_blocks).strip(),
                "simulation": simulation_result,
                "scenario_interpretation": interpretation,
                "tool_calls_log": tool_calls_log,
                "trace": trace,
            }

        if response.stop_reason == "tool_use":
            # Append Claude's response (which includes tool_use blocks) to history
            anthropic_messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_result, sim_data, interp = _execute_tool_call(
                    tool_block.name,
                    tool_block.input,
                    sector_predictor,
                    locked_overrides,
                )
                if sim_data:
                    simulation_result = sim_data
                if interp:
                    interpretation = interp

                tool_calls_log.append({
                    "tool": tool_block.name,
                    "inputs": tool_block.input,
                })
                trace.append(_build_trace_event(
                    len(trace) + 1, tool_block.name, tool_block.input, tool_result, interp,
                ))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(tool_result),
                })

            anthropic_messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        logger.warning("Unexpected stop_reason: %s", response.stop_reason)
        break

    # Fallback if loop exhausted
    return {
        "reply": "\n".join(text_blocks).strip() if text_blocks else "I ran into an issue. Please try again.",
        "simulation": simulation_result,
        "scenario_interpretation": interpretation,
        "tool_calls_log": tool_calls_log,
        "trace": trace,
    }


# ── Tool execution ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _feature_group_names() -> dict[str, dict[str, str]]:
    """Group-id → display-name maps for policy levers and exogenous conditions,
    read once from the feature registry. Used to name the variables a surrogate
    run changed in the user-facing process trace.
    """
    try:
        with open(settings.feature_registry_path) as fh:
            reg = json.load(fh)
    except Exception as exc:  # registry missing/unreadable — names simply degrade
        logger.warning("Could not load feature registry for trace names: %s", exc)
        return {"lever": {}, "exogenous": {}}

    def _names(section: str) -> dict[str, str]:
        return {
            str(gid): meta.get("display_name", f"Group {gid}")
            for gid, meta in (reg.get(section) or {}).items()
        }

    return {"lever": _names("lever_features"), "exogenous": _names("exogenous_features")}


def _name_changed_groups(overrides: dict, kind: str, cap: int = 12) -> list[str]:
    """Turn {group_id: value} overrides into readable "Name: 0.90" trace lines,
    capped so a max-ambition run doesn't flood the trace (the rest go to the log).
    """
    names = _feature_group_names().get(kind, {})
    items = list((overrides or {}).items())
    lines = [f"{names.get(str(gid), f'Group {gid}')}: {float(val):.2f}" for gid, val in items[:cap]]
    if len(items) > cap:
        lines.append(f"…and {len(items) - cap} more")
    return lines


def _build_trace_event(
    step: int,
    tool_name: str,
    tool_input: dict,
    tool_result: dict,
    interp: dict | None,
) -> dict:
    """Build one user-facing process-trace event from an ACTUAL tool execution.

    The trace exists for transparency: it lets the user verify HOW an answer was
    produced (real pre-run vs surrogate, what was consulted, what was compared).
    It is derived from what the code really did — never from the model narrating
    its own steps — so it cannot be fabricated. See schemas.TraceStep.
    """
    interp = interp or {}
    result = tool_result if isinstance(tool_result, dict) else {}
    errored = "error" in result
    details: list[str] = []

    if tool_name == "run_simulation":
        scenario = interp.get("scenario_name") or tool_input.get("scenario_name", "scenario")
        label = f"Estimated “{scenario}” with the metamodel"
        data_source = "surrogate_xgboost"
        origin = "Live metamodel (XGBoost, trained on ~99,000 CDPM simulations)"
        # Name the specific variables the run changed (0–1 ambition value each).
        lever_lines = _name_changed_groups(interp.get("lever_overrides") or {}, "lever")
        exo_lines = _name_changed_groups(interp.get("exogenous_overrides") or {}, "exogenous")
        if lever_lines:
            details.append("Policy levers set — " + "; ".join(lever_lines))
        if exo_lines:
            details.append("Exogenous conditions set — " + "; ".join(exo_lines))
        if not lever_lines and not exo_lines:
            details.append("No levers changed from BAU (all at their default)")
        if interp.get("compared"):
            details.append("Compared against the metamodel's own BAU (clean policy delta)")
            if interp.get("real_refs"):
                details.append("Real BAU + HBLE official runs shown as reference lines")

    elif tool_name == "get_pathway_results":
        pathway = interp.get("scenario_name") or tool_input.get("pathway", "pathway")
        label = f"Retrieved the “{pathway}” official pathway result"
        data_source = "real_run"
        origin = "Official CDPM (SISEPUEDE) simulation — the 6 official named-pathway dataset"
        if not errored:
            details.append("Compared against the BAU and HBLE official pathway runs")
            if tool_input.get("groups_changed"):
                details.append("Included the pathway's own driver-variable detail for the changed levers")

    elif tool_name == "get_scenario_variables":
        label = "Looked up the physical driver & output variables"
        data_source = "reference"
        origin = "AWS run database — nearest SISEPUEDE experiment (design_id=4)"
        pid = result.get("primary_id")
        if pid is not None:
            details.append(f"Matched the nearest experiment (primary_id={pid})")

    elif tool_name == "get_country_context":
        topic = tool_input.get("topic", "")
        label = "Retrieved Uganda baseline context" + (f" ({topic})" if topic else "")
        data_source = "context"
        origin = "Uganda baseline dataset (loaded from AWS at startup)"

    elif tool_name == "list_strategies":
        label = "Listed the available SISEPUEDE strategies"
        data_source = "lookup"
        origin = "SISEPUEDE strategy registry (ATTRIBUTE_STRATEGY)"
        strategies = result.get("strategies")
        if strategies:
            details.append(f"{len(strategies)} strategies available")

    else:
        label = f"Called {tool_name}"
        data_source = "lookup"
        origin = tool_name

    if errored:
        details.append(f"Step failed: {result.get('error')}")

    return {
        "step": step,
        "tool": tool_name,
        "label": label,
        "data_source": data_source,
        "origin": origin,
        "details": details,
        "status": "error" if errored else "ok",
    }


def _execute_tool_call(
    tool_name: str,
    tool_input: dict,
    sector_predictor,
    locked_overrides: dict[int, float],
) -> tuple[dict, dict | None, dict | None]:
    """
    Dispatch a tool call and return (result_for_claude, simulation_data, interpretation).

    result_for_claude : JSON-serialisable dict sent back as the tool result
    simulation_data   : the full SimulationResponse-shaped dict (for the API response)
    interpretation    : what levers were changed and why (for the UI)
    """
    if tool_name == "run_simulation":
        return _run_simulation_tool(tool_input, sector_predictor, locked_overrides)

    if tool_name == "get_pathway_results":
        return _get_pathway_results_tool(tool_input)

    if tool_name == "get_scenario_variables":
        return _get_scenario_variables_tool(tool_input)

    if tool_name == "get_country_context":
        return _get_country_context_tool(tool_input)

    if tool_name == "list_strategies":
        return _list_strategies_tool(tool_input)

    logger.error("Unknown tool: %s", tool_name)
    return {"error": f"Unknown tool: {tool_name}"}, None, None


def _run_simulation_tool(
    inputs: dict,
    sector_predictor,
    locked_overrides: dict[int, float],
) -> tuple[dict, dict, dict]:
    scenario_name = inputs.get("scenario_name", "Scenario")
    compare = inputs.get("compare_to_baseline", True)
    strategy_id: int | None = inputs.get("strategy_id")

    # Parse Claude's overrides (keys come in as strings from JSON)
    lever_overrides: dict[int, float] = {
        int(k): float(v)
        for k, v in (inputs.get("lever_overrides") or {}).items()
    }
    exogenous_overrides: dict[int, float] = {
        int(k): float(v)
        for k, v in (inputs.get("exogenous_overrides") or {}).items()
    }

    # When a strategy_id is supplied, replace lever_overrides entirely with
    # the L values looked up from the LHS samples table for that strategy.
    # This honours the SISEPUEDE strategy definition rather than custom intensities.
    if strategy_id is not None:
        try:
            strategy_l = get_strategy_l_values(int(strategy_id))
            lever_overrides = strategy_l
            logger.info(
                "run_simulation: strategy_id=%d resolved to %d L group values",
                strategy_id, len(strategy_l),
            )
        except Exception as exc:
            logger.error("Failed to load strategy_id=%d: %s", strategy_id, exc)
            return {
                "error": f"Could not load strategy_id={strategy_id}: {exc}"
            }, None, None

    # Apply locked overrides from the UI (these always win).
    # L groups are 1–54, X (exogenous) groups are 55–67 in this run.
    for gid, val in locked_overrides.items():
        if 1 <= gid <= 54:
            lever_overrides[gid] = val
        elif 55 <= gid <= 67:
            exogenous_overrides[gid] = val

    # Run the surrogate for the SCENARIO. The surrogate now predicts the SAME 23
    # official inventory categories the real runs use, so the sector stack can honestly
    # show the surrogate scenario against the REAL BAU (they share the category scheme
    # AND the 2019 historical anchor). Headline emissions % and cost-benefit are also
    # measured vs real BAU. If the real runs can't be loaded we fall back to the
    # surrogate's own BAU so a run never breaks.
    sim = sector_predictor.predict_comparison(
        lever_overrides=lever_overrides,
        exogenous_overrides=exogenous_overrides,
        preset_scenario="bau",
        scenario_name=scenario_name,
    )
    scenario_series = sim["scenario"]

    try:
        refs = pathways_lookup.build_reference_bundle()
    except Exception as exc:  # curated CSVs unavailable — degrade, don't break
        logger.warning(
            "run_simulation: real BAU/HBLE unavailable (%s) — falling back to the "
            "surrogate's own BAU baseline", exc,
        )
        refs = None

    logger.info(
        "run_simulation: data_source=surrogate_xgboost (scenario=%s, levers=%d, "
        "exog=%d, baseline=surrogate_bau, real_refs=%s)",
        scenario_name, len(lever_overrides), len(exogenous_overrides),
        bool(refs),
    )

    if compare:
        # Compare the surrogate POLICY scenario against the surrogate's OWN BAU — a clean
        # policy delta from a single model (no surrogate-vs-real level bias). Both share
        # the 23 inventory categories and the 2019 anchor. The real BAU + HBLE runs are
        # overlaid as reference LINES by _attach_real_references below (frontier context),
        # NOT used as the comparison baseline.
        result = {
            "scenario": scenario_series,
            "baseline": sim["baseline"],
            "comparison": sim["comparison"],
        }
        result["sector_comparison"] = {**sim, "sector_meta_overrides": sector_crosswalk.SECTOR_META}
        result["cost_benefit_comparison"] = {
            "years": pathways_lookup.CB_YEARS,
            "scenario": scenario_series["cost_benefit"],
            "baseline": sim["baseline"]["cost_benefit"],
            "deltas": sim["cost_benefit_deltas"],
        }
    else:
        # No baseline comparison requested.
        result = {"scenario": scenario_series, "baseline": None, "comparison": None}
        result["sector_comparison"] = {
            "scenario": scenario_series, "baseline": None,
            "sector_meta_overrides": sector_crosswalk.SECTOR_META,
        }
        result["cost_benefit_comparison"] = {
            "years": pathways_lookup.CB_YEARS,
            "scenario": scenario_series["cost_benefit"],
            "baseline": None,
        }

    # Draw the real BAU + HBLE reference lines on both charts whenever the real runs
    # loaded (incl. the fallback / no-compare paths, for frontier context).
    if refs:
        _attach_real_references(result)

    # Build a concise summary for Claude to narrate from. sector_comparison carries
    # the sector/cost deltas and the real references (for the HBLE frontier value).
    summary = _build_result_summary(result, result.get("sector_comparison"))

    interpretation = {
        "lever_overrides": lever_overrides,
        "exogenous_overrides": exogenous_overrides,
        "scenario_name": scenario_name,
        # Provenance for the user-facing process trace.
        "data_source": "surrogate_xgboost",
        "compared": bool(compare),
        "baseline_source": "surrogate_bau",   # what-if compares vs the surrogate's own BAU
        "real_refs": bool(refs),               # real BAU + HBLE shown as reference lines
    }

    return summary, result, interpretation


def _attach_real_references(result: dict) -> None:
    """Attach real BAU + HBLE reference series to a result's chart bundles (in place).

    Shared by the surrogate flow (run_simulation) and available to any chart: the
    sector chart wants the full series (it reads sector_trajectories); the cost/benefit
    chart wants just the per-year cost_benefit maps. Non-fatal — a data hiccup simply
    omits the reference lines and the charts still render.
    """
    try:
        refs = pathways_lookup.build_reference_bundle()
    except Exception as exc:
        logger.warning("Could not attach real reference lines (non-fatal): %s", exc)
        return
    if isinstance(result.get("sector_comparison"), dict):
        result["sector_comparison"]["references"] = {
            "bau": refs["bau"], "hble": refs["hble"],
        }
    if isinstance(result.get("cost_benefit_comparison"), dict):
        result["cost_benefit_comparison"]["references"] = {
            "bau": refs["bau"]["cost_benefit"], "hble": refs["hble"]["cost_benefit"],
        }


def _get_pathway_results_tool(inputs: dict) -> tuple[dict, dict | None, dict | None]:
    """Return REAL pre-run results for one of the 6 named pathways.

    Mirrors _run_simulation_tool's result shape (scenario/baseline/comparison +
    sector_comparison + cost_benefit_comparison) so the schema, _build_result_summary,
    and both charts are reused unchanged — the only difference is the data is a real
    SISEPUEDE run, flagged data_source="real_run".
    """
    pathway = inputs.get("pathway", "")
    try:
        bundle = pathways_lookup.build_pathway_comparison(pathway)
    except LookupError as exc:
        return {"error": str(exc)}, None, None
    except FileNotFoundError as exc:
        logger.error("Pathway data unavailable: %s", exc)
        return {"error": f"Real pathway data is unavailable: {exc}"}, None, None

    result: dict = {
        "scenario": bundle["scenario"],
        "baseline": bundle["baseline"],
        "comparison": bundle["comparison"],
    }
    # Full sector bundle (scenario/baseline trajectories + sector_deltas) for the
    # stacked chart; it already carries the real BAU+HBLE reference series.
    result["sector_comparison"] = bundle
    result["cost_benefit_comparison"] = {
        "years": pathways_lookup.CB_YEARS,
        "scenario": bundle["scenario"]["cost_benefit"],
        "baseline": bundle["baseline"]["cost_benefit"],
        "deltas": bundle["cost_benefit_deltas"],
        "references": {
            "bau": bundle["references"]["bau"]["cost_benefit"],
            "hble": bundle["references"]["hble"]["cost_benefit"],
        },
    }

    # Same compact summary Claude narrates from, plus a real-run flag.
    summary = _build_result_summary(result, bundle)
    summary["data_source"] = "real_run"

    # Optional: real driver/output variable detail for the named levers.
    groups_changed = [int(g) for g in (inputs.get("groups_changed") or [])]
    if groups_changed:
        try:
            dv = pathways_lookup.get_pathway_driver_variables(pathway, groups_changed)
            summary["driver_detail"] = _format_driver_detail(dv, groups_changed)
        except Exception as exc:
            logger.warning("pathway driver detail failed: %s", exc)

    interpretation = {
        "pathway": pathway,
        "scenario_name": bundle["scenario"]["scenario_name"],
        "data_source": "real_run",
    }
    logger.info("get_pathway_results: %s (data_source=real_run)", pathway)
    return summary, result, interpretation


def _format_driver_detail(dv: dict, groups_changed: list[int]) -> str:
    """Format real driver/output variable trajectories (same layout the
    get_scenario_variables tool uses) for a named pathway."""
    primary_id = dv.get("primary_id")
    groups: dict = dv.get("groups", {})

    def _fmt_record(rec: dict) -> str:
        years = rec["by_year"]
        parts = [f"{y}={years[y]:g}" for y in sorted(years)]
        pct = rec.get("pct_change")
        pct_str = f"  ({pct:+.1f}%)" if pct is not None else ""
        return f"    • {rec['name']} [{rec['field']}]: " + ", ".join(parts) + pct_str

    def _section(title: str, recs: list, total: int) -> list[str]:
        out = [f"  {title} — {total} total:"]
        if recs:
            out.extend(_fmt_record(r) for r in recs)
            if total > len(recs):
                out.append(f"    …and {total - len(recs)} more")
        else:
            out.append("    (none mapped for this lever)")
        return out

    lines: list[str] = [f"Real pathway run: primary_id={primary_id}", ""]
    for gid in groups_changed:
        g = groups.get(gid) or groups.get(str(gid))
        if not g:
            continue
        counts = g.get("counts", {})
        lines.append(f"Group {gid} — {g['display_name']} ({g.get('transformation_code', '')})")
        lines += _section("Input variables (2019→2070)", g.get("inputs", []), counts.get("inputs", 0))
        lines += _section("Downstream output variables (2019→2070)", g.get("outputs", []), counts.get("outputs", 0))
        lines.append("")
    lines.append(dv.get("design_note", ""))
    return "\n".join(lines).rstrip()


def _get_scenario_variables_tool(inputs: dict) -> tuple[dict, None, None]:
    """
    Explain the physical 'how' behind the changed levers: the INPUT driver
    variables each lever moves (2015→2070, all groups) and the DOWNSTREAM OUTPUT
    variables it affects (2019→2070, where present), taken from the nearest
    pre-computed SISEPUEDE experiment (design_id=4).
    """
    groups_changed: list[int] = [int(g) for g in inputs.get("groups_changed", [])]
    l_values: dict[int, float] = {
        int(k): float(v) for k, v in (inputs.get("l_values") or {}).items()
    }

    try:
        result = get_scenario_variable_trajectories(
            group_ids=groups_changed, l_values=l_values
        )
    except Exception as exc:
        logger.error("get_scenario_variables_tool failed: %s", exc)
        return {
            "error": str(exc),
            "formatted_output": f"Could not retrieve variable trajectories: {exc}",
        }, None, None

    primary_id = result.get("primary_id")
    groups: dict = result.get("groups", {})

    def _fmt_record(rec: dict) -> str:
        years = rec["by_year"]
        parts = [f"{y}={years[y]:g}" for y in sorted(years)]
        pct = rec.get("pct_change")
        pct_str = f"  ({pct:+.1f}%)" if pct is not None else ""
        return f"    • {rec['name']} [{rec['field']}]: " + ", ".join(parts) + pct_str

    def _section(title: str, recs: list, total: int) -> list[str]:
        out = [f"  {title} — {total} total:"]
        if recs:
            out.extend(_fmt_record(r) for r in recs)
            if total > len(recs):
                out.append(f"    …and {total - len(recs)} more")
        else:
            out.append("    (none mapped for this lever)")
        return out

    lines: list[str] = [
        f"Nearest matched scenario: primary_id={primary_id}",
        "(design_id=4 — L and X both vary; real SISEPUEDE input & output variable trajectories)",
        "",
    ]
    for gid in groups_changed:
        g = groups.get(gid) or groups.get(str(gid))
        if not g:
            continue
        counts = g.get("counts", {})
        lines.append(f"Group {gid} — {g['display_name']} ({g.get('transformation_code', '')})")
        lines += _section("Input variables changed (2015→2070)",
                          g.get("inputs", []), counts.get("inputs", 0))
        lines += _section("Downstream output variables affected (2019→2070)",
                          g.get("outputs", []), counts.get("outputs", 0))
        lines.append("")

    lines.append(result.get("design_note", ""))
    formatted = "\n".join(lines).rstrip()

    logger.info(
        "get_scenario_variables_tool: primary_id=%s, groups=%s",
        primary_id, groups_changed,
    )
    return {
        "formatted_output": formatted,
        "primary_id": primary_id,
        "groups": groups,
    }, None, None


def _list_strategies_tool(_inputs: dict) -> tuple[dict, None, None]:
    """Return all SISEPUEDE strategies from ATTRIBUTE_STRATEGY.csv."""
    try:
        strategies = _list_strategies()
    except Exception as exc:
        logger.error("list_strategies_tool failed: %s", exc)
        return {"error": str(exc)}, None, None
    logger.info("list_strategies_tool: returned %d strategies", len(strategies))
    return {"strategies": strategies}, None, None


def _get_country_context_tool(inputs: dict) -> tuple[dict, None, None]:
    """
    Return formatted Uganda baseline context for the requested topic.
    Delegates entirely to context.get_country_context(), which loads data
    from S3 at module import time and caches it.
    """
    topic: str = inputs.get("topic", "")
    text = get_country_context(topic)
    logger.info("get_country_context_tool: topic=%s", topic)
    return {"context": text}, None, None


def _build_result_summary(result: dict, sector_result: dict | None = None) -> dict:
    """
    Build a compact JSON summary of the simulation result.
    This is what Claude receives as the tool result — it uses this to write
    its narrative response. Keep it structured but readable.
    """
    scenario = result["scenario"]
    baseline = result.get("baseline")
    comparison = result.get("comparison")

    # Real HBLE frontier headline values, for narrating where a scenario lands
    # relative to the aggressive frontier (BAU stays the % baseline). Present on
    # both the surrogate and named-pathway bundles via the real references.
    hble_ref = None
    if sector_result and isinstance(sector_result.get("references"), dict):
        hble_ref = sector_result["references"].get("hble")

    summary: dict[str, Any] = {
        "scenario_name": scenario["scenario_name"],
        "predictions": {},
    }

    for metric, pred in scenario["predictions"].items():
        entry: dict[str, Any] = {
            "value": pred["value"],
            "unit": pred["unit"],
            "display_name": pred["display_name"],
        }
        if comparison and metric in comparison:
            entry["change_from_bau_pct"] = comparison[metric]
        if baseline and metric in baseline["predictions"]:
            entry["bau_value"] = baseline["predictions"][metric]["value"]
        if hble_ref and metric in hble_ref.get("predictions", {}):
            entry["hble_value"] = hble_ref["predictions"][metric]["value"]
        summary["predictions"][metric] = entry

    if sector_result:
        sector_deltas = sector_result.get("sector_deltas", {})
        sector_breakdown: dict[str, Any] = {}
        for sector, years in sector_deltas.items():
            display = SECTOR_DISPLAY_NAMES.get(sector, sector.upper())
            sector_breakdown[sector] = {"display_name": display, "unit": "Mt CO₂e"}
            for year in [2025, 2050, 2070]:
                if year in years:
                    d = years[year]
                    sector_breakdown[sector][str(year)] = {
                        "scenario": d["scenario"], "bau": d["bau"],
                        "delta": d["delta"], "pct_change": d["pct_change"],
                    }
        summary["sector_breakdown"] = sector_breakdown

        # Per-year cost/benefit totals + cost-as-%-of-GDP for narration.
        cb_deltas = sector_result.get("cost_benefit_deltas", {})
        if cb_deltas:
            cost_benefit: dict[str, Any] = {}
            for year, d in cb_deltas.items():
                cost_benefit[str(year)] = {
                    "total_benefit_bn_usd": d["benefit_scenario"],
                    "total_cost_bn_usd": d["cost_scenario"],
                    "net_bn_usd": d["net_scenario"],
                    "cost_pct_gdp": d["cost_pct_gdp_scenario"],
                    "bau_net_bn_usd": d["net_bau"],
                }
            summary["cost_benefit_by_year"] = cost_benefit

    return summary


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    """
    Build the Claude system prompt. This is the single most important piece
    of the agent — it defines how Claude understands the model and translates
    user language into simulation inputs.

    To adjust Claude's behaviour:
    - Change tone/persona → edit the opening section
    - Add domain rules → add to the RULES section
    - Add new output interpretation → edit the OUTPUTS section
    - Add caveats → edit the LIMITATIONS section
    """
    registry_path = settings.feature_registry_path
    with open(registry_path) as f:
        registry = json.load(f)

    # Build lever feature list
    lever_lines = []
    for gid, meta in sorted(registry["lever_features"].items(), key=lambda x: int(x[0])):
        lever_lines.append(
            f"  Group {gid} | {meta['display_name']} | Sector: {meta['sector']}\n"
            f"    0.0 → {meta['semantic_min']}\n"
            f"    1.0 → {meta['semantic_max']}\n"
            f"    Aliases: {', '.join(meta['aliases'])}"
        )

    # Build exogenous feature list (X features are sampled in [0, 1] in this run).
    exog_lines = []
    for gid, meta in sorted(registry["exogenous_features"].items(), key=lambda x: int(x[0])):
        exog_lines.append(
            f"  Group {gid} | {meta['display_name']} | {meta['sector']}\n"
            f"    0.0 → {meta['semantic_0']}\n"
            f"    0.5 → {meta['semantic_05']}\n"
            f"    1.0 → {meta['semantic_1']}\n"
            f"    Aliases: {', '.join(meta['aliases'])}"
        )

    # Compact L-sector and X-factor rosters, used by the "what can I ask you?" answer
    # below. Built from the registry so the capability answer can never drift from the
    # levers that actually exist.
    sector_counts: dict[str, int] = {}
    for meta in registry["lever_features"].values():
        sector_counts[meta["sector"]] = sector_counts.get(meta["sector"], 0) + 1
    sector_summary = "; ".join(
        f"{sector} ({n})"
        for sector, n in sorted(sector_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    exog_summary = ", ".join(
        meta["display_name"]
        for _, meta in sorted(registry["exogenous_features"].items(), key=lambda x: int(x[0]))
    )

    # Static description of the model output categories (175 disaggregated targets).
    output_lines = [
        "  Emissions by sector × year — emission_<sector>_yr<year> [Mt CO₂e], for the 15",
        "    SISEPUEDE subsectors at 2025/2035/2040/2050/2070 (frst is negative = carbon sink).",
        "    Economy-wide total per year is derived by summing sectors, reported as",
        "    'Total Net Emissions (<year>)'.",
        "  Co-benefits by type × year — benefit_<type>_yr<year> [billion USD], 16 types.",
        "  Costs by type × year — cost_<type>_yr<year> [billion USD], 3 types (fuel, system, technical).",
        "  GDP by year — gdp_mmm_usd_yr<year> [billion USD], used for cost/benefit as % of GDP.",
    ]

    # The 6 officially named pathways served from REAL pre-run data via
    # get_pathway_results (triage category A). Built from pathways_lookup so the
    # prompt, the tool enum, and the reference lines share one source of truth.
    named_pathway_lines = "\n".join(
        f"  - {name} (primary_id {meta['primary_id']}"
        + (", the BAU baseline — zero cost-benefit" if meta["is_baseline"]
           else f", strategy {meta['strategy_code']}")
        + (", a.k.a. HBLE — the aggressive frontier" if meta["primary_id"] == pathways_lookup.HBLE_PID else "")
        + ")"
        for name, meta in pathways_lookup.PATHWAY_REGISTRY.items()
    )

    prompt = f"""You are the assistant inside the **Uganda Climate Pathways Explorer** (formerly the Uganda Climate Policy Simulator), the exploration tool for Uganda's National Climate and Development Strategy.

Your role is to help government officials, policymakers, and development partners explore how different levels of sectoral transition — and different assumptions about Uganda's future development and implementation conditions — could affect greenhouse gas emissions, costs, and wider development benefits between 2025 and 2070.

The analysis rests on Uganda's **Country Development Pathway Model (CDPM)**, developed using the **SISEPUEDE** modelling framework. You answer from two distinct sources:
- **Official pathway results** — a fixed set of official CDPM simulations (Uganda's NDC pathways and the High Benefits, Low Emission (HBLE) pathway, which underpins Uganda's NDC 3.0).
- **Metamodel estimates** — a live metamodel (XGBoost) trained on ~99,000 CDPM simulations, which estimates results for pathway combinations that were never officially simulated. It covers a very large range of combinations, at a lower level of detail than the official CDPM simulations.

This combination is what the tool is for: the official pathways used to be readable only in a document; here they can be interrogated directly, AND extended to combinations of ambition and country conditions that no official simulation covers.

## OBJECTIVE

Your single objective is to help policymakers explore possible pathways and their implications for Uganda's emissions, costs, and development benefits. Every interaction must serve that goal. If a request does not, say so plainly and steer back to what you can do.

## TERMINOLOGY — USE THESE WORDS EXACTLY

- Call a result from one of the 6 named pathways an **official pathway result** (from an official CDPM simulation).
- Call anything you produce with `run_simulation` a **metamodel estimate**. Say so explicitly in the first sentence of the answer — the reader must never mistake an estimate for an official simulation.
- Do NOT use "simulation" as a generic word for every answer. "Simulation" belongs to the official CDPM runs only.
- Never say the number of possible combinations is "infinite" or "unlimited". Say **"a very large range of pathway combinations"**.
- Always expand HBLE on first use: **High Benefits, Low Emission (HBLE) pathway**, and note that it provides the analytical basis for **Uganda's NDC 3.0**.
- Refer to the underlying model as Uganda's **Country Development Pathway Model (CDPM)**, developed with the **SISEPUEDE** framework — not as "the surrogate", "the ML model", or "my training data".
- Prefer **sectoral transition** and **ambition level** over "policy intensity"; prefer **development benefits** over "co-benefits" in user-facing prose.

## WHAT YOU CAN AND CANNOT DO

You CAN:
- Adjust the 54 policy levers (L groups) and the 13 exogenous uncertainty factors (X groups) listed below.
- Report, for any pathway you run, vs a BAU baseline:
  - Emissions: total net emissions per year and per-sector emissions, both at 2025/2035/2040/2050/2070.
  - Cost & benefit disaggregated by type and year (16 benefit types, 3 cost types) for 2025/2035/2040/2050/2070, including per-year total benefit, total cost, net, and cost/benefit as a % of GDP.
- Run the predefined standard pathways (see TRIAGE) and report Uganda's baseline situation via the get_country_context tool.

You CANNOT (these are out of scope — decline them):
- Anything for a country other than Uganda.
- Metrics, variables, sectors, pollutants, or indicators the model does not output (only the emissions and cost/benefit outputs above exist).
- Years or horizons outside 2025–2070, or annual detail beyond the reported years.
- Policies or interventions that have no corresponding lever in the list below.
- General knowledge, definitions, news, or advice unrelated to running and interpreting these pathways.

## WHAT THE USER CAN ASK YOU — answer this directly when asked

When the user asks "what can I ask you?", "what can this tool do?", "which levers can I move?",
"what assumptions can I change?", or anything similar, answer CONCRETELY and without calling a tool.
Give three parts, briefly:

1. **The official pathways** — the 6 named CDPM pathways listed under REQUEST TRIAGE. These return
   official pathway results, including the HBLE pathway that underpins Uganda's NDC 3.0.
2. **Sectoral transitions — the ambition levers (L).** 54 levers across 16 sectors:
   {sector_summary}. Each runs from no action (business as usual) to maximum technically feasible
   deployment by 2070, and they can be combined freely — that is what the metamodel estimates.
3. **Country conditions — the exogenous uncertainties (X).** 13 factors outside Uganda's control:
   {exog_summary}. Each runs from the low end of its uncertainty range, through the median (central)
   future, to the high end.

Then state briefly what is out of scope (other countries; metrics the model does not produce; years
outside 2025–2070; interventions with no corresponding lever), and invite one concrete question,
offering two examples drawn from the lists above. Do NOT dump all 54 levers unless the user asks for
the full list; name the sectors and offer to go deeper on any one of them.

## REQUEST TRIAGE

Before answering ANY request, silently classify it into exactly one of three categories, then act accordingly:

**A — Named pathway (REAL pre-run data).** The user names one of Uganda's 6 official pathways:
{named_pathway_lines}
→ Call `get_pathway_results` with that pathway. These return ACTUAL official CDPM (SISEPUEDE) simulations — accurate, and the ONLY correct source for the aggressive pathways (the metamodel cannot reproduce them). NEVER use `run_simulation` for these, and never hand-set levers to approximate them.

**B — Custom pathway (estimate it with the metamodel).** The user describes a custom combination of the available levers ("what if we push renewables and protect forests?").
→ Call `run_simulation` with `lever_overrides`. Present the result as a METAMODEL ESTIMATE, and say so in your first sentence. It is reliable near BAU. Its emissions/costs are the metamodel's; the "% vs BAU" and the comparison are measured against the official BAU simulation, and the official HBLE simulation is shown as the ambition frontier (see REFERENCE PATHWAYS). Do NOT use it to approximate a named pathway from category A.

**C — Cannot answer.** The request needs a metric/variable/sector/region/time the model does not produce, or a policy with no corresponding lever.
→ Do NOT guess. Give a brief one-sentence decline and redirect to the closest thing you CAN do (a related lever you can adjust, or an output you can report).

Special cases:
- **Other SISEPUEDE strategies** beyond the 6 named pathways (e.g. a specific sector-only strategy by code) — these are NOT pre-served. They remain lookup-only via `list_strategies`; do not invent their results. Offer the closest named pathway, or a custom `run_simulation` if the user specifies the levers.
- **Borderline Uganda/climate questions** outside the outputs above — answer only if they are about your own levers, outputs, pathways, or Uganda's baseline (via get_country_context). Otherwise treat as category C.

## UGANDA COUNTRY CONTEXT

Uganda has approximately 47 million people and a GDP of roughly 40 billion USD. About 85 percent of Uganda's electricity comes from hydropower, and agriculture employs 72 percent of the workforce.

Uganda's NDC (Nationally Determined Contribution) target is a 22 percent reduction in greenhouse gas emissions by 2030 relative to a business-as-usual baseline. This target is conditional on receiving adequate international financial and technical support.

When the user asks about Uganda's current situation, baseline data, or sector-level statistics, call the get_country_context tool — do not invent numbers.

## MODEL MECHANICS

The model takes 67 input parameters — grouped into 54 policy lever groups (L, scale 0 to 1) and 13 exogenous uncertainty groups (X, scale 0 to 1) — and predicts emissions (per-sector by year + a derived economy-wide total), implementation costs, and economic co-benefits (both disaggregated by type and year), plus cost/benefit as a share of GDP. See WHAT YOU CAN AND CANNOT DO for the exact output set.

**L groups are policy choices.** You CAN set L values in response to user policy requests.

**X groups are exogenous uncertainties** — external conditions beyond Uganda's control (GDP trajectory, population growth, fossil fuel prices, etc.). You must NEVER set X values in response to a policy request. Only adjust X values when the user explicitly asks to explore a different future scenario or uncertainty condition (e.g. "what if GDP grows faster"). When describing X groups, frame them as scenario context, not policy levers.

## L TRANSFORM FORMULA

The physical effect of each L lever is computed as:

  T = 0.9 × x + 0.1    (the standard policy design)

Where x is the L value in [0, 1] and T is the transformation magnitude in [0.1, 1.0].

Reverse mapping (if you know the physical target T and need the L value):
  x = (T − 0.1) / 0.9

To describe what a lever setting means in physical terms, use the per-group fields in feature_registry.json: `semantic_min` (what L=0 means), `semantic_max` (what L=1 means), and `policy_description`. For the ACTUAL physical numbers — which model variables the lever moves and their values over time — call get_scenario_variables, which returns the real input-variable trajectories from the nearest SISEPUEDE experiment.

The SISEPUEDE ramp mechanism means T is not applied instantly — it is the magnitude TARGET at the end of the simulation (2070). A linear or sigmoid ramp transitions each policy variable progressively from its baseline toward the 2070 target over approximately 20–30 years. get_scenario_variables shows this ramp directly (the driver trajectory 2015→2070).

## REFERENCE PATHWAYS ON CHARTS

Every chart is anchored by two REAL reference lines, attached automatically to every
result (both get_pathway_results and run_simulation):
- **BAU** — the real business-as-usual run (primary_id 0). Minimal policy action.
- **HBLE / Candidate NDC3** — the real aggressive-frontier run (primary_id 5005). Maximum ambition.

**These are the only two reference lines.** They come from official CDPM simulations, not the metamodel.
You do not set or run them — they are always present in the payload. Do not add other
named strategies as chart lines. A user's custom `run_simulation` scenario appears as its
own line on top of these two references.

Note on custom runs: a `run_simulation` scenario is now compared against the REAL BAU run
(the baseline for the stated "% vs BAU") and the REAL HBLE run (the ambition frontier).
This gives policymakers a real what-if comparison. Caveat to keep in mind (do not belabour
it to the user unless asked): the pathway's own numbers come from the metamodel, so the
comparison folds in the metamodel's error — this is an accepted, temporary trade-off.
When helpful, note where the scenario lands between real BAU and the HBLE frontier
(the `hble_value` in the result).

## NAMED SISEPUEDE STRATEGIES

The model has access to 76 named strategies (NDC variants, sector-specific, etc.). **Do not use or surface these in responses unless the user explicitly names one.** They are available for lookup only.

## POLICY LEVERS (L features) — Scale: 0.0 to 1.0

0.0 = No policy action / business as usual
0.5 = Moderate ambition
0.9–1.0 = Maximum / HBLE ambition

{chr(10).join(lever_lines)}

## EXOGENOUS UNCERTAINTY FACTORS (X features) — Scale: 0.0 to 1.0

These are external conditions BEYOND policy control. Adjust only when the user explicitly asks about different future scenarios — never in response to a policy request.

0.0 = Low end of the uncertainty range
0.5 = Median (central) future — the default
1.0 = High end of the uncertainty range

IMPORTANT: These are RELATIVE scales within the model's uncertainty range. They do not directly correspond to % changes in absolute GDP, population, etc.

{chr(10).join(exog_lines)}

## MODEL OUTPUTS

{chr(10).join(output_lines)}

## COST & BENEFIT BREAKDOWN

Every run_simulation result includes a `cost_benefit_by_year` field with, for 2025/2035/2040/2050/2070: `total_benefit_bn_usd` (positive), `total_cost_bn_usd` (net cost, usually negative), `net_bn_usd`, `cost_pct_gdp`, and the BAU net for comparison. Use these directly — no extra tool call.

- `cost_pct_gdp` is ALREADY a percentage (e.g. 0.37 means 0.37% of GDP). Do not multiply it.
- Benefits are positive cash flows; costs are negative. Net = benefits + costs.
- To show this visually, place a `cost_benefit` chart block where it fits your narrative
  (see CHARTS — YOU CONTROL THEM). It does not render on its own.

## SECTOR BREAKDOWN

Every run_simulation result includes a `sector_breakdown` field with emissions at the
target years for the **23 official inventory categories** (the same categories the
official pathways / Tableau use). Use this to answer sector-specific questions directly
— no additional tool call needed.

The sector KEYS are category slugs → display names:
- `forest_land_removals` → Forest Land - Removals — **Uganda's LARGEST source (~62 Mt).**
  This is the CO₂ from burning biomass for energy (firewood + charcoal; Uganda is ~89%
  biomass energy). Under IPCC/LULUCF accounting this carbon is booked as forest-land
  removals, NOT as electricity. To cut it, the levers are CLEAN COOKING (efficient/
  modern stoves, fuel switching) and AFFORESTATION — **not** power plants.
- `electricity_and_heat_generation` → Electricity and Heat Generation — TINY for Uganda
  (~0.08 Mt, grid is ~85% hydro). Do NOT attribute the biomass block to this.
- `residential`, `commercial`, `other_combustion` → non-biomass stationary combustion
  in buildings (the biomass part of buildings is already in Forest Land - Removals).
- `livestock` → Livestock (enteric fermentation + manure); `agriculture_and_managed_soil`
  → Agriculture & Managed Soil.
- `deforestation`, `other_land_use_conversion`, `wetlands` → land-use change (LULUCF).
- `forest_land_sequestration` → Forest Land - Sequestration (NEGATIVE = carbon sink);
  `forest_land_methane` → forest CH₄.
- `industrial_combustion` → Industrial Combustion (non-biomass); `ippu` → Industrial
  Processes; `fuel_production` → Fuel Production; `fugitive_emissions` → Fugitive.
- `transportation`, `solid_waste`, `wastewater_treatment` → as named.
- `carbon_capture_industries` → CCS; `other_not_estimated_*` → small residual categories.

LULUCF categories (land sector): forest_land_removals, forest_land_sequestration,
forest_land_methane, deforestation, other_land_use_conversion, wetlands, and the
other_not_estimated_* ones. The rest are non-LULUCF (energy/industry/waste/ag).

Each sector entry in `sector_breakdown` has:
- `scenario`: predicted Mt CO₂e for the user's scenario
- `bau`: BAU baseline value
- `delta`: absolute change (negative = reduction)
- `pct_change`: % change vs BAU

When reporting sector results, always compare scenario vs BAU and highlight which sectors benefit most from the user's policy choices.

## RULES

0. **Triage first (A/B/C).** Run the REQUEST TRIAGE on every request before doing anything else. Never answer a category-C request by guessing — decline briefly and redirect. Never state a pathway result, emission number, cost, or co-benefit that was not produced by a tool call IN THIS turn; if you have not run the relevant pathway this turn, run it or decline.

1. **Always call run_simulation BEFORE giving any emissions, cost, or co-benefit numbers.** Never state or estimate these values without first running the model.

2. **Sector emissions are included automatically in run_simulation results** via `sector_breakdown`. Use them directly to answer sector-specific questions. Call `get_scenario_variables` only to explain the physical "how" — which specific input variables a lever changes and the downstream output variables it moves, and their trajectories over time. It does NOT return headline emissions (those come from run_simulation).

3. **Call get_country_context when the user asks about Uganda's current situation**, baseline conditions, or sector-level statistics (energy mix, GDP, population, agriculture, transport). Never invent baseline numbers — always retrieve them.

4. **Never hallucinate values.** All emission numbers, costs, co-benefits, and baseline statistics must come from tool calls. If a tool call fails, say so explicitly.

5. **Never set X groups in response to a policy request.** X groups are scenario context only. If the user says "what if GDP is higher", you may adjust group 57 (GDP Growth Trajectory) — but not in the same run as a policy lever change unless the user explicitly asked for both.

6. **Be transparent about information sources.** Any fact, statistic, or context that did NOT come from a tool call must be explicitly flagged. Use phrasing like "Based on general knowledge (not from the model):" or "From my training data, not verified against Uganda's input data:". Never blend tool-sourced and general-knowledge data in the same sentence without distinguishing them.

7. **Named pathways are official pathway results; custom combinations are metamodel estimates — route each correctly and label each correctly.** A request for one of the 6 named pathways → `get_pathway_results` (an official CDPM simulation). A request for custom lever settings → `run_simulation` (a metamodel estimate). Do not use `run_simulation` to approximate a named pathway, and never let a metamodel estimate read as though it came from an official CDPM simulation. Both flows compare against the SAME official anchors — the official BAU pathway (the baseline, zero cost-benefit by construction) and the official HBLE pathway (the frontier) — so an estimate and an official result can be read on the same axes. The only caveat: an estimate's own values carry the metamodel's error (accepted, temporary); flag that only if the user asks how the comparison is made.

## TRANSLATION RULES

When the user describes a policy or scenario, translate it to group values:

| User says | What to do |
|---|---|
| "aggressive/ambitious/maximum" on policy X | Set L group to 0.9 |
| "moderate/some/partial" on policy X | Set L group to 0.5 |
| "business as usual/no change/baseline" | Set all L groups to 0.1 |
| "slight/small" on policy X | Set L group to 0.2–0.3 |
| "phase out" fossil fuels in sector | Set relevant fuel-switch L group to 0.9 |
| "protect forests" | Set L groups 15 (reduce deforestation) + 9 (increase forest sequestration) to 0.8–0.9 |
| "Net Zero" / "HBLE" / "maximum ambition" (by name) | Call `get_pathway_results` with "Candidate NDC3" — the REAL aggressive pathway. Do NOT approximate it with `run_simulation`. |
| "higher GDP growth" | Set X group 57 to 0.7–0.9 (scenario only) |
| "lower/pessimistic GDP" | Set X group 57 to 0.1–0.3 (scenario only) |
| "high population growth" | Set X group 60 to 0.8–1.0 (scenario only) |
| "expensive fossil fuels" | Set X group 56 to 0.7–0.9 (scenario only) |
| "optimistic future" | Set all X groups to 0.7–0.8 (scenario only) |
| "pessimistic future" | Set all X groups to 0.1–0.3 (scenario only) |

## CHARTS — YOU CONTROL THEM

Charts do NOT render automatically. You decide which charts (if any) help the reader,
and you place each one exactly where it belongs by writing a fenced ```chart block at
that position in your answer. Use zero, one, or several. If a chart would not aid
understanding (conceptual questions, definitions, simple facts), include none.

Workflow: run the simulation → form your analysis → write the answer → drop a ```chart
block at each point where a visual makes the surrounding text clearer (e.g. an emissions
chart first, then prose about costs, then a cost/benefit chart).

A chart block carries only the template name + which view; the data is filled in
automatically from the simulation you ran THIS turn. Schema:

```chart
{{ "template": "<name>", "scenario": "current" | "scenario" | "both", "title": "optional" }}
```

Templates:
- "emissions_by_sector" — stacked emissions by sector.
    scenario:"current" = one panel, BAU only (use for "current emissions", no comparison);
    "scenario" = one panel, the user's scenario; "both" = BAU vs scenario side by side.
- "emissions_timeseries" — total emissions trajectory across 2019–2070.
    "current" = BAU line only; "scenario" = scenario line; "both" = both lines.
- "cost_benefit" — diverging bars (benefits up, costs down) by year, with a net line.
    "scenario" = the scenario alone; "both" = adds the BAU net reference line;
    "current" = BAU only.

Rules:
- Only emit a chart block after calling `run_simulation` this turn — the data must be fresh.
- For "show me current / actual emissions" with no scenario: run the `bau` preset and use
  scenario:"current".
- Never claim you cannot draw a chart — place the appropriate block instead.
- Don't over-chart: usually one or two blocks per answer, placed where they support the text.

## RESPONSE STYLE

Write in the analytical register of Uganda's NDC report — but concise. Your value is
helping the reader understand a scenario WITHOUT reading the full document, so stay
tight: usually 1–3 short paragraphs.

Principles:
- **Say which kind of answer this is, first.** An answer built from `get_pathway_results` opens by
  naming it as an official pathway result; an answer built from `run_simulation` opens by naming it
  as a metamodel estimate of a combination outside the official pathways. One clause is enough —
  "The metamodel estimates that…" — but it must never be missing.
- **Magnitude + horizon + driver.** Never just "emissions rise" — say how much, by when,
  and what drives it (e.g. "emissions climb from ~105 to ~200 MtCO₂e by 2050, driven by
  population growth and energy demand").
- **One story: emissions → development co-benefits → investment.** Connect mitigation to
  health, air quality, congestion, forests, AND to the cost/investment it implies. Avoid
  listing metrics in isolation.
- **Narrate by sector and driver** (clean cooking, livestock, electrification, land
  restoration), and by scenario when comparing.
- **Frame trade-offs explicitly** ("higher-benefit but also higher-investment").
- **Tables are optional.** Use a small markdown table (`| Col | Col |`) only when it
  genuinely clarifies dense numbers — never as a default wrapper for every answer.
- Do NOT use horizontal rules (`---`, `***`) to separate sections — they don't render.
  Separate sections with a short `##`/`###` heading or a blank line instead.
- Lead with the key finding in the first sentence, then support it.
- Keep the source-honesty rules above: never state an emission, cost, or co-benefit
  number that did not come from a tool call THIS turn.

Place charts where they support the narrative — see CHARTS — YOU CONTROL THEM.

Match the user's language. Never say "I cannot run simulations" — call run_simulation
whenever the user asks about scenarios.
"""
    return prompt
