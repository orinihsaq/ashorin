# Build a Production-Grade Self-Hosted Media Downloader

You are the lead software architect and senior full-stack engineer.

Build a complete production-quality self-hosted web application called **Media Downloader**.

The application uses **yt-dlp** as the media extraction/download engine and **FFmpeg** for media processing/merging.

The entire application must run inside Docker and must be optimized for a small, reliable production image.

Do not create a toy/demo implementation. Build the actual application end-to-end, including frontend, backend, Docker, tests, security, error handling, documentation, and update mechanisms.

---

## 1. Product Goal

Create a web application where a user can:

1. Paste a URL from a yt-dlp-supported website.
2. Analyze the URL.
3. See title, thumbnail, duration, uploader and available media qualities.
4. Select a desired quality/output format.
5. Start the download.
6. See real-time download progress.
7. Cancel the download if required.
8. Receive the completed media file.
9. Download the resulting file from the browser.

The application must support a large number of websites through yt-dlp.

Do NOT claim that every website is supported. Clearly handle unsupported sites, DRM-protected media, authentication requirements, unavailable content, and extractor failures.

The application must only be designed for media the user is authorized to download.

Do not implement DRM bypassing, paywall bypassing, CAPTCHA bypassing, authentication circumvention, or access-control circumvention.

---

# 2. Technology Stack

Use:

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS

Backend:
- Python
- FastAPI
- Pydantic

Media:
- yt-dlp
- FFmpeg

Communication:
- REST API
- Server-Sent Events for download progress

Storage:
- Local filesystem
- No database required for V1

Container:
- Docker
- Multi-stage build
- Non-root runtime

Use current stable package versions compatible with the environment.

Do not unnecessarily introduce Redis, PostgreSQL, Celery, Kubernetes, or other infrastructure.

Keep the architecture simple and maintainable.

---

# 3. Architecture

Use this architecture:

Browser
↓
React frontend
↓
FastAPI REST/SSE API
↓
Download job manager
↓
yt-dlp
↓
FFmpeg when necessary
↓
Temporary job directory
↓
Final downloads directory

Keep yt-dlp execution isolated inside a service layer.

Do not scatter subprocess calls throughout the application.

Create clear services such as:

- YtDlpService
- FFmpegService
- DownloadService
- JobManager
- YtDlpUpdater
- FileService
- Security/URL validation service

---

# 4. URL Analysis

Implement:

POST /api/analyze

Request:

{
  "url": "https://example.com/..."
}

Use yt-dlp extraction-only behavior.

Do not download media during analysis.

Return normalized metadata:

- title
- thumbnail
- duration
- uploader
- webpage URL
- extractor/site
- available formats
- audio availability
- video availability

Normalize raw yt-dlp formats into a clean frontend-friendly representation.

Do not expose a huge confusing raw format list by default.

---

# 5. Format Selection

The frontend should provide understandable options such as:

Video:
- Best
- 1080p
- 720p
- 480p
- 360p

Audio:
- Best
- MP3
- M4A
- WAV where technically appropriate

Container/output:
- MP4
- MKV
- WebM
- MP3
- M4A

Only display options that are actually available.

Do not blindly request formats that don't exist.

Create a backend format-selection layer that translates UI selections into safe yt-dlp format selectors.

---

# 6. Download API

Implement:

POST /api/download

Example:

{
  "url": "...",
  "format": "1080p",
  "output": "mp4"
}

Return:

{
  "job_id": "..."
}

Implement:

GET /api/jobs/{job_id}

Implement:

GET /api/jobs/{job_id}/events

Use Server-Sent Events for:

- queued
- analyzing
- downloading
- processing
- progress
- speed
- ETA
- completed
- failed
- cancelled

The UI must update progress without page refresh.

---

# 7. Cancellation

Implement:

POST /api/jobs/{job_id}/cancel

The backend must terminate only the subprocess associated with that job.

Clean up temporary files afterward.

Handle cancellation safely.

---

# 8. Job System

Implement an in-memory job manager for V1.

Job states:

QUEUED
ANALYZING
DOWNLOADING
PROCESSING
COMPLETED
FAILED
CANCELLED

Track:

- job ID
- URL
- title
- status
- progress
- speed
- ETA
- current stage
- created time
- started time
- completed time
- output file
- error information

Limit concurrent downloads using:

MAX_CONCURRENT_DOWNLOADS

Do not allow unlimited subprocess creation.

---

# 9. File Management

Use:

/data/downloads

for completed downloads.

Use:

/data/temp/{job_id}

for temporary files.

Workflow:

yt-dlp
↓
temporary directory
↓
FFmpeg processing/merging if necessary
↓
final output
↓
/data/downloads

Delete temporary job directories after completion or failure.

Sanitize all filenames.

Never trust a title or filename supplied by a remote website.

Prevent:

- path traversal
- absolute paths
- invalid filenames
- excessively long filenames

