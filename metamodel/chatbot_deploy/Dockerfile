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
    MODEL_SECTOR_PATH=/data/model.pkl \
    SSP_DATA_DIR=/data/ssp \
    LOG_DIR=/data/logs
# Mount a single Railway persistent Volume at /data. Everything that must survive
# restarts/redeploys lives under it: the S3-downloaded model + data CSVs AND the
# interaction logs (the container filesystem is otherwise ephemeral). Because
# download_assets.py is idempotent — it skips any file already present with the
# same byte size — the ~370 MB model+data download only happens on the FIRST boot;
# later boots (and serverless wake-ups) find the assets already on the volume and
# skip straight to starting the server, so cold starts are fast.

EXPOSE 8080

# entrypoint.sh downloads assets from S3, then execs uvicorn on $PORT.
CMD ["./entrypoint.sh"]
