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
    DownloadConfig,
    TechnicalSummary,
    VideoQualityOption,
)
from app.services.file_service import FileService
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


def format_upload_date(raw_date: Optional[str]) -> Optional[str]:
    if not raw_date or not isinstance(raw_date, str):
        return None
    raw = raw_date.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


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
        Parses formats and detailed technical information.
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
        upload_date = format_upload_date(data.get("upload_date"))
        view_count = data.get("view_count")
        like_count = data.get("like_count")
        webpage_url = data.get("webpage_url") or original_url
        extractor = data.get("extractor_key") or data.get("extractor") or "Generic"

        formats = data.get("formats") or []
        available_heights = set()
        has_audio = False
        has_video = False
        max_fps: Optional[int] = None
        main_vcodec: Optional[str] = None
        main_acodec: Optional[str] = None
        max_tbr: Optional[float] = None
        best_width: Optional[int] = None
        best_height: Optional[int] = None

        # Format lookup mapping by height
        height_info: Dict[int, Dict[str, Any]] = {}

        for f in formats:
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            h = f.get("height")
            w = f.get("width")
            fps = f.get("fps")
            tbr = f.get("tbr")
            filesize = f.get("filesize") or f.get("filesize_approx")

            if vcodec and vcodec != "none":
                has_video = True
                if not main_vcodec:
                    main_vcodec = str(vcodec).split(".")[0]
                if fps and (max_fps is None or fps > max_fps):
                    max_fps = int(fps)
                if h and isinstance(h, int) and h > 0:
                    available_heights.add(h)
                    if best_height is None or h > best_height:
                        best_height = h
                        best_width = w
                    if h not in height_info or (tbr and tbr > (height_info[h].get("tbr") or 0)):
                        height_info[h] = {
                            "width": w,
                            "fps": fps,
                            "vcodec": str(vcodec).split(".")[0] if vcodec else None,
                            "filesize": filesize,
                            "tbr": tbr,
                        }

            if acodec and acodec != "none":
                has_audio = True
                if not main_acodec:
                    main_acodec = str(acodec).split(".")[0]

            if tbr and (max_tbr is None or tbr > max_tbr):
                max_tbr = float(tbr)

        # Build clean quality options
        video_options: List[VideoQualityOption] = []
        video_options.append(
            VideoQualityOption(
                label="Best Available Quality",
                resolution="best",
                height=best_height,
                width=best_width,
                fps=max_fps,
                vcodec=main_vcodec,
                ext="mp4",
                filesize_approx=None,
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
            if any(h >= height for h in available_heights):
                info = height_info.get(height, {})
                sz_str = FileService.format_bytes(info["filesize"]) if info.get("filesize") else None
                video_options.append(
                    VideoQualityOption(
                        label=label,
                        resolution=f"{height}p",
                        height=height,
                        width=info.get("width"),
                        fps=info.get("fps"),
                        vcodec=info.get("vcodec"),
                        filesize_approx=sz_str,
                        ext="mp4",
                    )
                )

        audio_options: List[AudioQualityOption] = [
            AudioQualityOption(label="MP3 (Best Quality, 320 kbps)", format="mp3", ext="mp3", bitrate="320k"),
            AudioQualityOption(label="M4A (AAC Audio)", format="m4a", ext="m4a", bitrate="256k"),
            AudioQualityOption(label="WAV (Lossless Audio)", format="wav", ext="wav", bitrate="lossless"),
            AudioQualityOption(label="FLAC (Lossless Audio)", format="flac", ext="flac", bitrate="lossless"),
            AudioQualityOption(label="Opus (High Efficiency)", format="opus", ext="opus", bitrate="160k"),
        ]

        resolution_str = f"{best_width} × {best_height}" if best_width and best_height else None
        tech_summary = TechnicalSummary(
            resolution_str=resolution_str,
            fps=max_fps,
            vcodec=main_vcodec,
            acodec=main_acodec,
            tbr=max_tbr,
            format_count=len(formats),
            media_type="video" if has_video else ("audio" if has_audio else "media"),
        )

        return AnalyzeResponse(
            url=original_url,
            title=title,
            thumbnail=thumbnail,
            duration=duration,
            duration_string=format_duration(duration),
            uploader=uploader,
            upload_date=upload_date,
            view_count=view_count,
            like_count=like_count,
            webpage_url=webpage_url,
            extractor=extractor,
            media_type="video" if has_video else ("audio" if has_audio else "media"),
            video_available=has_video,
            audio_available=has_audio,
            video_options=video_options,
            audio_options=audio_options,
            supported_containers=["mp4", "mkv", "webm"],
            technical_summary=tech_summary,
        )

    @classmethod
    def build_download_command(
        cls,
        url: str,
        temp_dir: Path,
        config: Optional[DownloadConfig] = None,
        # Legacy keyword arguments
        resolution: Optional[str] = None,
        audio_only: Optional[bool] = None,
        audio_format: Optional[str] = None,
        output_container: Optional[str] = None,
    ) -> List[str]:
        """
        Builds the safe command argument array for yt-dlp download execution.
        Accepts structured DownloadConfig or maps legacy parameters.
        Never invokes shell; parameters are passed safely as separate array elements.
        """
        if config is None:
            # Map legacy kwargs to DownloadConfig
            config = DownloadConfig(
                quality=resolution or "best",
                audio_mode="audio_only" if audio_only else "merge",
                audio_format=audio_format or "mp3",
                output_container=output_container or "mp4",
            )

        bin_path = cls.get_binary_path()
        ffmpeg_bin = settings.FFMPEG_PATH or shutil.which("ffmpeg")

        # 1. Output Template Validation and Sanitization
        safe_template = FileService.sanitize_filename_template(config.filename_template)
        out_path_template = str(temp_dir / safe_template)

        # 2. Base Command Configuration
        cmd = [
            bin_path,
            "--newline",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "-o", out_path_template,
        ]

        if ffmpeg_bin:
            cmd.extend(["--ffmpeg-location", ffmpeg_bin])

        # 3. Network Limits & Clamped Parameters
        retries = max(1, min(100, config.retries))
        timeout = max(5, min(3600, config.timeout))
        cmd.extend([
            "--retries", str(retries),
            "--fragment-retries", str(retries),
            "--socket-timeout", str(timeout),
        ])

        if config.concurrent_fragments > 1:
            frag = max(1, min(16, config.concurrent_fragments))
            cmd.extend(["--concurrent-fragments", str(frag)])

        if settings.MAX_DOWNLOAD_SIZE:
            cmd.extend(["--max-filesize", settings.MAX_DOWNLOAD_SIZE])

        # 4. Playlist Configuration
        if config.playlist_mode == "playlist":
            if config.playlist_items:
                # Sanitize playlist items (only digits, commas, dashes allowed)
                safe_items = re.sub(r"[^\d,-]", "", str(config.playlist_items))
                if safe_items:
                    cmd.extend(["--playlist-items", safe_items])
        else:
            cmd.append("--no-playlist")

        # 5. Format & Container Selection
        allowed_containers = {"mp4", "mkv", "webm", "mp3", "m4a", "wav", "flac", "opus"}
        allowed_audio_fmts = {"mp3", "m4a", "wav", "flac", "opus"}

        is_audio_only = config.audio_mode == "audio_only"

        if is_audio_only:
            audio_fmt = config.audio_format.lower() if config.audio_format.lower() in allowed_audio_fmts else "mp3"
            cmd.extend([
                "-x",
                "--audio-format", audio_fmt,
                "--audio-quality", str(config.audio_quality or "0"),
            ])
        else:
            # Video selector construction
            res = (config.quality or "best").lower()
            container = config.output_container.lower() if config.output_container.lower() in allowed_containers else "mp4"

            # Codec preference
            codec_filter = ""
            if config.video_codec == "h264":
                codec_filter = "[vcodec^=avc]"
            elif config.video_codec == "vp9":
                codec_filter = "[vcodec^=vp9]"
            elif config.video_codec == "av1":
                codec_filter = "[vcodec^=av01]"

            if res == "best" or not res.endswith("p"):
                if codec_filter:
                    format_selector = f"bestvideo{codec_filter}+bestaudio/best{codec_filter}/best"
                else:
                    format_selector = "bestvideo+bestaudio/best"
            else:
                try:
                    h = int(res.rstrip("p"))
                    if codec_filter:
                        format_selector = f"bestvideo[height<={h}]{codec_filter}+bestaudio/best[height<={h}]{codec_filter}/best"
                    else:
                        format_selector = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                except ValueError:
                    format_selector = "bestvideo+bestaudio/best"

            cmd.extend([
                "-f", format_selector,
                "--merge-output-format", container,
            ])

        # 6. Subtitles Configuration
        if config.subtitles:
            cmd.append("--write-subs")
            if config.auto_subtitles:
                cmd.append("--write-auto-subs")
            if config.subtitle_langs:
                safe_langs = re.sub(r"[^\w,-]", "", config.subtitle_langs)
                if safe_langs:
                    cmd.extend(["--sub-langs", safe_langs])
            if config.embed_subtitles and not is_audio_only:
                cmd.append("--embed-subs")

        # 7. Metadata & Chapters
        if config.embed_metadata:
            cmd.append("--embed-metadata")
        if config.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if config.write_chapters and not is_audio_only:
            cmd.append("--embed-chapters")

        # 8. Safe End of Options Separator and URL
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

        # Subtitles
        if "[subtitles]" in line.lower() or "writing video subtitles" in line.lower():
            return {
                "stage": "Processing subtitles",
                "progress": 92.0,
                "speed": "Subtitles",
                "eta": "A few moments",
            }

        return None
