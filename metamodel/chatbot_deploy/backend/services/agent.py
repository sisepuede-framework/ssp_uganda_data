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
from typing import Any

import anthropic

from backend.config import settings
from backend.services.context import get_country_context
from backend.services.predictor import get_sector_predictor, SECTOR_DISPLAY_NAMES
from backend.services.s3_lookup import (
    get_scenario_outcomes,
    get_strategy_l_values,
    list_strategies as _list_strategies,
)

logger = logging.getLogger(__name__)

# ── Predefined "standard" pathways (triage category A) ───────────────────────
# These are the pathways the bot may run by name without the user specifying
# levers. To expose a new one (e.g. NDC2, NDC3, Conditional, Unconditional):
#   1. Add an entry here (preset key → one-line description), AND
#   2. Add a matching preset in predictor.PRESET_DEFAULTS (+ any per-group
#      overrides, like NETZERO_L_OVERRIDES).
# The A-vs-B triage test is simply: "is the requested pathway in this dict?"
PREDEFINED_PATHWAYS: dict[str, str] = {
    "bau":     "Business as Usual — minimal policy action (all levers at baseline)",
    "netzero": "Net Zero — Uganda's calibrated maximum-ambition strategy",
}

# ── Tool definitions ─────────────────────────────────────────────────────────
# Claude uses these to understand what it can call and with what parameters.
# Keep descriptions precise — they directly affect translation accuracy.

