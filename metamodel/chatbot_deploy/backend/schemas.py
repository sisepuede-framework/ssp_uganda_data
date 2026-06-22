"""
Pydantic request/response models for the Uganda Climate Chatbot API.

These define the shape of data going into and out of every endpoint.
Adding a new field to a response: add it here AND populate it in the service.
"""

from typing import Any
from pydantic import BaseModel, Field


# ── Simulation ──────────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    """
    Direct simulation endpoint — bypasses the LLM agent.
    Useful for programmatic access or building custom UIs on top of the model.

    lever_overrides:    group_id (int 1–54) → value in [0.0, 1.0]
    exogenous_overrides: group_id (int 55–67) → value in [0.0, 1.0]
    Unspecified groups use the scenario defaults (see preset_scenario).
    """
    scenario_name: str = "Custom Scenario"
    lever_overrides: dict[int, float] = Field(default_factory=dict)
    exogenous_overrides: dict[int, float] = Field(default_factory=dict)
    # "bau" | "moderate" | "netzero"  — sets the fill value for unspecified groups
    preset_scenario: str = "bau"
    compare_to_baseline: bool = True


class PredictionResult(BaseModel):
    """Single prediction for one output metric.

    training_range / percentile_in_training are optional: this run's headline
    emission metrics are derived (sum of sectors), so they have no dedicated
    training distribution.
    """
    value: float
    unit: str
    display_name: str
    training_range: dict[str, float] | None = None  # {"min": ..., "max": ...}
    percentile_in_training: float | None = None     # 0–100: where this prediction sits


class SimulationResult(BaseModel):
    """Full result for one scenario run."""
    scenario_name: str
    feature_vector: dict[str, float]  # column_name → value used
    group_values: dict[int, float]    # group_id → value used (cleaner for display)
    predictions: dict[str, PredictionResult]


class SimulationResponse(BaseModel):
    """Response from POST /api/simulate."""
    scenario: SimulationResult
    baseline: SimulationResult | None = None
    # For each output metric: the % change from baseline
    comparison: dict[str, float] | None = None
    # Sector-level breakdown from SectorPredictor — used by the stacked area chart
    sector_comparison: dict | None = None
    # Cost/benefit disaggregated by year × type — used by the diverging bar chart
    cost_benefit_comparison: dict | None = None


# ── Chat ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str           # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """
    Request body for POST /api/chat.
    The backend maintains no session state — the full conversation history
    must be sent each turn. This keeps the backend stateless and scalable.
    """
    messages: list[ChatMessage]
    # Optional: lock certain levers to specific values before the agent runs
    locked_overrides: dict[int, float] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """
    Non-streaming response. For streaming use GET /api/chat/stream.
    The simulation field is populated only when the agent ran the model.
    """
    reply: str
    simulation: SimulationResponse | None = None
    # Metadata about what the agent decided to change
    scenario_interpretation: dict[str, Any] | None = None


# ── Features ────────────────────────────────────────────────────────────────

class FeatureInfo(BaseModel):
    """Metadata for a single feature group, suitable for UI rendering."""
    group_id: int
    feature_type: str    # "L" or "X"
    training_column: str
    display_name: str
    sector: str
    scale_min: float
    scale_max: float
    semantic_min: str
    semantic_max: str
    policy_description: str
    aliases: list[str]


class FeatureRegistryResponse(BaseModel):
    lever_features: list[FeatureInfo]
    exogenous_features: list[FeatureInfo]
