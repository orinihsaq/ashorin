import asyncio
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.models.schemas import (
    AnalyzeResponse,
    AudioQualityOption,
    VideoQualityOption,
)
from app.utils.errors import (
    AppException,
    DRMProtectedError,
    MediaUnavailableError,
    UnsupportedWebsiteError,
    map_ytdlp_error,
)
from app.utils.logger import logger


def format_duration(seconds: Optional[int]) -> Optional[str]:
    if seconds is None or seconds < 0:
        return None
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class YtDlpService:
    @classmethod
    def get_binary_path(cls) -> str:
        return settings.YTDLP_PATH or shutil.which("yt-dlp") or "yt-dlp"

    @classmethod
    async def get_version(cls) -> str:
        bin_path = cls.get_binary_path()
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0 and stdout:
                return stdout.decode("utf-8").strip()
        except Exception as e:
            logger.warning(f"Error checking yt-dlp version: {e}")
        return "Unknown"

    @classmethod
    async def analyze_url(cls, url: str) -> AnalyzeResponse:
        """
        Extracts metadata using yt-dlp without downloading any media content.
        Parses formats into a clean, human-friendly set of choices.
        """
        bin_path = cls.get_binary_path()
        args = [
            bin_path,
            "--dump-single-json",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "--socket-timeout", "20",
            "--",
            url,
        ]

        logger.info(f"Analyzing URL: {url}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(settings.ANALYSIS_TIMEOUT),
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            raise AppException("The remote website took too long to respond. Analysis timed out.", status_code=504)
        except Exception as e:
            logger.error(f"Subprocess execution error during analysis: {e}")
            raise AppException("Failed to run extraction engine.")

        if proc.returncode != 0:
            stderr_str = stderr_bytes.decode("utf-8", errors="ignore")
            logger.warning(f"yt-dlp analysis error (code {proc.returncode}): {stderr_str}")
            user_msg = map_ytdlp_error(stderr_str)
            if "DRM" in user_msg:
                raise DRMProtectedError(user_msg)
            elif "not currently supported" in user_msg:
                raise UnsupportedWebsiteError(user_msg)
            elif "unavailable" in user_msg:
                raise MediaUnavailableError(user_msg)
            raise AppException(user_msg, status_code=400)

        try:
            raw_data = json.loads(stdout_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse yt-dlp JSON output: {e}")
            raise AppException("Failed to parse media metadata from extractor.")

        return cls._normalize_metadata(url, raw_data)

    @classmethod
    def _normalize_metadata(cls, original_url: str, data: Dict[str, Any]) -> AnalyzeResponse:
        title = data.get("title") or "Untitled Media"
        thumbnail = data.get("thumbnail")
        duration = data.get("duration")
        uploader = data.get("uploader") or data.get("channel") or data.get("creator")
        webpage_url = data.get("webpage_url") or original_url
        extractor = data.get("extractor_key") or data.get("extractor") or "Generic"

        formats = data.get("formats") or []
        available_heights = set()
        has_audio = False
        has_video = False

        for f in formats:
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            height = f.get("height")

            if vcodec and vcodec != "none":
                has_video = True
                if height and isinstance(height, int) and height > 0:
                    available_heights.add(height)

            if acodec and acodec != "none":
                has_audio = True

        # If direct video formats were found, construct sensible resolution options
        video_options: List[VideoQualityOption] = []
        video_options.append(
            VideoQualityOption(
                label="Best Available Quality",
                resolution="best",
                height=None,
                ext="mp4",
            )
        )

        standard_resolutions = [
            (2160, "2160p (4K Ultra HD)"),
            (1440, "1440p (2K Quad HD)"),
            (1080, "1080p (Full HD)"),
            (720, "720p (HD)"),
            (480, "480p (Standard)"),
            (360, "360p (Low)"),
        ]

        for height, label in standard_resolutions:
            # Include option if any stream is at or higher than this height
            if any(h >= height for h in available_heights):
                video_options.append(
                    VideoQualityOption(
                        label=label,
                        resolution=f"{height}p",
                        height=height,
                        ext="mp4",
                    )
                )

        audio_options: List[AudioQualityOption] = [
            AudioQualityOption(label="MP3 (Best Quality, 320 kbps)", format="mp3", ext="mp3"),
            AudioQualityOption(label="M4A (AAC Audio)", format="m4a", ext="m4a"),
            AudioQualityOption(label="WAV (Lossless Audio)", format="wav", ext="wav"),
        ]

        return AnalyzeResponse(
            url=original_url,
            title=title,
            thumbnail=thumbnail,
            duration=duration,
            duration_string=format_duration(duration),
            uploader=uploader,
            webpage_url=webpage_url,
            extractor=extractor,
            video_available=has_video,
            audio_available=has_audio,
            video_options=video_options,
            audio_options=audio_options,
            supported_containers=["mp4", "mkv", "webm"],
        )

    @classmethod
    def build_download_command(
        cls,
        url: str,
        temp_dir: Path,
        resolution: Optional[str] = "best",
        audio_only: bool = False,
        audio_format: Optional[str] = "mp3",
        output_container: Optional[str] = "mp4",
    ) -> List[str]:
        """
        Builds the safe command argument array for yt-dlp download execution.
        Never invokes shell, passes parameters safely as separate arguments.
        """
        bin_path = cls.get_binary_path()
        ffmpeg_bin = settings.FFMPEG_PATH or shutil.which("ffmpeg")

        # Output template: save inside job temp_dir with bounded filename length
        out_template = str(temp_dir / "%(title).150B.%(ext)s")

        cmd = [
            bin_path,
            "--newline",             # Essential for line-by-line progress stream
            "--no-playlist",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "--socket-timeout", "30",
            "-o", out_template,
        ]

        if ffmpeg_bin:
            cmd.extend(["--ffmpeg-location", ffmpeg_bin])

        # Enforce max download size if configured
        if settings.MAX_DOWNLOAD_SIZE:
            cmd.extend(["--max-filesize", settings.MAX_DOWNLOAD_SIZE])

        if audio_only:
            audio_fmt = (audio_format or "mp3").lower()
            cmd.extend([
                "-x",
                "--audio-format", audio_fmt,
                "--audio-quality", "0",
            ])
        else:
            # Video selection logic
            res = (resolution or "best").lower()
            container = (output_container or "mp4").lower()

            if res == "best" or not res.endswith("p"):
                format_selector = "bestvideo+bestaudio/best"
            else:
                try:
                    h = int(res.rstrip("p"))
                    format_selector = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                except ValueError:
                    format_selector = "bestvideo+bestaudio/best"

            cmd.extend([
                "-f", format_selector,
                "--merge-output-format", container,
            ])

        # End of options, followed strictly by url
        cmd.extend(["--", url])
        return cmd

    @classmethod
    def parse_progress_line(cls, line: str) -> Optional[Dict[str, Any]]:
        """
        Parses yt-dlp stdout progress line:
        Example: [download]  42.5% of ~ 150.00MiB at   4.20MiB/s ETA 00:15
        """
        line = line.strip()
        if not line:
            return None

        # Download percentage, speed, ETA pattern
        # [download]  12.3% of 50.00MiB at  2.50MiB/s ETA 00:20
        match = re.search(
            r"\[download\]\s+([0-9.]+)%\s+of\s+(?:~\s*)?([0-9.]+[A-Za-z]+)(?:\s+at\s+([0-9.]+[A-Za-z/]+))?(?:\s+ETA\s+([0-9:]+))?",
            line,
        )
        if match:
            percent = float(match.group(1))
            total_str = match.group(2)
            speed_str = match.group(3) or "N/A"
            eta_str = match.group(4) or "N/A"
            return {
                "stage": "Downloading",
                "progress": percent,
                "speed": speed_str,
                "eta": eta_str,
            }

        # Merging stage
        if "[merger]" in line.lower() or "merging formats" in line.lower():
            return {
                "stage": "Merging video & audio",
                "progress": 98.0,
                "speed": "Processing",
                "eta": "A few moments",
            }

        # Audio extraction
        if "[extractaudio]" in line.lower() or "destination:" in line.lower():
            return {
                "stage": "Extracting audio",
                "progress": 95.0,
                "speed": "Processing",
                "eta": "A few moments",
            }

        return None
