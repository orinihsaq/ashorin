# ashoriN

A precision, high-performance self-hosted media extraction and stream transcoding utility powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org). Designed for reliable containerized deployment with non-root security, real-time Server-Sent Events (SSE), granular yt-dlp parameter controls, optimization presets, and a desktop utility interface.

---

## 1. Product Overview

**ashoriN** provides a polished, self-hosted web interface to inspect, transcode, and extract video and audio streams from supported websites. It isolates yt-dlp execution inside clean architectural service layers, converts technical errors into friendly user messages, limits concurrent resource usage, and ensures that neither media files nor internal networks are exposed to SSRF attacks.

### Core Principles
- **No Demoware / No Placeholders**: Fully implemented backend and frontend with real yt-dlp execution.
- **Enterprise Security**: Strict SSRF prevention against private IP networks, cloud metadata endpoints, and loopback addresses.
- **Self-Contained Docker Architecture**: Multi-stage Debian slim build running as non-root user `appuser` (UID 10001).
- **Graceful Auto-Updates**: Non-breaking startup update checks against official PyPI releases with offline fallback.
- **Real-Time Progress**: Live Server-Sent Events (SSE) streaming download progress, speed, ETA, and processing stages.
- **Canonical Presets & Advanced Controls**: Dual-mode workflow with 5 optimization presets and deep yt-dlp controls.

---

## 2. Features & Workflow

- **Instant URL Analysis**:
  - Fetches thumbnail, title, uploader avatar, duration, upload date, view count, and technical stream specifications (video codec, audio codec, framerate, bitrate, format count) without downloading media.
- **Dual-Mode Configuration**:
  - **Recommended Mode**: Default clean workflow with instant presets, resolution selectors, and container buttons.
  - **Advanced Mode**: Granular yt-dlp parameter controls organized into General, Video, Audio, Network, Subtitles, Metadata, and Playlist categories.
- **Canonical Optimization Presets**:
  - `Recommended`: Balanced standard for maximum compatibility. Best video and audio merged into MP4 with metadata.
  - `Best Quality`: Maximum visual & audio fidelity (up to 4K/8K) preserved in MKV with chapters and metadata.
  - `Audio Only`: Extracts pure audio stream and transcodes to pristine 320 kbps MP3 with album artwork embedded.
  - `Small File`: Efficient compact stream selection (up to 720p H.264) for mobile devices and storage efficiency.
  - `Archive`: Full fidelity preservation with all embedded subtitles, chapters, metadata tags, and resilient network retries.
- **Real-Time Download Tracking**:
  - 5-stage progression stepper: `Preparing` -> `Extracting` -> `Downloading` -> `Merging` -> `Completed`.
  - Dynamic progress bar, downloaded percentage, transfer speed, remaining ETA, and downloaded payload size.
- **Subprocess Cancellation**:
  - Safely terminates running jobs on demand, sends SIGTERM/SIGKILL only to the target subprocess, and purges temporary files.
- **Safe File Delivery & In-Browser Download**:
  - Path traversal protection, safe filename template sanitization, and direct browser download button.
- **Download History & Management**:
  - `ashoriN History` drawer with direct file access and record deletion.
- **Automated Lifecycle Cleanup**:
  - Periodic background cleanup deleting expired media files and temp directories according to retention rules.
- **Storage & Engine Diagnostics**:
  - System modal reporting yt-dlp version, FFmpeg status, concurrency limits, and live persistent disk usage gauge (`/data`).

---

## 3. Technology Stack & Architecture

```
Browser (React + TypeScript + Vite + Tailwind CSS + Phosphor Icons)
   │
   │  REST API & Server-Sent Events (/api/jobs/{id}/events)
   ▼
FastAPI Application (Python 3.12 / Uvicorn)
   ├── SecurityService (SSRF defense, IP resolution, scheme validation)
   ├── YtDlpService (Subprocess extraction, format normalization, CLI builder)
   ├── PresetService (Canonical presets and configuration definitions)
   ├── FFmpegService (Version query, format probe)
   ├── JobManager (Queue, concurrency semaphore, cancellation, SSE broadcast)
   ├── FileService (Filename template sanitization, path containment, byte formatting)
   ├── YtDlpUpdater (HTTPS update verification & non-blocking upgrade)
   └── CleanupService (Periodic background expired file purging)
   │
   ├── Temporary directory (/data/temp/{job_id})
   └── Final storage (/data/downloads/)
```

