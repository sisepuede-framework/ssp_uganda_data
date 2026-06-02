FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# model.pkl is the sector pipeline (serves both the 11 aggregate metrics and the
# 48 sector×year trajectories). Target metadata travels in
# backend/target_distributions.json, copied with backend/ — no training parquet
# is needed at runtime.
COPY backend/  ./backend/
COPY frontend/ ./frontend/
COPY run.py model.pkl ./

ENV HOST=0.0.0.0 \
    PORT=8080 \
    RELOAD=false \
    MODEL_SECTOR_PATH=/app/model.pkl

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
