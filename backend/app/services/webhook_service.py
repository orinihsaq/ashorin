import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
import httpx
from app.config import settings
from app.repositories.webhook_repository import WebhookRepository
from app.services.security import SecurityService
from app.utils.logger import logger


class WebhookService:
    @classmethod
    async def _send_single_webhook(cls, webhook: Dict[str, Any], event: str, payload_str: str) -> None:
        webhook_id = webhook["id"]
        url = webhook["url"]
        signing_secret = webhook.get("signing_secret")

        # 1. SSRF check
        try:
            SecurityService.validate_url(url)
        except Exception as e:
            logger.warning(f"Webhook {webhook_id} SSRF check blocked: {e}")
            WebhookRepository.log_delivery(
                webhook_id=webhook_id,
                event=event,
                payload_summary=payload_str[:200],
                status_code=None,
                success=False,
                attempt_count=1,
                error_message=f"SSRF block: {str(e)}",
            )
            return

        # 2. Build headers & HMAC
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"ashoriN-MediaAutomation/{settings.APP_VERSION}",
            "X-ashoriN-Event": event,
        }
        if signing_secret:
            sig = hmac.new(
                signing_secret.encode("utf-8"),
                payload_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-ashoriN-Signature"] = f"sha256={sig}"

        # 3. HTTP POST
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=False) as client:
                resp = await client.post(url, content=payload_str.encode("utf-8"), headers=headers)
                success = 200 <= resp.status_code < 300
                WebhookRepository.log_delivery(
                    webhook_id=webhook_id,
                    event=event,
                    payload_summary=payload_str[:200],
                    status_code=resp.status_code,
                    success=success,
                    attempt_count=1,
                    error_message=None if success else f"HTTP status {resp.status_code}",
                )
        except Exception as e:
            logger.warning(f"Webhook delivery failed for {webhook_id} ({url}): {e}")
            WebhookRepository.log_delivery(
                webhook_id=webhook_id,
                event=event,
                payload_summary=payload_str[:200],
                status_code=None,
                success=False,
                attempt_count=1,
                error_message=str(e),
            )

    @classmethod
    async def dispatch_event_async(cls, event: str, data: Dict[str, Any]) -> None:
        """Dispatches an event payload to all matching registered webhooks."""
        if not settings.ENABLE_WEBHOOKS:
            return

        try:
            webhooks = WebhookRepository.list_webhooks()
            matching = [
                w for w in webhooks
                if w.get("is_enabled", True) and (event in w.get("events", []) or "*" in w.get("events", []))
            ]
            if not matching:
                return

            payload = {
                "event": event,
                "timestamp": time.time(),
                "data": data,
            }
            payload_str = json.dumps(payload, default=str)

            tasks = [cls._send_single_webhook(w, event, payload_str) for w in matching]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error dispatching webhook event '{event}': {e}")

    @classmethod
    def dispatch_event(cls, event: str, data: Dict[str, Any]) -> None:
        """Schedules asynchronous dispatch without blocking."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cls.dispatch_event_async(event, data))
        except RuntimeError:
            pass  # No running loop (e.g. during sync shutdown)