---

## 4. Quick Start with Docker Compose

Deploying ashoriN takes under a minute:

```bash
# 1. Start the container stack
docker compose up -d --build

# 2. Access the application in your browser
open http://localhost:8080
```

To stop the service:
```bash
docker compose down
```

---

## 5. Configuration & Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_PORT` | `8080` | Port for the HTTP server to listen on. |
| `APP_HOST` | `0.0.0.0` | Host IP binding. |
| `LOG_LEVEL` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`). |
| `DOWNLOAD_DIR` | `/data/downloads` | Directory where final completed media files reside. |
| `TEMP_DIR` | `/data/temp` | Temporary scratch space for partial downloads. |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Maximum concurrent yt-dlp worker subprocesses. |
| `MAX_DOWNLOAD_SIZE` | `10G` | Max file size filter passed to yt-dlp (`--max-filesize`). |
| `DOWNLOAD_RETENTION` | `86400` | Retention duration for finished downloads (seconds, 0 = disabled). |
| `TEMP_RETENTION` | `3600` | Retention duration for abandoned temp files (seconds). |
| `AUTO_UPDATE_YTDLP` | `true` | Enable non-blocking startup check for yt-dlp updates. |

---

## 6. API Reference

Interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

### Key Endpoints

- `GET /health`: Healthcheck endpoint for orchestration.
- `GET /api/presets`: Returns canonical optimization presets.
- `POST /api/analyze`: Inspects a media URL and returns title, thumbnail, duration, options, and technical specs.
- `POST /api/download`: Queues a media extraction job with preset or advanced configuration.
- `GET /api/jobs`: Lists recent jobs and active concurrency.
- `GET /api/jobs/{id}`: Retrieves job progress and status.
- `GET /api/jobs/{id}/events`: Server-Sent Events stream for real-time progress updates.
- `POST /api/jobs/{id}/cancel`: Safely terminates a running job.
- `DELETE /api/jobs/{id}`: Deletes a job record and purged files.
- `GET /api/files/{id}`: Streams the completed media file with Content-Disposition attachment header.
- `GET /api/system`: Returns runtime diagnostic info, yt-dlp version, FFmpeg status, and storage metrics.
- `POST /api/system/update-ytdlp`: Triggers an online update check for yt-dlp.

---

## 7. Security Architecture

1. **SSRF Defense (`SecurityService`)**:
   - Every input URL is strictly parsed.
   - Only `http` and `https` schemes are accepted.
   - Hostnames are resolved through DNS to their destination IP addresses.
   - Private IPv4/IPv6 networks, loopback (`127.0.0.0/8`, `::1`), link-local, carrier-grade NAT, and cloud metadata addresses (`169.254.169.254`, `metadata.google.internal`) are rejected with `400 Bad Request`.

2. **Command Injection Prevention**:
   - Subprocesses are spawned with argument arrays (`List[str]`).
   - `shell=True` is forbidden across the codebase.
   - End-of-options separator `--` is appended immediately before user URLs.

3. **Path Traversal & Filename Sanitization**:
   - Output filename templates are sanitized to strip traversal markers (`..`), directory slashes, control characters, and reserved tokens.
   - Final files are strictly verified to reside within designated target directories using `Path.resolve().is_relative_to()`.

4. **Container Hardening**:
   - Non-root user `appuser` (UID 10001, GID 10001).
   - Read-only root filesystem compatible.
   - Volumes mapped to `/data` with appropriate ownership.

---

## 8. Testing

### Run Backend Test Suite (Pytest)
```bash
./.venv/bin/pytest -v
```

### Run Frontend Test Suite (Vitest)
```bash
cd frontend && npm test
```

### Run Frontend Production Build
```bash
cd frontend && npm run build
```

---

## 9. Dedication

Made in Love with her ♥
