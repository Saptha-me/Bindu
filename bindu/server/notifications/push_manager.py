# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Push Notification Manager for Bindu Task System.

This module handles all push notification functionality for task lifecycle events.
It manages notification configurations, delivery, sequencing, and error handling.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from bindu.common.protocol.types import (
    DeleteTaskPushNotificationConfigRequest,
    DeleteTaskPushNotificationConfigResponse,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    ListTaskPushNotificationConfigRequest,
    ListTaskPushNotificationConfigResponse,
    PushNotificationConfig,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    TaskNotFoundError,
    TaskPushNotificationConfig,
)

from ...utils.logging import get_logger
from ...utils.notifications import NotificationDeliveryError, NotificationService

logger = get_logger("pebbling.server.notifications.push_manager")

PUSH_NOT_SUPPORTED_MESSAGE = (
    "Push notifications are not supported by this server configuration. Please use polling to check task status. "
    "See: GET /tasks/{id}"
)


@dataclass
class PushNotificationManager:
    """Manages push notifications for task lifecycle events."""

    manifest: Any | None = None
    notification_service: NotificationService = field(
        default_factory=NotificationService
    )
    _push_notification_configs: dict[uuid.UUID, PushNotificationConfig] = field(
        default_factory=dict, init=False
    )
    _notification_sequences: dict[uuid.UUID, int] = field(
        default_factory=dict, init=False
    )

    def is_push_supported(self) -> bool:
        """Check if push notifications are supported by the manifest."""
        if not self.manifest:
            return False
        capabilities = getattr(self.manifest, "capabilities", None)
        if not capabilities:
            return False
        if isinstance(capabilities, dict):
            return bool(capabilities.get("push_notifications"))
        return bool(getattr(capabilities, "push_notifications", False))

    def _sanitize_push_config(
        self, config: PushNotificationConfig
    ) -> PushNotificationConfig:
        """Sanitize push notification config to only include allowed fields."""
        sanitized: dict[str, Any] = {"id": config["id"], "url": config["url"]}
        token = config.get("token")
        if token is not None:
            sanitized["token"] = token
        authentication = config.get("authentication")
        if authentication is not None:
            sanitized["authentication"] = authentication
        return cast(PushNotificationConfig, sanitized)

    def register_push_config(
        self, task_id: uuid.UUID, config: PushNotificationConfig
    ) -> None:
        """Register a push notification configuration for a task."""
        config_copy = self._sanitize_push_config(config)
        self.notification_service.validate_config(config_copy)
        self._push_notification_configs[task_id] = config_copy
        self._notification_sequences.setdefault(task_id, 0)

    def remove_push_config(self, task_id: uuid.UUID) -> PushNotificationConfig | None:
        """Remove push notification configuration for a task."""
        self._notification_sequences.pop(task_id, None)
        return self._push_notification_configs.pop(task_id, None)

    def get_push_config(self, task_id: uuid.UUID) -> PushNotificationConfig | None:
        """Get push notification configuration for a task."""
        return self._push_notification_configs.get(task_id)

    def build_task_push_config(self, task_id: uuid.UUID) -> TaskPushNotificationConfig:
        """Build a TaskPushNotificationConfig response."""
        config = self._push_notification_configs.get(task_id)
        if config is None:
            raise KeyError("No push notification configuration for task")
        return TaskPushNotificationConfig(
            id=task_id,
            push_notification_config=self._sanitize_push_config(config),
        )

    def _next_sequence(self, task_id: uuid.UUID) -> int:
        """Get the next sequence number for a task's notifications."""
        current = self._notification_sequences.get(task_id, 0) + 1
        self._notification_sequences[task_id] = current
        return current

    def build_lifecycle_event(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> dict[str, Any]:
        """Build a lifecycle event payload for push notification."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "event_id": str(uuid.uuid4()),
            "sequence": self._next_sequence(task_id),
            "timestamp": timestamp,
            "kind": "status-update",
            "task_id": str(task_id),
            "context_id": str(context_id),
            "status": {"state": state, "timestamp": timestamp},
            "final": final,
        }

    async def notify_lifecycle(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> None:
        """Send a lifecycle notification for a task."""
        if not self.is_push_supported():
            return
        config = self._push_notification_configs.get(task_id)
        if not config:
            return
        event = self.build_lifecycle_event(task_id, context_id, state, final)
        try:
            await self.notification_service.send_event(config, event)
        except NotificationDeliveryError as exc:
            logger.warning(
                "Push notification delivery failed",
                task_id=str(task_id),
                context_id=str(context_id),
                state=state,
                status=exc.status,
                message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Unexpected error delivering push notification",
                task_id=str(task_id),
                context_id=str(context_id),
                state=state,
                error=str(exc),
            )

    def schedule_notification(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> None:
        """Schedule a notification to be sent asynchronously."""
        if not self.is_push_supported():
            return
        if task_id not in self._push_notification_configs:
            return
        asyncio.create_task(self.notify_lifecycle(task_id, context_id, state, final))

    def _jsonrpc_error(
        self, response_class: type, request_id: Any, message: str, code: int = -32001
    ):
        """Create a JSON-RPC error response."""
        return response_class(
            jsonrpc="2.0", id=request_id, error={"code": code, "message": message}
        )

    def _push_not_supported_response(self, response_class: type, request_id: Any):
        """Create a 'push not supported' error response."""
        return response_class(
            jsonrpc="2.0",
            id=request_id,
            error={"code": -32005, "message": PUSH_NOT_SUPPORTED_MESSAGE},
        )

    def _create_error_response(
        self, response_class: type, request_id: str, error_class: type, message: str
    ) -> Any:
        """Create a standardized error response."""
        return response_class(
            jsonrpc="2.0",
            id=request_id,
            error=error_class(code=-32001, message=message),
        )

    async def set_task_push_notification(
        self, request: SetTaskPushNotificationRequest, task_loader
    ) -> SetTaskPushNotificationResponse:
        """Set push notification settings for a task."""
        if not self.is_push_supported():
            return self._push_not_supported_response(
                SetTaskPushNotificationResponse, request["id"]
            )

        params = request["params"]
        task_id = params["id"]
        push_config = cast(
            PushNotificationConfig, dict(params["push_notification_config"])
        )

        task = await task_loader(task_id)
        if task is None:
            return self._create_error_response(
                SetTaskPushNotificationResponse,
                request["id"],
                TaskNotFoundError,
                "Task not found",
            )

        try:
            self.register_push_config(task_id, push_config)
        except ValueError as exc:
            return self._jsonrpc_error(
                SetTaskPushNotificationResponse,
                request["id"],
                f"Invalid push notification configuration: {exc}",
            )

        logger.debug(
            "Registered push notification subscriber",
            task_id=str(task_id),
            subscriber=str(push_config.get("id")),
        )
        return SetTaskPushNotificationResponse(
            jsonrpc="2.0",
            id=request["id"],
            result=self.build_task_push_config(task_id),
        )

    async def get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        """Get push notification settings for a task."""
        if not self.is_push_supported():
            return self._push_not_supported_response(
                GetTaskPushNotificationResponse, request["id"]
            )

        task_id = request["params"]["task_id"]
        if task_id not in self._push_notification_configs:
            return self._jsonrpc_error(
                GetTaskPushNotificationResponse,
                request["id"],
                "Push notification configuration not found for task.",
            )

        return GetTaskPushNotificationResponse(
            jsonrpc="2.0",
            id=request["id"],
            result=self.build_task_push_config(task_id),
        )

    async def list_task_push_notifications(
        self, request: ListTaskPushNotificationConfigRequest
    ) -> ListTaskPushNotificationConfigResponse:
        """List push notification configurations for a task."""
        if not self.is_push_supported():
            return self._push_not_supported_response(
                ListTaskPushNotificationConfigResponse, request["id"]
            )

        task_id = request["params"]["id"]
        if task_id not in self._push_notification_configs:
            return self._jsonrpc_error(
                ListTaskPushNotificationConfigResponse,
                request["id"],
                "Push notification configuration not found for task.",
            )

        return ListTaskPushNotificationConfigResponse(
            jsonrpc="2.0",
            id=request["id"],
            result=self.build_task_push_config(task_id),
        )

    async def delete_task_push_notification(
        self, request: DeleteTaskPushNotificationConfigRequest
    ) -> DeleteTaskPushNotificationConfigResponse:
        """Delete a push notification configuration for a task."""
        if not self.is_push_supported():
            return self._push_not_supported_response(
                DeleteTaskPushNotificationConfigResponse, request["id"]
            )

        params = request["params"]
        task_id = params["id"]
        config_id = params["push_notification_config_id"]

        existing = self._push_notification_configs.get(task_id)
        if existing is None:
            return self._jsonrpc_error(
                DeleteTaskPushNotificationConfigResponse,
                request["id"],
                "Push notification configuration not found for task.",
            )

        if existing.get("id") != config_id:
            return self._jsonrpc_error(
                DeleteTaskPushNotificationConfigResponse,
                request["id"],
                "Push notification configuration identifier mismatch.",
            )

        removed = self.remove_push_config(task_id)
        if removed is None:
            return self._jsonrpc_error(
                DeleteTaskPushNotificationConfigResponse,
                request["id"],
                "Push notification configuration not found for task.",
            )

        logger.debug(
            "Removed push notification subscriber",
            task_id=str(task_id),
            subscriber=str(config_id),
        )

        return DeleteTaskPushNotificationConfigResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "id": task_id,
                "push_notification_config": self._sanitize_push_config(removed),
            },
        )
