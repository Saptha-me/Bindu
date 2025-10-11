"""Push notification delivery service for agent task events."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from bindu.common.protocol.types import PushNotificationConfig
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.notifications")


class NotificationDeliveryError(Exception):
    """Raised when a push notification cannot be delivered."""

    def __init__(self, status: int | None, message: str):
        """Initialize notification delivery error.

        Args:
            status: HTTP status code if available
            message: Error message
        """
        super().__init__(message)
        self.status = status


@dataclass
class NotificationService:
    """Deliver push notification events to configured HTTP endpoints."""

    timeout: float = 5.0
    max_retries: int = 2
    base_backoff: float = 0.5

    async def send_event(
        self, config: PushNotificationConfig, event: dict[str, Any]
    ) -> None:
        """Send an event to the configured HTTP webhook."""
        self.validate_config(config)

        payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
        headers = self._build_headers(config)

        await self._post_with_retries(config["url"], headers, payload, event)

    def validate_config(self, config: PushNotificationConfig) -> None:
        """Validate push notification configuration before use."""
        parsed = urlparse(config["url"])
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Push notification URL must use http or https scheme.")
        if not parsed.netloc:
            raise ValueError("Push notification URL must include a network location.")

    async def _post_with_retries(
        self, url: str, headers: dict[str, str], payload: bytes, event: dict[str, Any]
    ) -> None:
        attempt = 0
        backoff = self.base_backoff
        last_error: NotificationDeliveryError | None = None

        while attempt <= self.max_retries:
            try:
                status = await asyncio.to_thread(self._post_once, url, headers, payload)
                logger.debug(
                    "Delivered push notification",
                    event_id=event.get("event_id"),
                    task_id=event.get("task_id"),
                    status=status,
                )
                return
            except NotificationDeliveryError as exc:
                last_error = exc
                if (
                    exc.status is not None
                    and 400 <= exc.status < 500
                    and exc.status != 429
                ):
                    logger.warning(
                        "Dropping push notification due to client error",
                        event_id=event.get("event_id"),
                        task_id=event.get("task_id"),
                        status=exc.status,
                        message=str(exc),
                    )
                    raise

            attempt += 1
            if attempt > self.max_retries:
                break

            logger.debug(
                "Retrying push notification delivery",
                event_id=event.get("event_id"),
                task_id=event.get("task_id"),
                attempt=attempt,
            )
            await asyncio.sleep(backoff)
            backoff *= 2

        if last_error is None:
            last_error = NotificationDeliveryError(None, "Unknown delivery failure")

        logger.error(
            "Failed to deliver push notification after retries",
            event_id=event.get("event_id"),
            task_id=event.get("task_id"),
            status=last_error.status,
            message=str(last_error),
        )
        raise last_error

    def _post_once(self, url: str, headers: dict[str, str], payload: bytes) -> int:
        req = request.Request(url, data=payload, method="POST")
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            # URL scheme is validated in validate_config() to only allow http/https
            with request.urlopen(req, timeout=self.timeout) as response:  # nosec B310
                status = response.getcode()
                if 200 <= status < 300:
                    return status
                raise NotificationDeliveryError(
                    status, f"Unexpected status code: {status}"
                )
        except error.HTTPError as exc:
            status = exc.code
            body = b""
            try:
                body = exc.read() or b""
            except Exception:
                body = b""
            message = body.decode("utf-8", errors="ignore").strip()
            raise NotificationDeliveryError(
                status, message or f"HTTP error {status}"
            ) from exc
        except error.URLError as exc:
            raise NotificationDeliveryError(
                None, f"Connection error: {exc.reason}"
            ) from exc

    def _build_headers(self, config: PushNotificationConfig) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
