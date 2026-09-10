# Media Downloader Pro

A production-grade, self-hosted web application for media extraction and audio processing powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org). Designed for reliable containerized deployment with non-root security, real-time Server-Sent Events (SSE), automated safe updates, and an anti-slop consumer utility interface.

---

## 1. Product Overview

Media Downloader Pro provides a polished, self-hosted web interface to extract, inspect, and download video and audio streams from supported websites. It isolates yt-dlp execution inside clean architectural service layers, converts technical errors into friendly user messages, limits concurrent resource usage, and ensures that neither media files nor internal networks are exposed to SSRF attacks.

### Core Principles
- **No Demoware / No Placeholders**: Fully implemented backend and frontend with real yt-dlp execution.
- **Enterprise Security**: Strict SSRF prevention against private IP networks, cloud metadata endpoints, and loopback addresses.
- **Self-Contained Docker Architecture**: Multi-stage Debian slim build running as non-root user `appuser` (UID 10001).
- **Graceful Auto-Updates**: Non-breaking startup update checks against official PyPI/GitHub releases with offline fallback.
- **Real-Time Progress**: Live Server-Sent Events (SSE) streaming download progress, speed, ETA, and processing stages.

---

## 2. Features

- **Instant URL Analysis**:
  - Fetches thumbnail, title, uploader, duration, source site, and video/audio stream availability without downloading media.
- **Granular Quality & Format Selection**:
  - Video resolutions: Best Available, 2160p (4K), 1440p (2K), 1080p, 720p, 480p, 360p.
  - Container selection: MP4, MKV, WebM.
  - Audio extraction: MP3 (320 kbps), M4A (AAC), WAV (Lossless).
- **Real-Time Download Tracking**:
  - Dynamic progress bar, downloaded percentage, transfer speed, remaining ETA, and processing stage pill ("Queued", "Downloading", "Merging", "Completed").
- **Subprocess Cancellation**:
  - Safely terminates running jobs on demand, sends SIGTERM/SIGKILL only to the target subprocess, and purges temporary files.
- **Safe File Delivery & In-Browser Download**:
  - Path traversal protection, safe filename sanitization, and direct browser download button.
- **Download History & Management**:
  - Recent downloads drawer with direct file access and record deletion.
- **Automated Lifecycle Cleanup**:
  - Periodic background cleanup deleting expired media files and temp directories according to retention rules.
- **Theme & Accessibility**:
  - Dark / Light mode toggle with system preference detection and keyboard accessibility.

---

## 3. Technology Stack & Architecture

```
Browser (React + Vite + Tailwind CSS + Phosphor Icons)
   │
   │  REST API & Server-Sent Events (/api/jobs/{id}/events)
   ▼
FastAPI Application (Python 3.12 / Uvicorn)
   ├── SecurityService (SSRF defense, IP resolution, scheme validation)
   ├── YtDlpService (Subprocess extraction, format normalization, CLI builder)
   ├── FFmpegService (Version query, format probe)
   ├── JobManager (Queue, concurrency semaphore, cancellation, SSE broadcast)
   ├── FileService (Filename sanitization, path containment, byte formatting)
   ├── YtDlpUpdater (HTTPS update verification & non-blocking pip upgrade)
   └── CleanupService (Periodic background expired file purging)
   │
   ├── Temporary directory (/data/temp/{job_id})
   └── Final storage (/data/downloads/)
```

---

## 4. System Requirements

- **Docker**: Engine version 24.0 or newer
- **Docker Compose**: version 2.20 or newer
- **Disk Space**: At least 5 GB recommended for media storage
- **Memory**: 512 MB minimum (1 GB recommended during concurrent video transcode/merge)

---

## 5. Quick Start with Docker Compose

Deploying Media Downloader Pro takes under a minute:

```bash
# 1. Clone repository
git clone https://github.com/example/media-downloader-pro.git
cd "Media Downloader Pro"

# 2. Configure environment (optional)
cp .env.example .env

# 3. Launch container
docker compose up -d

# 4. Open in browser
# http://localhost:8080
```

To stop the service:
```bash
docker compose down
```

---

## 6. Standalone Docker Run

If you prefer using `docker run` directly:

```bash
# Build the production image
docker build -t media-downloader:latest .

# Run container with volumes and port mapping
docker run -d \
  --name media-downloader \
  -p 8080:8080 \
  -v "$(pwd)/downloads:/data/downloads" \
  -v "$(pwd)/temp:/data/temp" \
  --restart unless-stopped \
  media-downloader:latest
```

---

## 7. Configuration & Environment Variables

