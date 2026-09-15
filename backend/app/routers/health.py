from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    HealthIssueModel,
    HealthRepairRequest,
    HealthScanModel,
    StorageForecastResponse,
)
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService
from app.utils.formatting import format_bytes

router = APIRouter(prefix="/api/health", tags=["Media Health Center"])


@router.get("", response_model=Optional[HealthScanModel])
async def get_latest_health_scan():
    """Retrieves the latest audit scan results."""
    scan = HealthRepository.get_latest_scan()
    if not scan:
        return None
    scan["storage_recoverable_formatted"] = format_bytes(scan.get("storage_recoverable_bytes", 0))
    return HealthScanModel(**scan)


@router.post("/scan", response_model=HealthScanModel)
async def trigger_health_scan():
    """Triggers an immediate audit scan of library records and disk storage."""
    scan = await HealthService.scan_library()
    return scan


@router.get("/issues", response_model=List[HealthIssueModel])
async def list_health_issues(
    scan_id: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    unresolved_only: bool = Query(True),
):
    """Lists detected health issues with optional filtering."""
    issues = HealthRepository.list_issues(
        scan_id=scan_id, unresolved_only=unresolved_only, issue_type=issue_type
    )
    return [HealthIssueModel(**i) for i in issues]


@router.post("/repair")
async def repair_health_issues(req: HealthRepairRequest):
    """Safely repairs specified health issues or all issues of a certain type."""
    result = await HealthService.repair_issues(
        issue_ids=req.issue_ids, repair_type=req.repair_type
    )
    return result


@router.get("/forecast", response_model=StorageForecastResponse)
async def get_storage_forecast():
    """Calculates disk consumption rates and forecast until low space threshold."""
    return HealthService.get_storage_forecast()
