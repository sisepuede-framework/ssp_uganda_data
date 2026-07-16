#!/usr/bin/env sh
# Container entrypoint: pull assets from S3, then start the API.
# Kept as a script (not a bare CMD) so the S3 download runs before uvicorn binds
# — the model must be on disk before the app's startup event loads it.
set -e

echo "[entrypoint] downloading model + data from S3..."
python -m backend.scripts.download_assets

# Railway (and most PaaS) inject $PORT; fall back to 8080 for local `docker run`.
echo "[entrypoint] starting uvicorn on 0.0.0.0:${PORT:-8080}"
exec uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-8080}"