TOOLS: list[dict] = [
    {
        "name": "run_simulation",
        "description": (
            "Run the Uganda climate surrogate model for a specific policy scenario. "
            "Call this whenever the user asks 'what would happen if...', wants to "
            "compare scenarios, or requests a simulation. "
            "Returns, vs a BAU baseline: emission metrics (total cumulative 2025–2070, "
            "near-term 2033–37 and long-term 2066–70 averages), per-sector emissions for "
            "2030/2040/2050/2070, and cost & benefit disaggregated by type and year "
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
                        "Keys are group IDs as strings (e.g. '8' for renewable electricity). "
                        "Values are floats in [0.0, 1.0]. "
                        "Omitted levers default to 0.1 (BAU — minimal policy action). "
                        "Use 0.9–1.0 for aggressive/Net Zero ambition, "
                        "0.4–0.6 for moderate, 0.1–0.2 for BAU/no action."
                    ),
                    "additionalProperties": {"type": "number"},
                },
                "exogenous_overrides": {
                    "type": "object",
                    "description": (
                        "Exogenous (external) factor settings. "
                        "Keys are group IDs as strings (60–68). "
                        "Values are floats in [-1.0, 1.0] where -1.0 = fixed baseline trajectory, "
                        "0.0 = low/pessimistic scenario, 0.5 = median uncertainty, "
                        "1.0 = high/optimistic scenario. "
                        "Omitted factors default to -1.0 (baseline trajectory)."
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
            "Retrieve SISEPUEDE simulation outputs (sector-level CO2e emission trajectories) "
            "for the nearest pre-computed experiment matching the given L values. "
            "Call this AFTER run_simulation whenever the user asked what would actually happen "
            "in specific sectors, or wants to see the simulated emission breakdown by sector. "
            "Returns emission_co2e_subsector_total for each sector affected by the changed groups. "
            "Only valid for L groups (groups 1–59). Do NOT use for X group variables. "
            "Always uses design_id=3 (L-only design)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "groups_changed": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": (
                        "List of L group IDs (integers, 1–59) whose variables should be "
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

    # Agentic loop: Claude may call tools multiple times
    max_iterations = 5  # safety limit
    for iteration in range(max_iterations):
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=system_prompt,
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
    }


# ── Tool execution ───────────────────────────────────────────────────────────

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

    # Apply locked overrides from the UI (these always win)
    for gid, val in locked_overrides.items():
        if 1 <= gid <= 59:
            lever_overrides[gid] = val
        elif 60 <= gid <= 68:
            exogenous_overrides[gid] = val

    # Run the model. A single sector pipeline produces both the 11 aggregate
    # metrics and the per-sector trajectories, so one call covers everything.
    sim = sector_predictor.predict_comparison(
        lever_overrides=lever_overrides,
        exogenous_overrides=exogenous_overrides,
        preset_scenario="bau",
        scenario_name=scenario_name,
    )

    if compare:
        result = {
            "scenario": sim["scenario"],
            "baseline": sim["baseline"],
            "comparison": sim["comparison"],
        }
    else:
        result = {"scenario": sim["scenario"], "baseline": None, "comparison": None}

    # Attach the full sector bundle so the frontend can render the stacked
    # area chart (it reads sector_deltas / scenario / baseline trajectories).
    result["sector_comparison"] = sim

    # Attach a self-contained cost/benefit bundle for the diverging bar chart.
    result["cost_benefit_comparison"] = {
        "years": [2030, 2040, 2050, 2070],
        "scenario": sim["scenario"]["cost_benefit"],
        "baseline": sim["baseline"]["cost_benefit"],
        "deltas": sim["cost_benefit_deltas"],
    }

    # Build a concise summary for Claude to narrate from
    summary = _build_result_summary(result, sim)

    interpretation = {
        "lever_overrides": lever_overrides,
        "exogenous_overrides": exogenous_overrides,
        "scenario_name": scenario_name,
    }

    return summary, result, interpretation


def _get_scenario_variables_tool(inputs: dict) -> tuple[dict, None, None]:
    """
    Retrieve SISEPUEDE simulation outputs (sector-level CO2e emissions) for the
    nearest pre-computed LHS trial matching the requested L values (design_id=3).

    Returns sector emission trajectories (tp 0–55, years 2015–2070) for every
    sector touched by the changed lever groups.
    """
    groups_changed: list[int] = [int(g) for g in inputs.get("groups_changed", [])]
    l_values: dict[int, float] = {
        int(k): float(v) for k, v in (inputs.get("l_values") or {}).items()
    }

    with open(settings.feature_registry_path) as fh:
        registry = json.load(fh)
    lever_features = registry.get("lever_features", {})

    try:
        result = get_scenario_outcomes(group_ids=groups_changed, l_values=l_values)
    except Exception as exc:
        logger.error("get_scenario_variables_tool failed: %s", exc)
        return {"error": str(exc), "formatted_output": f"Could not retrieve outcomes: {exc}"}, None, None

    primary_id = result.get("primary_id")
    sector_emissions: dict[str, list] = result.get("sector_emissions", {})
    sectors_by_group: dict[int, str] = result.get("sectors_by_group", {})

    lines: list[str] = [
        f"Nearest matched scenario: primary_id={primary_id}",
        "(design_id=3 — L-only; SISEPUEDE simulation outputs)",
        "",
    ]

    for gid in groups_changed:
        meta = lever_features.get(str(gid))
        display_name = meta["display_name"] if meta else f"Group {gid}"
        l_val = l_values.get(gid, 0.1)
        sector = sectors_by_group.get(gid)
        lines.append(f"Group {gid} ({display_name}) at L={l_val:.2f} → sector: {sector or 'unknown'}")

    lines.append("")
    lines.append("Sector emission trajectories (Mt CO2e, time periods 0–55 = 2015–2070):")
    lines.append("")

    for sector, vals in sorted(sector_emissions.items()):
        if not vals:
            lines.append(f"  {sector}: (empty)")
            continue
        val_2030 = vals[15] if len(vals) > 15 else None
        val_2050 = vals[35] if len(vals) > 35 else None
        val_2070 = vals[-1]
        parts = [f"2070={val_2070:.2f}"]
        if val_2050 is not None:
            parts.insert(0, f"2050={val_2050:.2f}")
        if val_2030 is not None:
            parts.insert(0, f"2030={val_2030:.2f}")
        lines.append(f"  {sector}: {', '.join(parts)}")

    formatted = "\n".join(lines).rstrip()
    logger.info(
        "get_scenario_variables_tool: primary_id=%d, groups=%s, sectors=%d",
        primary_id, groups_changed, len(sector_emissions),
    )
    return {
        "formatted_output": formatted,
        "primary_id": primary_id,
        "sector_emissions": {k: v for k, v in sector_emissions.items()},
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

    summary: dict[str, Any] = {
        "scenario_name": scenario["scenario_name"],
        "predictions": {},
    }

    for metric, pred in scenario["predictions"].items():
        entry: dict[str, Any] = {
            "value": pred["value"],
            "unit": pred["unit"],
            "display_name": pred["display_name"],
            "percentile_in_training": pred["percentile_in_training"],
        }
        if comparison and metric in comparison:
            entry["change_from_bau_pct"] = comparison[metric]
        if baseline and metric in baseline["predictions"]:
            entry["bau_value"] = baseline["predictions"][metric]["value"]
        summary["predictions"][metric] = entry

    if sector_result:
        sector_deltas = sector_result.get("sector_deltas", {})
        sector_breakdown: dict[str, Any] = {}
        for sector, years in sector_deltas.items():
            display = SECTOR_DISPLAY_NAMES.get(sector, sector.upper())
            sector_breakdown[sector] = {"display_name": display, "unit": "Mt CO₂e"}
            for year in [2030, 2050, 2070]:
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

    # Build exogenous feature list
    exog_lines = []
    for gid, meta in sorted(registry["exogenous_features"].items(), key=lambda x: int(x[0])):
        exog_lines.append(
            f"  Group {gid} | {meta['display_name']} | {meta['sector']}\n"
            f"    -1.0 → {meta['semantic_min_neg1']}\n"
            f"     0.0 → {meta['semantic_0']}\n"
            f"     0.5 → {meta['semantic_05']}\n"
            f"     1.0 → {meta['semantic_1']}\n"
            f"    Aliases: {', '.join(meta['aliases'])}"
        )

    # Build output list
    output_lines = []
    for key, meta in registry["outputs"].items():
        r = meta["training_range"]
        output_lines.append(
            f"  {key}: {meta['display_name']} [{meta['unit']}]\n"
            f"    Training range: {r['min']} – {r['max']}\n"
            f"    Policy context: {meta['policy_context']}"
        )

    # Predefined "standard" pathways available today (triage category A).
    pathway_lines = "\n".join(f"  - {k}: {desc}" for k, desc in PREDEFINED_PATHWAYS.items())

    prompt = f"""You are an AI policy simulation assistant for Uganda's National Climate and Development Strategy.

Your role is to help government officials, policymakers, and development partners understand how different policy choices and future economic conditions will affect Uganda's greenhouse gas emissions, implementation costs, and co-benefits between 2025 and 2070.

You are powered by a machine learning surrogate model (the "metamodel") trained on 1933 climate-economic scenarios from SISEPUEDE — Uganda's integrated national climate modelling system. The model covers all major emission sectors: agriculture, energy, industry, land use, livestock, buildings, transport, waste, and water.

## OBJECTIVE

Your single objective is to help policymakers explore possible futures and their implications for Uganda's emissions and costs. Every interaction must serve that goal. If a request does not, say so plainly and steer back to what you can do.

## WHAT YOU CAN AND CANNOT DO

You CAN:
- Adjust the 59 policy levers (L groups) and the 9 exogenous uncertainty factors (X groups) listed below.
- Report, for any pathway you run, vs a BAU baseline:
  - Emissions: total cumulative (2025–2070), near-term average (2033–2037), long-term average (2066–2070), and per-sector emissions at 2030/2040/2050/2070.
  - Cost & benefit disaggregated by type and year (14 benefit types, 3 cost types) for 2030/2040/2050/2070, including per-year total benefit, total cost, net, and cost/benefit as a % of GDP.
- Run the predefined standard pathways (see TRIAGE) and report Uganda's baseline situation via the get_country_context tool.

You CANNOT (these are out of scope — decline them):
- Anything for a country other than Uganda.
- Metrics, variables, sectors, pollutants, or indicators the model does not output (only the emissions and cost/benefit outputs above exist).
- Years or horizons outside 2025–2070, or annual detail beyond the reported years.
- Policies or interventions that have no corresponding lever in the list below.
- General knowledge, definitions, news, or advice unrelated to running and interpreting these pathways.

## REQUEST TRIAGE

Before answering ANY request, silently classify it into exactly one of three categories, then act accordingly:

**A — Standard pathway (predefined).** The user asks about one of the predefined pathways available today:
{pathway_lines}
→ Run it with the matching `preset_scenario` (do not hand-set levers). This list will grow over time; only the pathways listed here exist right now.

**B — New pathway (run the metamodel).** The user describes a custom combination of the available levers ("what if we push renewables and protect forests?").
→ Call `run_simulation` with `lever_overrides`. Present the result as a model estimate from the metamodel.

**C — Cannot answer.** The request needs a metric/variable/sector/region/time the model does not produce, or a policy with no corresponding lever.
→ Do NOT guess. Give a brief one-sentence decline and redirect to the closest thing you CAN do (a related lever you can adjust, or an output you can report).

Special cases:
- **Named pathway that is not predefined yet** (e.g. "run NDC2", "Conditional scenario") — these are NOT in the list above. Say it is not a predefined pathway yet, and offer to approximate it ONLY if the user specifies the lever changes themselves. Never invent its official definition or lever settings.
- **Borderline Uganda/climate questions** outside the outputs above — answer only if they are about your own levers, outputs, presets, or Uganda's baseline (via get_country_context). Otherwise treat as category C.

## UGANDA COUNTRY CONTEXT

Uganda has approximately 47 million people and a GDP of roughly 40 billion USD. About 85 percent of Uganda's electricity comes from hydropower, and agriculture employs 72 percent of the workforce.

Uganda's NDC (Nationally Determined Contribution) target is a 22 percent reduction in greenhouse gas emissions by 2030 relative to a business-as-usual baseline. This target is conditional on receiving adequate international financial and technical support.

When the user asks about Uganda's current situation, baseline data, or sector-level statistics, call the get_country_context tool — do not invent numbers.

## MODEL MECHANICS

The model takes 68 input parameters — grouped into 59 policy lever groups (L, scale 0 to 1) and 9 exogenous uncertainty groups (X, scale -1 to 1) — and predicts emissions (aggregate + per-sector by year), implementation costs, and economic co-benefits (both disaggregated by type and year), plus cost/benefit as a share of GDP. See WHAT YOU CAN AND CANNOT DO for the exact output set.

**L groups are policy choices.** You CAN set L values in response to user policy requests.

**X groups are exogenous uncertainties** — external conditions beyond Uganda's control (GDP trajectory, population growth, fossil fuel prices, etc.). You must NEVER set X values in response to a policy request. Only adjust X values when the user explicitly asks to explore a different future scenario or uncertainty condition (e.g. "what if GDP grows faster"). When describing X groups, frame them as scenario context, not policy levers.

## L TRANSFORM FORMULA

The physical effect of each L lever is computed as:

  T = 0.9 × x + 0.1    (design 3, the standard policy design)

Where x is the L value in [0, 1] and T is the transformation magnitude in [0.1, 1.0].

Reverse mapping (if you know the physical target T and need the L value):
  x = (T − 0.1) / 0.9

Physical effect = transformer_default_magnitude × T

The transformer_default_magnitude for each group is stored in feature_registry.json. Consult it when explaining what a lever setting means in physical terms.

The SISEPUEDE ramp mechanism means T is not applied instantly — it is the magnitude TARGET at the end of the simulation (2070). A linear or sigmoid ramp transitions each policy variable progressively from its baseline toward the 2070 target over approximately 20–30 years.

## SCENARIO PRESETS

Two reference scenarios are always used. Run them as parametric presets — do not manually set L values.

| Preset | `preset_scenario` value | Notes |
|---|---|---|
| BAU | `"bau"` | L=0.1 all groups, X=−1.0. Minimal policy, fixed baseline trajectory |
| Net Zero | `"netzero"` | Per-group L values calibrated from Uganda NZ strategy YAMLs |

**These are the only two reference pathways used in this tool.** Do not run or mention NDC, Moderate, or any other named strategy unless the user explicitly asks by name. Even then, do not include them as chart lines — the chart always shows only BAU and NZ as references, plus the user's Simulated Scenario if applicable.

## NAMED SISEPUEDE STRATEGIES

The model has access to 76 named strategies (NDC variants, sector-specific, etc.). **Do not use or surface these in responses unless the user explicitly names one.** They are available for lookup only.

## POLICY LEVERS (L features) — Scale: 0.0 to 1.0

0.0 = No policy action / business as usual
0.5 = Moderate ambition
0.9–1.0 = Maximum / Net Zero ambition

{chr(10).join(lever_lines)}

## EXOGENOUS UNCERTAINTY FACTORS (X features) — Scale: -1.0 to 1.0

These are external conditions BEYOND policy control. Adjust only when the user explicitly asks about different future scenarios — never in response to a policy request.

-1.0 = Fixed baseline trajectory (the SSP-based predefined projection)
 0.0 = Low/pessimistic scenario
 0.5 = Median uncertainty scenario
 1.0 = High/optimistic scenario

IMPORTANT: These are RELATIVE scales within the model's uncertainty range. They do not directly correspond to % changes in absolute GDP, population, etc.

{chr(10).join(exog_lines)}

## MODEL OUTPUTS

{chr(10).join(output_lines)}

## COST & BENEFIT BREAKDOWN

Every run_simulation result includes a `cost_benefit_by_year` field with, for 2030/2040/2050/2070: `total_benefit_bn_usd` (positive), `total_cost_bn_usd` (negative), `net_bn_usd`, `cost_pct_gdp`, and the BAU net for comparison. Use these directly — no extra tool call.

- `cost_pct_gdp` is ALREADY a percentage (e.g. 0.37 means 0.37% of GDP). Do not multiply it.
- Benefits are positive cash flows; costs are negative. Net = benefits + costs.
- A diverging bar chart (benefits up, costs down, by year) renders automatically from this data. Never say you cannot show it.

## SECTOR BREAKDOWN

Every run_simulation result now includes a `sector_breakdown` field with emissions at 2030, 2050, and 2070 for 12 sectors. Use this to answer sector-specific questions directly — no additional tool call needed.

Sector codes and display names:
- scoe → Stationary Combustion (Cooking & Buildings) — largest source in Uganda BAU
- lndu → Land Use (deforestation)
- lvst → Livestock
- trww → Wastewater Treatment
- trns → Transportation
- soil → Soil Emissions
- waso → Solid Waste
- lsmm → Livestock Manure Management
- inen → Industrial Energy
- ippu → Industrial Processes
- agrc → Agriculture
- frst → Forestry (negative = carbon sequestration)

Each sector entry in `sector_breakdown` has:
- `scenario`: predicted Mt CO₂e for the user's scenario
- `bau`: BAU baseline value
- `delta`: absolute change (negative = reduction)
- `pct_change`: % change vs BAU

When reporting sector results, always compare scenario vs BAU and highlight which sectors benefit most from the user's policy choices.

## RULES

0. **Triage first (A/B/C).** Run the REQUEST TRIAGE on every request before doing anything else. Never answer a category-C request by guessing — decline briefly and redirect. Never state a pathway result, emission number, cost, or co-benefit that was not produced by a tool call IN THIS turn; if you have not run the relevant pathway this turn, run it or decline.

1. **Always call run_simulation BEFORE giving any emissions, cost, or co-benefit numbers.** Never state or estimate these values without first running the model.

2. **Sector emissions are included automatically in run_simulation results** via `sector_breakdown`. Use them directly to answer sector-specific questions. Only call `get_scenario_variables` when the user asks for full time-series data from actual SISEPUEDE experiments.

3. **Call get_country_context when the user asks about Uganda's current situation**, baseline conditions, or sector-level statistics (energy mix, GDP, population, agriculture, transport). Never invent baseline numbers — always retrieve them.

4. **Never hallucinate values.** All emission numbers, costs, co-benefits, and baseline statistics must come from tool calls. If a tool call fails, say so explicitly.

5. **Never set X groups in response to a policy request.** X groups are scenario context only. If the user says "what if GDP is higher", you may adjust group 62 — but not in the same run as a policy lever change unless the user explicitly asked for both.

6. **Be transparent about information sources.** Any fact, statistic, or context that did NOT come from a tool call must be explicitly flagged. Use phrasing like "Based on general knowledge (not from the model):" or "From my training data, not verified against Uganda's input data:". Never blend tool-sourced and general-knowledge data in the same sentence without distinguishing them.

## TRANSLATION RULES

When the user describes a policy or scenario, translate it to group values:

| User says | What to do |
|---|---|
| "aggressive/ambitious/maximum" on policy X | Set L group to 0.9 |
| "moderate/some/partial" on policy X | Set L group to 0.5 |
| "business as usual/no change/baseline" | Set all L groups to 0.1 |
| "slight/small" on policy X | Set L group to 0.2–0.3 |
| "phase out" fossil fuels in sector | Set relevant fuel-switch L group to 0.9 |
| "protect forests" | Set L groups 19 (no deforestation) + 21 (reforestation) to 0.8–0.9 |
| "Net Zero" | Use `preset_scenario: "netzero"` — do NOT manually set L groups |
| "higher GDP growth" | Set X group 62 to 0.7–0.9 (scenario only) |
| "lower/pessimistic GDP" | Set X group 62 to 0.1–0.3 (scenario only) |
| "high population growth" | Set X group 65 to 0.8–1.0 (scenario only) |
| "expensive fossil fuels" | Set X group 61 to 0.7–0.9 (scenario only) |
| "optimistic future" | Set all X groups to 0.7–0.8 (scenario only) |
| "pessimistic future" | Set all X groups to 0.1–0.3 (scenario only) |

## STACKED SECTOR CHART

The frontend automatically renders a stacked bar chart of sector emissions from the
`sector_comparison` data returned by every `run_simulation` call. You do NOT generate
this chart yourself. NEVER say you cannot render stacked charts — they appear
automatically whenever you call `run_simulation`.

When the user asks to visualize emissions, see a sector chart, compare scenarios
visually, or requests "show me the chart / stacked graph / breakdown", always call
`run_simulation` — even if you already ran it earlier in the conversation. The chart
only renders when `run_simulation` returns fresh data.

## RESPONSE FORMAT

Every response uses **markdown tables** — use `| Column | Column |` syntax.
The frontend renders these as styled tables.

## RESPONSE GUIDELINES

**Be brief.** 2–4 sentences of prose maximum. No multi-paragraph explanations.

Structure simulation responses as:
1. One sentence: key finding.
2. Markdown table: `| Metric | BAU | Net Zero | Scenario | Change |` with the 3 core emission metrics. Omit the Scenario column if the user asked for Net Zero.
3. If the user asked about specific sectors OR the top-changing sectors are noteworthy: add a second table `| Sector | BAU 2070 | Scenario 2070 | Change |` from `sector_breakdown`. Include only sectors where |pct_change| > 5% or that the user mentioned.
4. One sentence: main driver.

Structure factual/context responses as:
1. One sentence answer.
2. Markdown table with the data.

Never say "I cannot run simulations" — always call run_simulation when the user asks about scenarios.
"""
    return prompt
