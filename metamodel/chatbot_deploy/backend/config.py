"""
Configuration for the Uganda Climate Simulation Chatbot.

All settings can be overridden via environment variables or a .env file
in the chatbot/ root directory.

To add a new config value:
  1. Add a field here with a sensible default.
  2. Set the corresponding env var (e.g. CLAUDE_MODEL) in .env.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to this file's directory: metamodel/chatbot/backend/
_BACKEND_DIR = Path(__file__).parent
# Absolute path to metamodel/ root
_METAMODEL_DIR = _BACKEND_DIR.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Suppress Pydantic warning about model_ prefix on our path fields
        protected_namespaces=("settings_",),
    )

    # ── Anthropic ──────────────────────────────────────────────────────────
    # Required at runtime. Set in .env file: ANTHROPIC_API_KEY=sk-ant-...
    anthropic_api_key: str = ""
    # Model to use for the Claude agent.
    # Recommended: claude-sonnet-4-6 (best reasoning/cost balance for this use case)
    claude_model: str = "claude-sonnet-4-6"
    # Max tokens Claude is allowed to generate per turn
    claude_max_tokens: int = 4096

    # ── Model paths ────────────────────────────────────────────────────────
    # Defaults resolve relative to the repo for local dev.
    # In production (Docker/App Runner) override via env vars:
    #   MODEL_PATH=/app/model.pkl
    #   TRAINING_DATA_PATH=/app/training.parquet
    model_path: Path = (
        _METAMODEL_DIR
        / "surrogate_model"
        / "trained_models"
        / "xgb_pipeline_2025-11-12t22;19;28.194097.pkl"
    )
    training_data_path: Path = (
        _METAMODEL_DIR
        / "data"
        / "training"
        / "training_data_w_suffix_2025-11-12t22;19;28.194097.parquet"
    )
    model_sector_path: Path = (
        _METAMODEL_DIR
        / "surrogate_model_sector"
        / "trained_models"
        / "xgb_pipeline_sector_independent_2025-11-12t22;19;28.194097.pkl"
    )
    training_data_sector_path: Path = (
        _METAMODEL_DIR
        / "data"
        / "training"
        / "training_data_sector_2025-11-12t22;19;28.194097.parquet"
    )
    feature_registry_path: Path = _BACKEND_DIR / "feature_registry.json"

    # ── AWS / S3 ───────────────────────────────────────────────────────────
    # Key/secret are optional — leave blank to use the default credential chain
    # (~/.aws/credentials, SSO, instance role, etc.)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    # Named AWS profile (e.g. "alexa" for SSO). Leave blank to use the
    # default credential chain (env vars, instance role, etc.).
    aws_profile: str = ""
    # S3 bucket and run ID for SISEPUEDE model inputs / variable lookups
    s3_bucket: str = "sisepuede-data"
    s3_run_id: str = "sisepuede_run_2025-11-12T22:19:28.194097"

    # ── Server ─────────────────────────────────────────────────────────────
    # Local dev defaults. Production (Docker) overrides via env:
    #   HOST=0.0.0.0  PORT=8080  RELOAD=false
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    # ── CORS ───────────────────────────────────────────────────────────────
    # Origins allowed to call the API. In development, the frontend is served
    # from the same origin (via FastAPI static files), so this is permissive.
    allowed_origins: list[str] = ["*"]


settings = Settings()
