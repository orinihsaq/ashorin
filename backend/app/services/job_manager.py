import asyncio
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from app.config import settings
from app.models.job import Job
from app.models.schemas import DownloadRequest, JobResponse, JobStatus
from app.services.file_service import FileService
from app.services.yt_dlp import YtDlpService
from app.utils.errors import FileTooLargeError, JobNotFoundError, map_ytdlp_error
from app.utils.logger import logger


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._lock = asyncio.Lock()

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_DOWNLOADS)
        return self._semaphore

    async def create_job(self, req: DownloadRequest) -> Job:
        """Create a new download job and schedule its asynchronous execution."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            url=req.url,
            title=req.title,
            resolution=req.resolution,
            audio_only=req.audio_only,
            audio_format=req.audio_format,
            output_container=req.output_container,
            status=JobStatus.QUEUED,
            current_stage="Queued in download manager",
        )

        async with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Job [{job_id}] created for URL: {req.url}")
        job.emit_event()

        # Schedule execution in background
        asyncio.create_task(self._process_job(job_id))
        return job

    def get_job(self, job_id: str) -> Job:
        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job {job_id} not found")
        return self._jobs[job_id]

    def list_jobs(self) -> List[JobResponse]:
        # Return sorted by created_at descending
        sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_response() for j in sorted_jobs]

    def get_active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values()
            if j.status in (JobStatus.QUEUED, JobStatus.ANALYZING, JobStatus.DOWNLOADING, JobStatus.PROCESSING)
        )

    async def cancel_job(self, job_id: str) -> Job:
        """Safely terminates subprocess and cleans temporary files."""
        job = self.get_job(job_id)

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return job

        logger.info(f"Cancelling job [{job_id}]...")
        job.is_cancelled = True
        job.status = JobStatus.CANCELLED
        job.current_stage = "Cancelled by user"

        # Terminate active subprocess safely
        if job.process:
            try:
                job.process.terminate()
                try:
                    await asyncio.wait_for(job.process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    job.process.kill()
                    await job.process.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.warning(f"Error terminating job process [{job_id}]: {e}")

        # Clean up temporary directory
        if job.temp_dir:
            FileService.cleanup_temp_dir(job.temp_dir)

        job.completed_at = time.time()
        job.emit_event()
        logger.info(f"Job [{job_id}] successfully cancelled and cleaned up.")
        return job

    async def delete_job(self, job_id: str) -> None:
        """Removes job from memory and deletes downloaded file if present."""
        job = self.get_job(job_id)

        if job.status in (JobStatus.QUEUED, JobStatus.ANALYZING, JobStatus.DOWNLOADING, JobStatus.PROCESSING):
            await self.cancel_job(job_id)

        if job.output_path and job.output_path.exists():
            try:
                job.output_path.unlink(missing_ok=True)
                logger.info(f"Deleted downloaded file for job [{job_id}]: {job.output_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file for job [{job_id}]: {e}")

        async with self._lock:
            self._jobs.pop(job_id, None)

    async def _process_job(self, job_id: str) -> None:
        """Worker executing download with concurrency limit and live progress parsing."""
        job = self.get_job(job_id)
        semaphore = self._get_semaphore()

        async with semaphore:
            if job.is_cancelled:
                return

            job.status = JobStatus.DOWNLOADING
            job.started_at = time.time()
            job.current_stage = "Starting download engine"
            job.emit_event()

            # Ensure directories and isolated temp dir
            FileService.ensure_directories()
            temp_dir = FileService.get_job_temp_dir(job_id)
            job.temp_dir = temp_dir

            # Build download arguments
            cmd = YtDlpService.build_download_command(
                url=job.url,
                temp_dir=temp_dir,
                resolution=job.resolution,
                audio_only=job.audio_only,
                audio_format=job.audio_format,
                output_container=job.output_container,
            )

            logger.info(f"Job [{job_id}] running command: {' '.join(cmd[:6])} ...")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                job.process = proc

                # Read output stream line by line to capture real-time progress
                stderr_output = []

                async def read_stdout():
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="ignore")
                        progress_info = YtDlpService.parse_progress_line(decoded)
                        if progress_info:
                            job.current_stage = progress_info.get("stage", job.current_stage)
                            job.progress = progress_info.get("progress", job.progress)
                            job.speed = progress_info.get("speed", job.speed)
                            job.eta = progress_info.get("eta", job.eta)
                            job.emit_event()

                async def read_stderr():
                    while True:
                        line = await proc.stderr.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="ignore")
                        stderr_output.append(decoded)

                # Run both readers concurrently with timeout
                await asyncio.wait_for(
                    asyncio.gather(read_stdout(), read_stderr(), proc.wait()),
                    timeout=float(settings.DOWNLOAD_TIMEOUT),
                )

                if job.is_cancelled:
                    return

                if proc.returncode != 0:
                    err_text = "".join(stderr_output)
                    user_msg = map_ytdlp_error(err_text)
                    logger.error(f"Job [{job_id}] failed with code {proc.returncode}: {err_text[:300]}")
                    job.status = JobStatus.FAILED
                    job.current_stage = "Failed"
                    job.error_message = user_msg
                    job.completed_at = time.time()
                    FileService.cleanup_temp_dir(temp_dir)
                    job.emit_event()
                    return

                # Locate the resulting file in the job's temporary directory
                candidates = [
                    f for f in temp_dir.iterdir()
                    if f.is_file() and not f.name.endswith(".part") and not f.name.endswith(".ytdl")
                ]

                if not candidates:
                    logger.error(f"Job [{job_id}] completed download but no output file found in {temp_dir}")
                    job.status = JobStatus.FAILED
                    job.current_stage = "Failed: file not created"
                    job.error_message = "Output file could not be verified after download."
                    job.completed_at = time.time()
                    FileService.cleanup_temp_dir(temp_dir)
                    job.emit_event()
                    return

                # Sort by size or modification time, take the media file
                downloaded_file = max(candidates, key=lambda f: f.stat().st_size)
                file_size = downloaded_file.stat().st_size

                # Verify file size against MAX_DOWNLOAD_SIZE
                if file_size > settings.max_download_size_bytes:
                    logger.warning(f"Job [{job_id}] file size {file_size} exceeds max allowed {settings.max_download_size_bytes}")
                    job.status = JobStatus.FAILED
                    job.current_stage = "File size limit exceeded"
                    job.error_message = "Downloaded media exceeds maximum allowed file size."
                    job.completed_at = time.time()
                    FileService.cleanup_temp_dir(temp_dir)
                    job.emit_event()
                    return

                # Sanitize filename and move to final downloads directory
                safe_name = FileService.sanitize_filename(downloaded_file.name)
                final_path = settings.download_path / f"{job_id}_{safe_name}"

                shutil.move(str(downloaded_file), str(final_path))
                logger.info(f"Job [{job_id}] successfully saved to: {final_path}")

                # Update job state
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.current_stage = "Completed"
                job.output_filename = safe_name
                job.output_filesize = file_size
                job.output_path = final_path
                job.completed_at = time.time()
                if not job.title:
                    job.title = downloaded_file.stem

                # Clean up temporary directory
                FileService.cleanup_temp_dir(temp_dir)
                job.emit_event()

            except asyncio.TimeoutError:
                logger.error(f"Job [{job_id}] timed out after {settings.DOWNLOAD_TIMEOUT} seconds.")
                if job.process:
                    try:
                        job.process.kill()
                    except Exception:
                        pass
                job.status = JobStatus.FAILED
                job.current_stage = "Download timed out"
                job.error_message = "Download timed out before completion."
                job.completed_at = time.time()
                FileService.cleanup_temp_dir(temp_dir)
                job.emit_event()

            except Exception as e:
                logger.exception(f"Unexpected error in job [{job_id}]: {e}")
                job.status = JobStatus.FAILED
                job.current_stage = "Internal processing failure"
                job.error_message = "Something went wrong while processing the download."
                job.completed_at = time.time()
                FileService.cleanup_temp_dir(temp_dir)
                job.emit_event()


job_manager = JobManager()
