from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    WebhookCreateRequest,
    WebhookDeliveryModel,
    WebhookModel,
)
from app.repositories.webhook_repository import WebhookRepository
from app.services.security import SecurityService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.get("", response_model=List[WebhookModel])
async def list_webhooks():
    """Lists registered webhook endpoints."""
    raw = WebhookRepository.list_webhooks()
    return [WebhookModel(**w) for w in raw]


@router.post("", response_model=WebhookModel)
async def create_webhook(req: WebhookCreateRequest):
    """Registers a new webhook endpoint after validating against SSRF attacks."""
    try:
        SecurityService.validate_url(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {str(e)}")

    valid_events = {"job.started", "job.completed", "job.failed", "batch.completed", "*"}
    filtered_events = [e for e in req.events if e in valid_events]
    if not filtered_events:
        filtered_events = ["job.completed"]

    wid = WebhookRepository.create_webhook(
        url=req.url,
        events=filtered_events,
        signing_secret=req.signing_secret,
    )
    created = WebhookRepository.get_webhook(wid)
    return WebhookModel(**created)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Deletes a webhook and its delivery history."""
    success = WebhookRepository.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "success", "message": "Webhook deleted successfully."}


@router.get("/deliveries", response_model=List[WebhookDeliveryModel])
async def list_deliveries(
    webhook_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns recent webhook delivery logs."""
    logs = WebhookRepository.list_deliveries(webhook_id=webhook_id, limit=limit)
    return [WebhookDeliveryModel(**l) for l in logs]


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Dispatches a test event to verify endpoint connectivity."""
    import json
    import time
    webhook = WebhookRepository.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "test.ping",
        "timestamp": time.time(),
        "data": {
            "message": "ashoriN webhook verification ping",
            "webhook_id": webhook_id,
        },
    }
    payload_str = json.dumps(test_payload)
    await WebhookService._send_single_webhook(webhook, "test.ping", payload_str)
    return {"status": "success", "message": "Test ping dispatched."}
