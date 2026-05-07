# Architecture & Technical Decisions

## System Overview

```
User (Browser)
    │ HTTP POST /api/chat  (full conversation history)
    ▼
FastAPI Backend  (backend/app.py)
    │
    ├── Agent Service  (backend/services/agent.py)
    │     │  Builds system prompt from feature_registry.json
    │     │  Calls Claude claude-sonnet-4-6 with tool definitions
    │     │  Claude calls run_simulation tool 1–N times
    │     ▼
    │   Predictor Service  (backend/services/predictor.py)
    │     │  Loads XGBoost .pkl model at startup
    │     │  Builds feature vector from group_id → value overrides
    │     │  Returns 11 predictions + percentile stats
    │     ▼
    │   Feature Registry  (backend/feature_registry.json)
    │     │  Maps group_id to column names, descriptions, aliases
    │     │  Single source of truth — edit to change Claude's knowledge
    │     ▼
    └── Returns: { reply, simulation, scenario_interpretation }
    │
    ▼
Frontend (frontend/)
    │  Pure HTML + CSS + JS — no framework, no build step
    │  Renders chat bubbles + metrics grid + Chart.js bar chart
    └── Maintains conversation history client-side (stateless server)
```

## Key Design Decisions

### 1. Stateless Backend
The server holds no session state. The full conversation history is sent by the client with every request. This makes the backend horizontally scalable (multiple instances behind a load balancer) with no shared state.

### 2. Feature Registry as JSON
All 68 feature group descriptions, semantics, and aliases live in `backend/feature_registry.json`. This is the single source of truth for:
- What Claude knows about each feature (system prompt is generated from it)
- What the UI knows about features (for rendering sliders/labels)
- What the predictor knows about column mappings

**To update feature descriptions:** Edit `feature_registry.json` — no code changes needed.

### 3. Column Order Authority
The XGBoost model expects features in a specific column order. The predictor reads this order from the training parquet at startup (not hardcoded). If the model is retrained, `predictor.py` adapts automatically as long as the registry `training_column` names are updated.

### 4. Agentic Loop with Tool Calling
Claude can call `run_simulation` multiple times per turn (e.g., to compare two scenarios). The loop in `agent.py` continues until Claude's stop_reason is `end_turn` (max 5 iterations as a safety limit).

### 5. Pure HTML/JS Frontend
No React, Vue, or build step required. Any team member can edit the UI directly. Chart.js is loaded from CDN. The backend serves the frontend via FastAPI's StaticFiles mount.

## Input Value Semantics

### L features (Policy Levers) — groups 1–59 — scale [0.0, 1.0]
- `0.0` = No policy intervention (business as usual)
- `0.1` = BAU default used for baseline comparisons
- `0.5` = Moderate ambition
- `0.9` = Near-maximum / Net Zero ambition
- `1.0` = Theoretical maximum (rarely seen in training data for some designs)

### X features (Exogenous Uncertainties) — groups 60–68 — scale [-1.0, 1.0]
- `-1.0` = Fixed baseline trajectory (the SSP-predefined projection; used in design_id=3 training data)
- `0.0` = Low/pessimistic end of the LHS uncertainty distribution
- `0.5` = Median uncertainty scenario
- `1.0` = High/optimistic end of the LHS uncertainty distribution

**Why are X features in [-1, 1] instead of [0, 1]?**
The training data mixes design_id=3 runs (X fixed at -1.0, representing "no uncertainty") with other designs where X varies in [0, 1]. The -1.0 sentinel means "use the predefined baseline trajectory for this variable." Values in [0, 1] represent draws from the Latin Hypercube Sampling distribution of possible futures.

## Design IDs — How They Affect the Model

The training data was generated from 5 experimental designs:

| design_id | L varies | X varies | L transformation | Note |
|-----------|----------|----------|-----------------|------|
| 0 | No | Yes | Fixed at 1.0 | Net Zero policies, X uncertainty |
| 1 | Yes | Yes | [0.25, 1.0] | Moderate range |
| 2 | Yes | Yes | [0.25, 1.0] | Biased toward extremes |
| 3 | Yes | No | [0.10, 1.0] | X fixed at -1.0 (baseline) |
| 4 | Yes | Yes | [0.00, 1.0] | Full range for both |

**design_id is NOT a model feature.** The XGBoost model was trained on the combined data from all designs. Any combination of L ∈ [0, 1] and X ∈ [-1, 1] is valid input. The mixing of designs gives the model broader training coverage.

## Known Limitations

1. **Uganda only** — Model cannot be applied to other regions.
2. **Fixed time periods** — Predictions are for 2033–37, 2066–70, and 2025–70 aggregates only.
3. **Grouped variables** — Each group_id controls multiple SISEPUEDE variables that move together. Individual variable control is not possible.
4. **Relative X scales** — "GDP" is a relative position in the uncertainty range, not an absolute USD figure.
5. **No uncertainty quantification** — XGBoost gives point estimates. No confidence intervals.
6. **Truncated column names** — Groups 3, 8, 9, 57 have incomplete names in the training data (source data issue). Their policies are identified from transformation codes instead.
7. **Static model** — The model reflects 2025-era Uganda data. It does not update with new statistics.
8. **Out-of-distribution risk** — Extreme combinations of levers that were not well-represented in training may produce unreliable predictions.

## Adding a New Model Version

1. Retrain the XGBoost pipeline using `surrogate_model/model_training.ipynb`.
2. Update `MODEL_PATH` and `TRAINING_DATA_PATH` in `backend/config.py` (or `.env`).
3. If feature columns changed, update `training_column` fields in `feature_registry.json`.
4. Restart the server.

## Extending the Agent

To add a new tool (e.g., `get_feature_importance`, `plot_scenario`):
1. Add the tool definition to `TOOLS` list in `backend/services/agent.py`.
2. Add a handler in `_execute_tool_call()`.
3. The agent will automatically use it when appropriate.

## Deployment Notes

For production deployment:
1. Set `RELOAD=False` in `.env`.
2. Set specific `ALLOWED_ORIGINS` to your frontend domain.
3. Run behind a reverse proxy (nginx) with HTTPS.
4. Consider rate-limiting the `/api/chat` endpoint (each call uses Anthropic API credits).
5. The model PKL file (~2.5 MB) is loaded at startup — keep the server warm.