Create or edit `.env` in the project root:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_PORT` | `8080` | Port on which the HTTP server listens |
| `APP_HOST` | `0.0.0.0` | Bind host address |
| `DOWNLOAD_DIR` | `/data/downloads` | Path for completed downloads |
| `TEMP_DIR` | `/data/temp` | Path for active job scratch files |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Maximum concurrent active download subprocesses |
| `DOWNLOAD_RETENTION` | `86400` | Retention duration for completed files in seconds (`0` = keep forever) |
| `TEMP_RETENTION` | `3600` | Retention duration for leftover temp folders in seconds |
| `YTDLP_AUTO_UPDATE` | `true` | Check for newer stable yt-dlp release on startup |
| `YTDLP_UPDATE_INTERVAL` | `86400` | Interval between update checks in seconds |
| `YTDLP_UPDATE_CHANNEL` | `stable` | Release channel (`stable`) |
| `MAX_DOWNLOAD_SIZE` | `10G` | Maximum allowable file download size (e.g. `10G`, `500M`) |
| `DOWNLOAD_TIMEOUT` | `3600` | Maximum seconds allowed for single download job |
| `ANALYSIS_TIMEOUT` | `45` | Maximum seconds allowed for URL extraction analysis |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 8. Volume Setup & Permissions

The container exposes two data mount points:
- `/data/downloads`: Stores completed media files.
- `/data/temp`: Stores in-progress chunks and intermediate FFmpeg streams.

When mounting host directories, ensure the container's non-root user (`UID 10001`) has write permissions:

```bash
mkdir -p downloads temp
chmod 777 downloads temp  # Or chown -R 10001:10001 downloads temp
```

---

## 9. Automatic yt-dlp Updates & Supply Chain Security

Media websites frequently update their extractors, requiring timely yt-dlp updates. Media Downloader Pro solves this securely:

1. **Official Release Verification**: Updates check only official PyPI (`pypi.org/pypi/yt-dlp/json`) or GitHub (`api.github.com/repos/yt-dlp/yt-dlp/releases/latest`) APIs over HTTPS.
2. **Version Tuples**: Strict semver comparison ensures yt-dlp is never accidentally downgraded.
3. **Graceful Offline Tolerance**: If GitHub or PyPI is unreachable (e.g. airgapped environment, network outage), startup continues uninterrupted with the currently installed version.
4. **No Arbitrary Script Execution**: Upgrades are executed strictly via `pip install --upgrade yt-dlp`.
5. **Manual Trigger**: An authenticated or UI button triggers instant update checks via `POST /api/system/update-ytdlp`.

---

## 10. Security Architecture

- **SSRF Defense**:
  - Whitelist of schemes (`http://`, `https://`).
  - DNS resolution of all submitted hostnames to IPv4/IPv6 addresses.
  - Rejection of loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), link-local/cloud metadata (`169.254.169.254`, `metadata.google.internal`), and broadcast addresses.
- **Subprocess Isolation**:
  - Subprocesses are spawned using `asyncio.create_subprocess_exec` with explicit argument arrays.
  - Shell execution (`shell=True`) is strictly banned.
  - Command option injection prevented using `--` separator before URL parameters.
- **Non-Root Execution**:
  - The Docker container runs under unprivileged user `appuser` (UID 10001).
- **Filesystem Security**:
  - All filenames received from remote extractors are sanitized: traversal markers (`../`), null bytes, and illegal filesystem characters are replaced.
  - Relative paths are verified using Python's `is_relative_to` against the base directory.

---

## 11. REST API Reference

Interactive Swagger documentation is available at `/docs` when running the application.

### Healthcheck
```http
GET /health
```
Response:
```json
{
  "status": "healthy",
  "app": "Media Downloader Pro",
  "version": "1.0.0",
  "timestamp": 1725965000.12
}
```

### System Status
```http
GET /api/system
```
Response:
```json
{
  "app_name": "Media Downloader Pro",
  "app_version": "1.0.0",
  "ytdlp_version": "2026.08.30",
  "latest_ytdlp_version": "2026.08.30",
  "update_available": false,
  "ffmpeg_available": true,
  "ffmpeg_version": "7.0.2",
  "active_jobs": 0,
  "max_concurrent_downloads": 2
}
```

### URL Analysis
```http
POST /api/analyze
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=..."
}
```

### Submit Download Job
```http
POST /api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=...",
  "resolution": "1080p",
  "audio_only": false,
  "output_container": "mp4"
}
```
Response:
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "QUEUED",
  "message": "Download job queued successfully."
}
```

### Stream Progress (Server-Sent Events)
```http
GET /api/jobs/{job_id}/events
```
Emits real-time JSON events with `progress`, `speed`, `eta`, and `current_stage`.

### Cancel Job
```http
POST /api/jobs/{job_id}/cancel
```

### Download Completed File
```http
GET /api/files/{job_id}
```
Serves the finished media file as an attachment.

---

## 12. Local Development

### Backend Setup
```bash
# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements-dev.txt

# Run FastAPI backend
export PYTHONPATH="$(pwd)/backend"
uvicorn app.main:app --reload --port 8080
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Frontend runs at http://localhost:3000 with API proxy to port 8080
```

---

## 13. Testing Suite

### Backend Unit & Integration Tests
```bash
.venv/bin/pytest -v
```
Covers:
- URL scheme and SSRF protection (localhost, RFC 1918, cloud metadata)
- Filename sanitization and directory traversal attempts
- Format normalization and command building
- Job manager lifecycle, concurrency limits, and cancellation
- Background cleanup worker
- Full API integration tests

### Frontend Tests
```bash
cd frontend
npm test
npm run build
```

---

## 14. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Access to local or private network addresses is restricted"** | SSRF protection blocked the URL. | Submit only publicly accessible web URLs. |
| **"This media appears to use DRM"** | DRM encrypted stream (e.g. Netflix, Spotify). | Media Downloader Pro does not bypass DRM. |
| **"The remote website could not be reached"** | Network connectivity issue or site offline. | Verify internet access from the host/container. |
| **"Output file could not be verified"** | Extraction failed before writing to disk. | Check server logs (`docker logs media-downloader`). |
| **Permission Denied in `/data/downloads`** | Host volume ownership mismatch. | Run `chmod 777 downloads temp` on host directory. |

---

## 15. Legal & Authorized-Use Policy

This software is designed solely for archiving and downloading media that the user owns, has created, or is legally authorized to access and download. It does not circumvent digital rights management (DRM), paywalls, or authentication access controls. Users are responsible for ensuring their use conforms to the Terms of Service of content providers and relevant copyright legislation.

---

## 16. License

Released under the MIT License.