---

# 10. Cleanup

Implement configurable cleanup.

Environment variables:

DOWNLOAD_RETENTION
TEMP_RETENTION

Example:

DOWNLOAD_RETENTION=86400
TEMP_RETENTION=3600

Implement periodic cleanup of expired files.

Do not delete files when retention is disabled.

Document the behavior clearly.

---

# 11. yt-dlp Automatic Updates

This is a major requirement.

The Docker container must support automatically updating yt-dlp to the latest stable version online.

Environment variables:

YTDLP_AUTO_UPDATE=true
YTDLP_UPDATE_INTERVAL=86400
YTDLP_UPDATE_CHANNEL=stable

At startup:

1. Determine installed yt-dlp version.
2. If auto-update is enabled, determine whether a newer stable version is available.
3. Update only when necessary.
4. Start the application.
5. If update fails because the network is unavailable or the update server cannot be reached, DO NOT prevent the application from starting.
6. Log the failure clearly.

Do not blindly reinstall yt-dlp every time the container starts.

Avoid unnecessary network requests.

Implement updater logic in a dedicated service/script.

The updater must not silently downgrade yt-dlp.

Expose system information through:

GET /api/system

Example:

{
  "app_version": "1.0.0",
  "ytdlp_version": "...",
  "latest_ytdlp_version": "...",
  "update_available": false,
  "ffmpeg_available": true,
  "ffmpeg_version": "..."
}

The frontend should show the yt-dlp status.

---

# 12. Important Supply-Chain Requirement

Automatic updates introduce supply-chain risk.

Design the updater so that:

- only the official yt-dlp distribution/source is used,
- HTTPS is required,
- versions are validated,
- failed updates preserve the current working version,
- application startup does not depend on successful updating,
- update behavior is clearly logged.

Do not execute arbitrary downloaded scripts.

Do not add unnecessary third-party update services.

Document the automatic-update behavior in README.md.

---

# 13. Security

Treat every submitted URL as untrusted.

Implement strong URL validation.

Allow only:

http://
https://

Reject dangerous schemes such as:

file://

Prevent SSRF against:

- localhost
- loopback addresses
- private IP ranges
- link-local addresses
- internal network services
- cloud metadata endpoints

Validate DNS resolution where appropriate.

Do not let a user use the downloader as an unrestricted internal-network proxy.

Use timeouts.

Apply configurable download size limits.

Environment variables:

MAX_DOWNLOAD_SIZE
DOWNLOAD_TIMEOUT

Run the application as a non-root user.

Never run yt-dlp or FFmpeg as root.

---

# 14. Process Security

Use subprocess execution carefully.

Never construct shell commands by string concatenation with user input.

Use argument arrays.

Do not use shell=True for user-controlled values.

Capture stdout/stderr safely.

Avoid exposing raw subprocess output directly to the browser.

Convert technical errors into safe user-facing messages while retaining detailed logs server-side.

---

# 15. Error Handling

Create clean error categories.

Examples:

Unsupported website:

"This website is not currently supported by yt-dlp."

DRM:

"This media appears to use DRM and cannot be downloaded by this application."

Network failure:

"The remote website could not be reached. Please try again."

Invalid URL:

"Please enter a valid HTTP or HTTPS URL."

Format unavailable:

"The selected quality is no longer available."

Server failure:

"Something went wrong while processing the download."

Do not show huge Python tracebacks in the UI.

---

# 16. Frontend

Build a polished modern utility-style interface.

The homepage should be simple.

Main screen:

Media Downloader

"Download media from supported websites"

Large URL input

[ Analyze ]

After analysis show:

- thumbnail
- title
- uploader
- duration
- source website
- available qualities
- output format
- download button

During download show:

- title
- progress bar
- percentage
- download speed
- ETA
- current stage
- cancel button

After completion show:

- success state
- filename
- file size
- Download button

---

# 17. UI Design

Use a professional modern design.

Requirements:

- responsive desktop/mobile
- light/dark theme
- accessible controls
- keyboard navigation
- clear loading states
- clear error states
- no unnecessary animations
- no visual clutter

Do not build a generic admin dashboard.

This should feel like a polished consumer utility.

---

# 18. API

Implement:

GET /health

GET /api/system

POST /api/analyze

POST /api/download

GET /api/jobs

GET /api/jobs/{id}

GET /api/jobs/{id}/events

POST /api/jobs/{id}/cancel

GET /api/files/{id}

DELETE /api/jobs/{id}

FastAPI should expose OpenAPI documentation at:

/docs

---

# 19. Docker

Build a production-quality multi-stage Docker image.

Requirements:

- small image
- no development dependencies
- no npm cache
- no package cache
- no source files that aren't required at runtime
- non-root user
- proper filesystem permissions
- healthcheck
- signal handling
- graceful shutdown

