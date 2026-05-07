FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/  ./backend/
COPY frontend/ ./frontend/
COPY run.py model.pkl training.parquet ./

ENV HOST=0.0.0.0 \
    PORT=8080 \
    RELOAD=false \
    MODEL_PATH=/app/model.pkl \
    TRAINING_DATA_PATH=/app/training.parquet

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
