# ==========================================
# Stage 1: Build the React Frontend
# ==========================================
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Runtime
# ==========================================
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Media Downloader Pro"
LABEL description="Production-grade self-hosted media downloader powered by yt-dlp and FFmpeg"

# Install runtime system packages: FFmpeg, curl (for healthcheck), ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version | head -n 1

# Create non-root system user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -d /app -s /usr/sbin/nologin appuser

# Prepare app and persistent data directories
RUN mkdir -p /app/backend /app/frontend/dist /data/downloads /data/temp && \
    chown -R appuser:appuser /app /data

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy built frontend from stage 1
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist /app/frontend/dist

# Copy backend application source
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    APP_PORT=8080 \
    APP_HOST=0.0.0.0 \
    DOWNLOAD_DIR=/data/downloads \
    TEMP_DIR=/data/temp

# Switch to non-root user
USER appuser

EXPOSE 8080

# Healthcheck monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
