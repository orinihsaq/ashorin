from typing import List
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.models.schemas import (
    BatchImportRequest,
    BatchImportResponse,
    BatchItemResult,
    DownloadConfig,
    DownloadRequest,
)
from app.repositories.profile_repository import ProfileRepository
from app.repositories.rule_repository import RuleRepository
from app.services.duplicate_detector import DuplicateDetector
from app.services.job_manager import job_manager
from app.services.security import SecurityService
from app.services.webhook_service import WebhookService
from app.utils.logger import logger

router = APIRouter(prefix="/api/batch", tags=["Batch Import"])


@router.post("/queue", response_model=BatchImportResponse)
async def queue_batch(req: BatchImportRequest):
    """
    Submits a batch of media URLs for automated background download.
    Deduplicates URLs, evaluates automation rules, applies selected profile,
    and enqueues jobs according to priority.
    """
    raw_urls = req.urls
    if not raw_urls:
        raise HTTPException(status_code=400, detail="No URLs provided in batch.")

    if len(raw_urls) > settings.MAX_BATCH_URLS:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_BATCH_URLS} URLs.",
        )

    # Resolve default or requested profile
    profile_data = None
    if req.profile_id:
        profile_data = ProfileRepository.get_profile(req.profile_id)
        if not profile_data:
            raise HTTPException(status_code=400, detail=f"Requested profile '{req.profile_id}' not found.")
    else:
        profile_data = ProfileRepository.get_default_profile()

    base_config = DownloadConfig(**profile_data.get("config", {}))

    results: List[BatchItemResult] = []
    seen_in_batch = set()
    accepted_count = 0
    dup_count = 0
    invalid_count = 0

    for raw_url in raw_urls:
        url = raw_url.strip()
        if not url:
            continue

        # SSRF / URL validation
        try:
            validated_url = SecurityService.validate_url(url)
        except Exception as e:
            invalid_count += 1
            results.append(
                BatchItemResult(
                    url=url,
                    valid=False,
                    error=f"Invalid URL: {str(e)}",
                )
            )
            continue

        norm_url = DuplicateDetector.normalize_url(validated_url)
        if norm_url in seen_in_batch:
            dup_count += 1
            results.append(
                BatchItemResult(
                    url=validated_url,
                    valid=False,
                    duplicate=True,
                    error="Duplicate URL in this batch submission",
                )
            )
            continue
        seen_in_batch.add(norm_url)

        # Check existing library / active job duplicates
        is_dup, dup_reason, _ = DuplicateDetector.check_duplicate(validated_url)
        if is_dup:
            dup_count += 1
            results.append(
                BatchItemResult(
                    url=validated_url,
                    valid=False,
                    duplicate=True,
                    error=f"Duplicate skipped: {dup_reason}",
                )
            )
            continue

        # Rule evaluation if profile wasn't explicitly forced
        target_cfg = base_config
        target_profile_id = profile_data.get("id", "recommended")
        if not req.profile_id:
            rule_match = RuleRepository.evaluate_rules(url=validated_url)
            if rule_match.get("matched") and rule_match.get("profile_id"):
                matched_prof = ProfileRepository.get_profile(rule_match["profile_id"])
                if matched_prof:
                    target_cfg = DownloadConfig(**matched_prof.get("config", {}))
                    target_profile_id = matched_prof.get("id")

        # Create download job
        try:
            download_req = DownloadRequest(
                url=validated_url,
                config=target_cfg,
                priority=req.priority or "NORMAL",
                profile_id=target_profile_id,
            )
            job = await job_manager.create_job(download_req)
            accepted_count += 1
            results.append(
                BatchItemResult(
                    url=validated_url,
                    valid=True,
                    job_id=job.id,
                    title=job.title,
                )
            )
        except Exception as e:
            logger.error(f"Error enqueuing batch URL {validated_url}: {e}")
            results.append(
                BatchItemResult(
                    url=validated_url,
                    valid=False,
                    error=str(e),
                )
            )

    resp = BatchImportResponse(
        total_submitted=len(raw_urls),
        total_accepted=accepted_count,
        duplicates_skipped=dup_count,
        invalid_urls=invalid_count,
        items=results,
    )

    # Emit webhook
    WebhookService.dispatch_event("batch.completed", resp.model_dump())
    return resp
