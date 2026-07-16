FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# The model.pkl and the SISEPUEDE data CSVs are NOT baked into the image — they
# are pulled from S3 at boot by entrypoint.sh (backend/scripts/download_assets.py)
# to the paths below. Only code + small JSON sidecars ship in the image.
COPY backend/  ./backend/
COPY frontend/ ./frontend/
COPY run.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV HOST=0.0.0.0 \
    PORT=8080 \
    RELOAD=false \
    MODEL_SECTOR_PATH=/app/model.pkl \
    SSP_DATA_DIR=/app/data/ssp \
    LOG_DIR=/app/logs
# Mount a Railway persistent Volume at LOG_DIR so interactions.jsonl survives
# restarts/redeploys (the container filesystem is otherwise ephemeral).

EXPOSE 8080

# entrypoint.sh downloads assets from S3, then execs uvicorn on $PORT.
CMD ["./entrypoint.sh"]
