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

Supports:
- Task-specific webhook configurations
- Global webhook fallback (from AgentManifest)
- Persistent webhook storage for long-running tasks
- Artifact update notifications
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from bindu.common.protocol.types import (
    Artifact,
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

if TYPE_CHECKING:
    from bindu.server.storage.base import Storage

logger = get_logger("pebbling.server.notifications.push_manager")

PUSH_NOT_SUPPORTED_MESSAGE = (
    "Push notifications are not supported by this server configuration. Please use polling to check task status. "
    "See: GET /tasks/{id}"
)


@dataclass
class PushNotificationManager:
    """Manages push notifications for task lifecycle events.

    Supports:
    - Task-specific webhook configurations (in-memory and persistent)
    - Global webhook fallback from AgentManifest
    - Artifact update notifications
    - Lifecycle event notifications
    """

    manifest: Any | None = None
    storage: Storage | None = None
    notification_service: NotificationService = field(
        default_factory=NotificationService
    )
    _push_notification_configs: dict[uuid.UUID, PushNotificationConfig] = field(
        default_factory=dict, init=False
    )
    _notification_sequences: dict[uuid.UUID, int] = field(
        default_factory=dict, init=False
    )

    async def initialize(self) -> None:
        """Initialize the push notification manager.

        Loads persisted webhook configurations from storage to restore
        state after server restarts. Should be called during startup.
        """
        if self.storage is None:
            logger.debug("No storage configured, skipping webhook config initialization")
            return

        try:
            persisted_configs = await self.storage.load_all_webhook_configs()
            for task_id, config in persisted_configs.items():
                self._push_notification_configs[task_id] = config
                self._notification_sequences.setdefault(task_id, 0)

            if persisted_configs:
                logger.info(
                    f"Loaded {len(persisted_configs)} persisted webhook configurations"
                )
        except Exception as exc:
            logger.error(f"Failed to load persisted webhook configs: {exc}")

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

    def get_global_webhook_config(self) -> PushNotificationConfig | None:
        """Get the global webhook configuration from the manifest.

        Returns:
            Global webhook config if configured, None otherwise
        """
        if not self.manifest:
            return None

        global_url = getattr(self.manifest, "global_webhook_url", None)
        if not global_url:
            return None

        global_token = getattr(self.manifest, "global_webhook_token", None)

        config: dict[str, Any] = {
            "id": uuid.uuid4(),  # Generate ID for global config
            "url": global_url,
        }
        if global_token:
            config["token"] = global_token

        return cast(PushNotificationConfig, config)

    def get_effective_webhook_config(
        self, task_id: uuid.UUID
    ) -> PushNotificationConfig | None:
        """Get the effective webhook config for a task.

        Priority order:
        1. Task-specific webhook configuration
        2. Global webhook configuration from manifest

        Args:
            task_id: The task to get webhook config for

        Returns:
            The effective webhook config, or None if no config available
        """
        # First check task-specific config
        task_config = self._push_notification_configs.get(task_id)
        if task_config:
            return task_config

        # Fall back to global config
        return self.get_global_webhook_config()

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

    async def register_push_config(
        self, task_id: uuid.UUID, config: PushNotificationConfig, persist: bool = False
    ) -> None:
        """Register a push notification configuration for a task.

        Args:
            task_id: The task to register the config for
            config: The push notification configuration
            persist: If True, save to storage for long-running tasks
        """
        config_copy = self._sanitize_push_config(config)
        self.notification_service.validate_config(config_copy)
        self._push_notification_configs[task_id] = config_copy
        self._notification_sequences.setdefault(task_id, 0)

        if persist and self.storage is not None:
            await self.storage.save_webhook_config(task_id, config_copy)
            logger.debug(f"Persisted webhook config for task {task_id}")

    async def remove_push_config(
        self, task_id: uuid.UUID, delete_from_storage: bool = False
    ) -> PushNotificationConfig | None:
        """Remove push notification configuration for a task.

        Args:
            task_id: The task to remove the config for
            delete_from_storage: If True, also remove from persistent storage

        Returns:
            The removed config, or None if not found
        """
        self._notification_sequences.pop(task_id, None)
        config = self._push_notification_configs.pop(task_id, None)

        if delete_from_storage and self.storage is not None:
            await self.storage.delete_webhook_config(task_id)
            logger.debug(f"Deleted webhook config from storage for task {task_id}")

        return config

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
        """Send a lifecycle notification for a task.

        Uses get_effective_webhook_config to support global webhook fallback.
        """
        if not self.is_push_supported():
            return
        config = self.get_effective_webhook_config(task_id)
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

    def build_artifact_event(
        self, task_id: uuid.UUID, context_id: uuid.UUID, artifact: Artifact | dict[str, Any]
    ) -> dict[str, Any]:
        """Build an artifact update event payload for push notification."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "event_id": str(uuid.uuid4()),
            "sequence": self._next_sequence(task_id),
            "timestamp": timestamp,
            "kind": "artifact-update",
            "task_id": str(task_id),
            "context_id": str(context_id),
            "artifact": artifact,
        }

    async def notify_artifact(
        self, task_id: uuid.UUID, context_id: uuid.UUID, artifact: Artifact | dict[str, Any]
    ) -> None:
        """Send an artifact update notification for a task.

        Args:
            task_id: The task that produced the artifact
            context_id: The context of the task
            artifact: The artifact data to notify about
        """
        if not self.is_push_supported():
            return
        config = self.get_effective_webhook_config(task_id)
        if not config:
            return
        event = self.build_artifact_event(task_id, context_id, artifact)
        try:
            await self.notification_service.send_event(config, event)
        except NotificationDeliveryError as exc:
            logger.warning(
                "Artifact notification delivery failed",
                task_id=str(task_id),
                context_id=str(context_id),
                artifact_name=artifact.get("name") if isinstance(artifact, dict) else None,
                status=exc.status,
                message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Unexpected error delivering artifact notification",
                task_id=str(task_id),
                context_id=str(context_id),
                error=str(exc),
            )

    def schedule_notification(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> None:
        """Schedule a notification to be sent asynchronously.

        Uses get_effective_webhook_config to support global webhook fallback.
        """
        if not self.is_push_supported():
            return
        if self.get_effective_webhook_config(task_id) is None:
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
        self, request: SetTaskPushNotificationRequest, task_loader, persist: bool = False
    ) -> SetTaskPushNotificationResponse:
        """Set push notification settings for a task.

        Args:
            request: The JSON-RPC request
            task_loader: Async function to load a task by ID
            persist: Deprecated parameter, now reads from request params
        """
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

        # A2A Protocol: Read long_running flag from request params
        # If True, persist webhook config to survive server restarts
        is_long_running = params.get("long_running", False)

        try:
            await self.register_push_config(task_id, push_config, persist=is_long_running)
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
        self, request: DeleteTaskPushNotificationConfigRequest, delete_from_storage: bool = False
    ) -> DeleteTaskPushNotificationConfigResponse:
        """Delete a push notification configuration for a task.

        Args:
            request: The JSON-RPC request
            delete_from_storage: If True, also remove from persistent storage
        """
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

        removed = await self.remove_push_config(task_id, delete_from_storage=delete_from_storage)
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