Prefer a Debian/Ubuntu slim-style Python runtime if that provides better FFmpeg/Python compatibility than Alpine.

Optimize for the smallest reliable image rather than blindly optimizing for absolute minimum size.

After implementation measure:

docker images

and:

docker history

Document the resulting image size.

---

# 20. Docker Compose

Provide:

docker-compose.yml

Example:

services:
  media-downloader:
    build: .
    container_name: media-downloader
    ports:
      - "8080:8080"
    volumes:
      - ./downloads:/data/downloads
      - ./temp:/data/temp
    environment:
      YTDLP_AUTO_UPDATE: "true"
      YTDLP_UPDATE_INTERVAL: "86400"
      MAX_CONCURRENT_DOWNLOADS: "2"
      DOWNLOAD_RETENTION: "86400"
      TEMP_RETENTION: "3600"
    restart: unless-stopped

Make sure the example actually works.

---

# 21. Environment Configuration

Create:

.env.example

Include:

APP_PORT=8080

DOWNLOAD_DIR=/data/downloads
TEMP_DIR=/data/temp

MAX_CONCURRENT_DOWNLOADS=2

DOWNLOAD_RETENTION=86400
TEMP_RETENTION=3600

YTDLP_AUTO_UPDATE=true
YTDLP_UPDATE_INTERVAL=86400
YTDLP_UPDATE_CHANNEL=stable

MAX_DOWNLOAD_SIZE=10G
DOWNLOAD_TIMEOUT=3600

LOG_LEVEL=INFO

Make configuration validation strict and provide sensible defaults.

---

# 22. Logging

Implement structured application logging.

Include:

- startup
- yt-dlp version
- FFmpeg version
- update checks
- update results
- job creation
- extraction
- download start
- download completion
- cancellation
- cleanup
- failures

Never log secrets, cookies, authorization headers, or sensitive credentials.

---

# 23. Tests

Create comprehensive tests.

Backend unit tests:

- URL validation
- SSRF protection
- filename sanitization
- configuration
- format normalization
- job lifecycle
- cancellation
- cleanup
- error mapping

Integration tests:

- analyze URL
- create download
- download test media
- FFmpeg processing
- progress events
- cancellation
- cleanup

Frontend tests:

- URL form
- analysis
- loading state
- format selection
- progress
- cancellation
- completion
- errors

Docker tests:

- image builds
- container starts
- health endpoint works
- frontend loads
- API works
- yt-dlp exists
- FFmpeg exists
- non-root execution works
- mounted directories work

Use safe/legal public test media.

Do not use DRM-protected test content.

---

# 24. README

Create a complete README.

Include:

- project overview
- features
- architecture
- requirements
- Docker installation
- Docker Compose installation
- configuration
- volume setup
- automatic yt-dlp updates
- security considerations
- API documentation
- troubleshooting
- development instructions
- testing
- upgrade procedure
- limitations
- legal/authorized-use notice

Installation should be as simple as:

git clone ...
cd media-downloader
docker compose up -d

Then:

http://localhost:8080

---

# 25. Code Quality

Use clean architecture.

Requirements:

- strong typing
- meaningful names
- small modules
- no giant files
- no duplicated business logic
- no hard-coded configuration
- no magic numbers
- useful comments only
- proper exception handling
- async where appropriate
- safe subprocess management

Do not create fake/mock download behavior.

The real application must use yt-dlp.

Do not replace working backend functionality with placeholders merely to make tests pass.

---

# 26. Development Process

Before coding:

1. Inspect the repository.
2. Determine what already exists.
3. Create a concise implementation plan.
4. Identify dependencies.
5. Build the architecture.
6. Implement backend.
7. Implement frontend.
8. Implement Docker.
9. Implement tests.
10. Run the complete test suite.
11. Run the Docker build.
12. Run the actual container.
13. Test the application through the browser/API.
14. Fix all issues discovered.
15. Perform a final production-quality review.

Do not stop after the first successful build.

---

# 27. Final Verification

Before declaring completion, verify:

- frontend loads
- API responds
- healthcheck passes
- yt-dlp is available
- FFmpeg is available
- URL analysis works
- real yt-dlp extraction works
- real media download works with legal/public test media
- progress works
- cancellation works
- file download works
- temporary cleanup works
- yt-dlp update check works
- update failure does not prevent startup
- container runs as non-root
- SSRF protections work
- Docker image is optimized
- all tests pass

Report the exact test results.

Report:

- Docker image size
- yt-dlp version
- FFmpeg version
- frontend test result
- backend test result
- integration test result
- Docker test result

If anything is failing, do not claim the project is complete. Fix it first.

---

# 28. Important Implementation Principle

Prioritize:

1. correctness
2. security
3. reliability
4. maintainability
5. user experience
6. image size optimization

Do not sacrifice security or reliability merely to reduce Docker image size.

Build this as software that another developer could clone and deploy without needing to repair the implementation manually.