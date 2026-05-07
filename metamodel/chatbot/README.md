# Uganda Climate Policy Simulator — Chatbot

An AI-powered chatbot for exploring Uganda's climate policy scenarios, built on top of a trained XGBoost surrogate model of the SISEPUEDE climate-economic system.

## What it does

Policy makers and analysts can describe scenarios in plain English ("What happens if Uganda protects all forests and electrifies transport?") and receive:
- Predicted emissions for 2025–2070 (cumulative and near/long-term annual)
- Implementation costs (absolute and as % of GDP)
- Economic co-benefits (air quality, health, congestion)
- Comparison against a Business as Usual baseline

## Prerequisites

- Python 3.11+
- Conda environment `ssp_uganda` (or any env with the packages below)
- Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))
- The trained model file at `../surrogate_model/trained_models/xgb_pipeline_2025-11-12t22;19;28.194097.pkl`
- The training parquet at `../data/training/training_data_w_suffix_2025-11-12t22;19;28.194097.parquet`

## Setup

```bash
# 1. Navigate to this directory
cd metamodel/chatbot

# 2. Activate the Uganda metamodel conda environment (has xgboost + pandas)
conda activate uganda_metamodel_env

# 3. Install additional dependencies (fastapi, anthropic, etc.)
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the server
python run.py
```

Open your browser at **http://127.0.0.1:8000**

API docs are at **http://127.0.0.1:8000/api/docs**

## Project structure

```
chatbot/
├── README.md               ← You are here
├── ARCHITECTURE.md         ← Technical decisions, input semantics, limitations
├── .env.example            ← Environment variable template
├── requirements.txt        ← Python dependencies
├── run.py                  ← One-command startup
│
├── backend/
│   ├── app.py              ← FastAPI routes + frontend serving
│   ├── config.py           ← Settings (paths, model name, server config)
│   ├── schemas.py          ← Pydantic request/response models
│   ├── feature_registry.json ← ⭐ Master registry of all 68 feature groups
│   └── services/
│       ├── predictor.py    ← XGBoost model wrapper + baseline runner
│       └── agent.py        ← Claude agent: tool calling + system prompt
│
└── frontend/
    ├── index.html          ← Single-page chat UI
    ├── style.css           ← Styling (edit to rebrand)
    └── app.js              ← Chat logic + results rendering
```

## Adjusting things

### Change feature descriptions (what Claude knows about each group)
Edit `backend/feature_registry.json`. This is the single source of truth. Changes take effect on server restart.

### Change Claude's tone or translation rules
Edit the `_build_system_prompt()` function in `backend/services/agent.py`.

### Change default values (BAU baseline levels)
Edit `BAU_L_DEFAULT`, `BAU_X_DEFAULT` constants in `backend/services/predictor.py`.

### Change the UI
Edit `frontend/index.html`, `frontend/style.css`, or `frontend/app.js`. No build step required — just refresh the browser.

### Add a new API endpoint
Add a route in `backend/app.py` and a schema in `backend/schemas.py`.

### Update to a new model
See `ARCHITECTURE.md` → "Adding a New Model Version".

## API reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server + model status |
| `/api/features` | GET | Full feature registry |
| `/api/simulate` | POST | Direct simulation (no LLM) |
| `/api/chat` | POST | LLM agent (natural language → simulation) |
| `/api/docs` | GET | Interactive Swagger UI |

## Known limitations

See `ARCHITECTURE.md` for the full list. Key ones:
- **Uganda only** — results cannot be applied to other countries
- **Fixed time periods** — no year-by-year trajectories
- **Relative scales** — GDP/population X features are not absolute values
- **Point estimates** — no confidence intervals around predictions
- **Group constraints** — all variables in a group move together
