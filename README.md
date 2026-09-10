<div align="center">

# ashori<span style="color:#9333ea;">N</span>

**The unified self-hosted media platform for web streams, playlists, magnets, and torrents.**

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

[Quick Start](#-quick-start) • [Features](#-features) • [Configuration](#-configuration) • [API](#-rest-api) • [Security](#-security)

</div>

---

## ✨ Overview

**ashoriN** transforms traditional media extraction into a unified self-hosted download station. It combines **yt-dlp**, **FFmpeg**, and an **embedded libtorrent-rasterbar engine** inside a single hardened, non-root Docker container consuming just **~52 MiB RAM** with zero external daemons.

Accepts any media input:
* 🌐 **Web URLs**: YouTube, Twitch, Twitter/X, SoundCloud, Vimeo, direct MP4/M3U8 streams, and 1,000+ supported sites.
* 📋 **Playlists**: Multi-item selection, dedicated folder generation, and scheduled sync watchers.
* 🧲 **BitTorrent & Magnets**: Multi-file checklist, per-file priorities, ratio/time seeding policies, and live swarm telemetry.

---

## 🚀 Quick Start

### Run with Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/ashoriN.git
cd ashoriN

# 2. Launch the container
docker compose up -d

# 3. Open in your browser
http://localhost:8080
```

---

## 🎯 Features

### 🎥 Web Media & Playlists
* **Instant URL Inspection**: Preview title, thumbnail, duration, stream formats, and technical codec specifications before downloading.
* **Granular yt-dlp Controls**: Preset modes (*Recommended*, *Best Quality*, *Audio Only*, *Small File*, *Archive*) or custom flags (codecs, subtitles, chapters, fragments).
* **Playlist Manager**: Select specific playlist items, auto-generate dedicated folders, and track per-item progress.

### 🧲 Native BitTorrent & Magnets
* **Ultra-Lightweight (~52MB RAM)**: Direct C++ `libtorrent-rasterbar` Python bindings. Zero Transmission or aria2 daemons.
* **Multi-File Selection & Priorities**: Inspect torrent contents before downloading; set files to *High*, *Normal*, *Low*, or *Skip*.
* **Seeding Policies**: Configurable swarm exit rules (*Stop immediately*, *1.0x Ratio*, *2.0x Ratio*, *30 min*, *2 hours*, *Indefinite*).
* **Swarm Diagnostics**: Live upload/download speeds, seeders/leechers counts, share ratio, ETA, and pause/resume/recheck controls.

### 📂 Smart Media Library
* **Built-in Player**: Stream audio and video directly in your browser with HTTP 206 range request support.
* **Auto-Cataloging**: Completed web and torrent media are automatically indexed with metadata and provider tags.
* **Storage Protection**: Pin favorite media items to protect them from automatic retention purging.

### 🔄 Automation & Intelligence
* **Sync Watchers**: Monitor YouTube playlists or channels on cron intervals and auto-download new uploads.
* **Rule Engine**: Define smart pattern-matching rules to automatically assign profiles and destination paths.
* **Download Preflight**: Inspect disk space forecasts, duplicate detection, and file collisions prior to execution.
* **REST API & Webhooks**: Automate downloads with scoped API keys and real-time webhook notifications.

---

## ⚙️ Configuration

Set variables in `docker-compose.yml` or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `APP_PORT` | `8080` | Web UI & API port |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Max concurrent worker processes |
| `DOWNLOAD_RETENTION` | `0` | Retention duration for finished files (seconds, `0` = disabled) |
| `TEMP_RETENTION` | `3600` | Retention for orphaned temporary files (seconds) |
| `MAX_DOWNLOAD_SIZE` | `10G` | Maximum download size threshold |
| `AUTO_UPDATE_YTDLP` | `true` | Check and apply yt-dlp updates on startup |

---

## 🔒 Security

* **SSRF Defense**: Strict validation rejecting loopback (`127.0.0.1`), private networks (`10.x`, `192.168.x`), and cloud metadata (`169.254.169.254`).
* **Non-Root Container**: Runs under unprivileged user `appuser` (`UID 10001`, `GID 10001`).
* **Safe Command Execution**: Zero `shell=True` subprocesses; strict argument arrays with `--` boundary flags.
* **Path Traversal Protection**: Output directories strictly validated within `/data` boundaries.

---

## 🛠️ Tech Stack

* **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Phosphor Icons
* **Backend**: FastAPI, Python 3.12, Uvicorn, SQLite, Server-Sent Events (SSE)
* **Engines**: [yt-dlp](https://github.com/yt-dlp/yt-dlp), [static-ffmpeg](https://github.com/mwader/static-ffmpeg), [libtorrent](https://libtorrent.org/)

---

## 🧪 Testing

```bash
# Backend test suite (108 tests)
pytest backend/tests

# Frontend test suite (27 tests)
cd frontend && npm test -- --run

# Production frontend build
cd frontend && npm run build
```

---

<div align="center">

Made in Love with her ♥

*Powered by yt-dlp + FFmpeg + libtorrent*

</div>
