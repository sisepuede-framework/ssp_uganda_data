"""country_context: Uganda's modelled baseline. Identical in v0 and v1; wraps the deployed service."""

from backend.rdm.tools.common import ToolError

TOPICS = ("energy_mix", "gdp", "population", "agriculture", "transport")
# Source-label test, "after" condition (docs/preregistration_source_labels.md): says what the gdp numbers describe.
GDP_LABEL = ("These values are SISEPUEDE's base future (future 0). It is not one of the experiment's runs, and its GDP "
             "is above the 90th percentile of the runs in 2040 and 2050. Do not read it as the middle of the futures "
             "explored.")


def country_context(topic: str) -> dict:
    if topic not in TOPICS:
        raise ToolError("BAD_TOPIC", f"topic must be one of {TOPICS}")
    from backend.services.context import ContextUnavailable, get_country_context
    try:
        text = get_country_context(topic)
        return {"topic": topic, "text": text + ("\n\n" + GDP_LABEL if topic == "gdp" else ""),
                "note": "Modelled baseline assumptions (2025–2050), not observed present-day statistics."}
    except ContextUnavailable as e:
        raise ToolError("CONTEXT_UNAVAILABLE", str(e))
