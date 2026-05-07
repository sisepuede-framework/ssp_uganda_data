# Uganda Climate Policy Chatbot
#
# Build context must be the metamodel/ directory (one level up from this file):
#
#   cd metamodel/
#   docker build -f chatbot/Dockerfile -t uganda-chatbot .
#
# The wider context is needed so the model .pkl and training .parquet files
# can be copied in from surrogate_model/ and data/training/.

FROM python:3.11-slim

WORKDIR /app

# System deps for numpy/pandas/xgboost
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying source (better layer caching)
COPY chatbot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY chatbot/backend/  ./backend/
COPY chatbot/frontend/ ./frontend/
COPY chatbot/run.py    ./run.py

# Model artifacts — baked in so startup is instant (total ~4 MB)
COPY surrogate_model/trained_models/xgb_pipeline_2025-11-12t22;19;28.194097.pkl \
     ./model.pkl
COPY data/training/training_data_w_suffix_2025-11-12t22;19;28.194097.parquet \
     ./training.parquet

# Static defaults for production — all overridable via env vars
ENV HOST=0.0.0.0 \
    PORT=8080 \
    RELOAD=false \
    MODEL_PATH=/app/model.pkl \
    TRAINING_DATA_PATH=/app/training.parquet

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
