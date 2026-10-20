"""country_context: Uganda's modelled baseline. Identical in v0 and v1; wraps the deployed service."""

from backend.rdm.tools.common import ToolError

TOPICS = ("energy_mix", "gdp", "population", "agriculture", "transport")


def country_context(topic: str) -> dict:
    if topic not in TOPICS:
        raise ToolError("BAD_TOPIC", f"topic must be one of {TOPICS}")
    from backend.services.context import ContextUnavailable, get_country_context
    try:
        return {"topic": topic, "text": get_country_context(topic),
                "note": "Modelled baseline assumptions (2025–2050), not observed present-day statistics."}
    except ContextUnavailable as e:
        raise ToolError("CONTEXT_UNAVAILABLE", str(e))
