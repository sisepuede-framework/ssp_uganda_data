"""
FastAPI Application
====================
Defines all HTTP endpoints and serves the frontend static files.

Endpoints
---------
GET  /                          → Serves the chat UI (frontend/index.html)
GET  /api/health                → Health check + model status
GET  /api/features              → Returns full feature registry (for UI rendering)
POST /api/simulate              → Direct simulation (no LLM, for programmatic use)
POST /api/chat                  → LLM agent: translates message → simulation → narrative

Adding a new endpoint
---------------------
1. Define your route function here.
2. Use the predictor via `get_sector_predictor()` or the agent via `agent.run()`.
3. Add a Pydantic schema in schemas.py if you have new request/response shapes.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend import schemas
from backend.services import agent
from backend.services.predictor import get_sector_predictor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_LOG_FILE = Path(__file__).parent.parent / "logs" / "interactions.jsonl"


def _log_interaction(user_message: str, result: dict, latency: float) -> None:
    sim = result.get("simulation") or {}
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_message": user_message,
        "tool_calls": result.get("tool_calls_log", []),
        "lever_overrides": (result.get("scenario_interpretation") or {}).get("lever_overrides"),
        "exogenous_overrides": (result.get("scenario_interpretation") or {}).get("exogenous_overrides"),
        "preset_scenario": (result.get("scenario_interpretation") or {}).get("preset_scenario"),
        "simulation_outputs": {
            **{
                k: v.get("value")
                for k, v in (sim.get("scenario") or {}).get("predictions", {}).items()
            },
            **{
                f"emission_{sector}_yr{year}": val
                for sector, traj in (
                    (sim.get("sector_comparison") or {})
                    .get("scenario", {})
                    .get("sector_trajectories", {})
                    .items()
                )
                for year, val in traj.items()
                if year != 2019
            },
        },
        "reply_snippet": result.get("reply", "")[:300],
        "latency_s": round(latency, 2),
    }
    try:
        _LOG_FILE.parent.mkdir(exist_ok=True)
        with open(_LOG_FILE, "a") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("Failed to write interaction log: %s", exc)

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Uganda Climate Simulation Chatbot",
    description=(
        "AI-powered chatbot for exploring Uganda's climate policy scenarios "
        "using a trained XGBoost surrogate model of SISEPUEDE."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: load model once ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Pre-load the surrogate model at startup to avoid cold-start latency."""
    logger.info("Loading surrogate model...")
    try:
        get_sector_predictor()
        logger.info("Surrogate model loaded and ready.")
    except Exception as e:
        logger.error("Failed to load surrogate model: %s", e)
        # Don't crash the app — health check will report unhealthy


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
def health_check():
    """Returns server status and whether the model is loaded."""
    try:
        predictor = get_sector_predictor()
        model_ok = predictor is not None
    except Exception:
        model_ok = False

    return {
        "status": "ok" if model_ok else "degraded",
        "model_loaded": model_ok,
        "model_run_id": settings.model_sector_path.stem.replace("xgb_pipeline_sector_independent_", ""),
        "region": "Uganda",
    }


@app.get("/api/features", tags=["Model"])
def get_features():
    """
    Returns the full feature registry: all 68 groups with display names,
    descriptions, sectors, and value semantics.
    Use this to dynamically render sliders or dropdowns in the UI.
    """
    predictor = get_sector_predictor()
    return predictor.get_feature_info()


_BAU_PATH = Path(__file__).parent / "bau_trajectory.json"


@app.get("/api/bau", tags=["Model"])
def get_bau():
    """
    Returns the pre-computed BAU (Business as Usual) baseline prediction.
    All 11 output metrics at L=0.1 / X=-1.0 for every group.

    This file is generated by scripts/precompute_bau.py and must be present
    before the server starts.  Re-run that script after any model retrain.
    """
    if not _BAU_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "BAU baseline not found. "
                "Run scripts/precompute_bau.py to generate bau_trajectory.json."
            ),
        )
    with open(_BAU_PATH) as fh:
        return json.load(fh)


@app.post("/api/simulate", response_model=schemas.SimulationResponse, tags=["Model"])
def simulate(request: schemas.SimulationRequest):
    """
    Direct simulation endpoint — no LLM involved.
    Provide group_id overrides and receive predictions for all 11 metrics.
    Useful for programmatic exploration or building custom UIs.

    Example body:
    {
        "scenario_name": "High Renewables",
        "lever_overrides": {"8": 0.9, "41": 0.8, "19": 0.85},
        "exogenous_overrides": {"62": 0.7},
        "preset_scenario": "bau",
        "compare_to_baseline": true
    }
    """
    predictor = get_sector_predictor()
    try:
        if request.compare_to_baseline:
            sim = predictor.predict_comparison(
                lever_overrides=request.lever_overrides,
                exogenous_overrides=request.exogenous_overrides,
                preset_scenario=request.preset_scenario,
                scenario_name=request.scenario_name,
            )
            result = {
                "scenario": sim["scenario"],
                "baseline": sim["baseline"],
                "comparison": sim["comparison"],
                "sector_comparison": sim,
                "cost_benefit_comparison": {
                    "years": [2030, 2040, 2050, 2070],
                    "scenario": sim["scenario"]["cost_benefit"],
                    "baseline": sim["baseline"]["cost_benefit"],
                    "deltas": sim["cost_benefit_deltas"],
                },
            }
        else:
            scenario = predictor.predict(
                lever_overrides=request.lever_overrides,
                exogenous_overrides=request.exogenous_overrides,
                preset_scenario=request.preset_scenario,
                scenario_name=request.scenario_name,
            )
            result = {"scenario": scenario, "baseline": None, "comparison": None}
        return result
    except Exception as e:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=schemas.ChatResponse, tags=["Agent"])
def chat(request: schemas.ChatRequest):
    """
    LLM agent endpoint.
    Send the full conversation history and receive a natural-language response.
    The agent will automatically run simulations when needed.

    The client is responsible for maintaining conversation history and
    sending it with each request (stateless backend).
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    try:
        t0 = time.time()
        result = agent.run(
            messages=[m.model_dump() for m in request.messages],
            locked_overrides=request.locked_overrides,
        )
        latency = time.time() - t0
        logger.info("Agent responded in %.2fs", latency)

        user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        _log_interaction(user_msg, result, latency)

        return schemas.ChatResponse(
            reply=result["reply"],
            simulation=result.get("simulation"),
            scenario_interpretation=result.get("scenario_interpretation"),
        )
    except Exception as e:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve frontend ────────────────────────────────────────────────────────────
# The frontend directory is at metamodel/chatbot/frontend/
# Mount it last so it does not shadow API routes.

_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend directory not found at %s — UI will not be served.", _FRONTEND_DIR)
