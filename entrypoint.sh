#!/usr/bin/env sh
set -e

# Ensure data directories exist and are writable
mkdir -p "${DOWNLOAD_DIR:-/data/downloads}" "${TEMP_DIR:-/data/temp}"

export PYTHONPATH="/app/backend"
PORT="${APP_PORT:-8080}"
HOST="${APP_HOST:-0.0.0.0}"
RAW_LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_LEVEL_LOWER=$(echo "$RAW_LOG_LEVEL" | tr '[:upper:]' '[:lower:]')

echo "Starting Media Downloader Pro on ${HOST}:${PORT} with log level ${LOG_LEVEL_LOWER}..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --log-level "${LOG_LEVEL_LOWER}"
