# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""The bindu Task Manager: A Burger Restaurant Architecture.

This module defines the TaskManager - the Restaurant Manager of our AI agent ecosystem.
Think of it like running a high-end burger restaurant where customers place orders,
and we coordinate the entire kitchen operation to deliver perfect results.

Restaurant Components

- TaskManager (Restaurant Manager): Coordinates the entire operation, handles customer requests
- Scheduler (Order Queue System): Manages the flow of orders to the kitchen
- Worker (Chef): Actually cooks the burgers (executes AI agent tasks)
- Runner (Recipe Book): Defines how each dish is prepared and plated
- Storage (Restaurant Database): Keeps track of orders, ingredients, and completed dishes

Restaurant Architecture

  +-----------------+
  |   Front Desk    |  Customer Interface
  |  (HTTP Server)  |     (Takes Orders)
  +-------+---------+
          |
          | Order Placed
          v
  +-------+---------+
  |                 |  Restaurant Manager
  |   TaskManager   |     (Coordinates Everything)
  |   (Manager)     |<-----------------+
  +-------+---------+                  |
          |                            |
          | Send to Kitchen         | Track Everything
          v                            v
  +------------------+         +----------------+
  |                  |         |                |  Restaurant Database
  |    Scheduler     |         |    Storage     |     (Orders & History)
  |  (Order Queue)   |         |  (Database)    |
  +------------------+         +----------------+
          |                            ^
          | Kitchen Ready              |
          v                            | Update Status
  +------------------+                 |
  |                  |                 |  Head Chef
  |     Worker       |-----------------+     (Executes Tasks)
  |     (Chef)       |
  +------------------+
          |
          | Follow Recipe
          v
  +------------------+
  |     Runner       |  Recipe Book
  |  (Recipe Book)   |     (Task Execution Logic)
  +------------------+

"""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from bindu.common.protocol.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    ClearContextsRequest,
    ClearContextsResponse,
    ContextNotFoundError,
    DeleteTaskPushNotificationConfigRequest,
    DeleteTaskPushNotificationConfigResponse,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    GetTaskRequest,
    GetTaskResponse,
    ListContextsRequest,
    ListContextsResponse,
    ListTaskPushNotificationConfigRequest,
    ListTaskPushNotificationConfigResponse,
    ListTasksRequest,
    ListTasksResponse,
    PushNotificationConfig,
    ResubscribeTaskRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    StreamMessageRequest,
    Task,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
    TaskNotCancelableError,
    TaskNotFoundError,
    TaskPushNotificationConfig,
    TaskSendParams,
)
from bindu.settings import app_settings

from ..utils.logging import get_logger
from ..utils.notifications import NotificationDeliveryError, NotificationService
from ..utils.task_telemetry import (
    trace_context_operation,
    trace_task_operation,
    track_active_task,
)
from .scheduler import Scheduler
from .storage import Storage
from .workers import ManifestWorker

logger = get_logger("pebbling.server.task_manager")

PUSH_NOT_SUPPORTED_MESSAGE = (
    "Push notifications are not supported by this server configuration. Please use polling to check task status. "
    "See: GET /tasks/{id}"
)


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks and coordinating the AI agent ecosystem."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None  # AgentManifest for creating workers

    _aexit_stack: AsyncExitStack | None = field(default=None, init=False)
    _workers: list[ManifestWorker] = field(default_factory=list, init=False)
    notification_service: NotificationService = field(
        default_factory=NotificationService
    )
    _push_notification_configs: dict[uuid.UUID, PushNotificationConfig] = field(
        default_factory=dict, init=False
    )
    _notification_sequences: dict[uuid.UUID, int] = field(
        default_factory=dict, init=False
    )

    async def __aenter__(self) -> TaskManager:
        """Initialize the task manager and start all components."""
        self._aexit_stack = AsyncExitStack()
        await self._aexit_stack.__aenter__()
        await self._aexit_stack.enter_async_context(self.scheduler)

        if self.manifest:
            worker = ManifestWorker(
                scheduler=self.scheduler,
                storage=self.storage,
                manifest=self.manifest,
                lifecycle_notifier=self._notify_lifecycle,
            )
            self._workers.append(worker)
            await self._aexit_stack.enter_async_context(worker.run())

        return self

    @property
    def is_running(self) -> bool:
        """Check if the task manager is currently running."""
        return self._aexit_stack is not None

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Clean up resources and stop all components."""
        if self._aexit_stack is None:
            raise RuntimeError("TaskManager was not properly initialized.")
        await self._aexit_stack.__aexit__(exc_type, exc_value, traceback)
        self._aexit_stack = None

    def _create_error_response(
        self, response_class: type, request_id: str, error_class: type, message: str
    ) -> Any:
        """Create a standardized error response."""
        return response_class(
            jsonrpc="2.0",
            id=request_id,
            error=error_class(code=-32001, message=message),
        )

    def _parse_context_id(self, context_id: Any) -> uuid.UUID:
        """Parse and validate context_id, generating a new one if needed."""
        if context_id is None:
            return uuid.uuid4()
        if isinstance(context_id, str):
            return uuid.UUID(context_id)
        if isinstance(context_id, uuid.UUID):
            return context_id
        return uuid.uuid4()

    def _push_supported(self) -> bool:
        if not self.manifest:
            return False
        capabilities = getattr(self.manifest, "capabilities", None)
        if not capabilities:
            return False
        if isinstance(capabilities, dict):
            return bool(capabilities.get("push_notifications"))
        return bool(getattr(capabilities, "push_notifications", False))

    def _push_not_supported_response(self, response_class: type, request_id: Any):
        return response_class(
            jsonrpc="2.0",
            id=request_id,
            error={"code": -32005, "message": PUSH_NOT_SUPPORTED_MESSAGE},
        )

    def _sanitize_push_config(
        self, config: PushNotificationConfig
    ) -> PushNotificationConfig:
        sanitized: dict[str, Any] = {"id": config["id"], "url": config["url"]}
        token = config.get("token")
        if token is not None:
            sanitized["token"] = token
        authentication = config.get("authentication")
        if authentication is not None:
            sanitized["authentication"] = authentication
        return cast(PushNotificationConfig, sanitized)

    def _register_push_config(
        self, task_id: uuid.UUID, config: PushNotificationConfig
    ) -> None:
        config_copy = self._sanitize_push_config(config)
        self.notification_service.validate_config(config_copy)
        self._push_notification_configs[task_id] = config_copy
        self._notification_sequences.setdefault(task_id, 0)

    def _remove_push_config(self, task_id: uuid.UUID) -> PushNotificationConfig | None:
        self._notification_sequences.pop(task_id, None)
        return self._push_notification_configs.pop(task_id, None)

    def _build_task_push_config(self, task_id: uuid.UUID) -> TaskPushNotificationConfig:
        config = self._push_notification_configs.get(task_id)
        if config is None:
            raise KeyError("No push notification configuration for task")
        return TaskPushNotificationConfig(
            id=task_id,
            push_notification_config=self._sanitize_push_config(config),
        )

    def _next_sequence(self, task_id: uuid.UUID) -> int:
        current = self._notification_sequences.get(task_id, 0) + 1
        self._notification_sequences[task_id] = current
        return current

    def _build_lifecycle_event(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> dict[str, Any]:
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

    async def _notify_lifecycle(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> None:
        if not self._push_supported():
            return
        config = self._push_notification_configs.get(task_id)
        if not config:
            return
        event = self._build_lifecycle_event(task_id, context_id, state, final)
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

    def _schedule_notification(
        self, task_id: uuid.UUID, context_id: uuid.UUID, state: str, final: bool
    ) -> None:
        if not self._push_supported():
            return
        if task_id not in self._push_notification_configs:
            return
        asyncio.create_task(self._notify_lifecycle(task_id, context_id, state, final))

    def _jsonrpc_error(
        self, response_class: type, request_id: Any, message: str, code: int = -32001
    ):
        return response_class(
            jsonrpc="2.0", id=request_id, error={"code": code, "message": message}
        )

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol."""
        message = request["params"]["message"]
        context_id = self._parse_context_id(message.get("context_id"))

        task: Task = await self.storage.submit_task(context_id, message)

        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("get_task")
    async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Get a task and return it to the client."""
        task_id = request["params"]["task_id"]
        history_length = request["params"].get("history_length")
        task = await self.storage.load_task(task_id, history_length)

        if task is None:
            return self._create_error_response(
                GetTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        return GetTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("cancel_task")
    @track_active_task
    async def cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        """Cancel a running task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self._create_error_response(
                CancelTaskResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        # Check if task is in a cancelable state
        current_state = task["status"]["state"]

        if current_state in app_settings.agent.terminal_states:
            return self._create_error_response(
                CancelTaskResponse,
                request["id"],
                TaskNotCancelableError,
                f"Task cannot be canceled in '{current_state}' state. "
                f"Tasks can only be canceled while pending or running.",
            )

        # Cancel the task
        await self.scheduler.cancel_task(request["params"])
        task = await self.storage.load_task(task_id)

        return CancelTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events.

        This method returns a StreamingResponse directly to support SSE,
        which will be handled at the application layer.
        """
        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self._parse_context_id(message.get("context_id"))

        # similar to the "messages/send flow submit the task to the configured storage"
        task: Task = await self.storage.submit_task(context_id, message)

        async def stream_generator():
            """Generate a consumable stream based on the function which was decorated using pebblify."""
            try:
                await self.storage.update_task(task["id"], state="working")
                # yield the initial status update event to indicate processing of the task has started
                status_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "working",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": False,
                }
                yield f"data: {json.dumps(status_event)}\n\n"

                if self._workers and self.manifest:
                    worker = self._workers[0]
                    message_history = await worker._build_complete_message_history(task)
                    manifest_result = self.manifest.run(message_history)

                    if inspect.isasyncgen(manifest_result):
                        async for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    elif inspect.isgenerator(manifest_result):
                        for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    else:
                        if manifest_result:
                            artifact_event = {
                                "kind": "artifact-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "artifact": {
                                    "artifact_id": str(uuid.uuid4()),
                                    "name": "response",
                                    "parts": [
                                        {"kind": "text", "text": str(manifest_result)}
                                    ],
                                },
                                "last_chunk": True,
                            }
                            yield f"data: {json.dumps(artifact_event)}\n\n"

                # Send completion status
                completion_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "completed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                }
                yield f"data: {json.dumps(completion_event)}\n\n"

                # Update task state in storage
                await self.storage.update_task(task["id"], state="completed")
            except Exception as e:
                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await self.storage.update_task(task["id"], state="failed")

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    async def set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        """Set push notification settings for a task."""
        if not self._push_supported():
            return self._push_not_supported_response(
                SetTaskPushNotificationResponse, request["id"]
            )

        params = request["params"]
        task_id = params["id"]
        push_config = cast(
            PushNotificationConfig, dict(params["push_notification_config"])
        )

        task = await self.storage.load_task(task_id)
        if task is None:
            return self._create_error_response(
                SetTaskPushNotificationResponse,
                request["id"],
                TaskNotFoundError,
                "Task not found",
            )

        try:
            self._register_push_config(task_id, push_config)
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
            result=self._build_task_push_config(task_id),
        )

    async def get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        """Get push notification settings for a task."""
        if not self._push_supported():
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
            result=self._build_task_push_config(task_id),
        )

    async def list_task_push_notifications(
        self, request: ListTaskPushNotificationConfigRequest
    ) -> ListTaskPushNotificationConfigResponse:
        """List push notification configurations for a task."""
        if not self._push_supported():
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
            result=self._build_task_push_config(task_id),
        )

    async def delete_task_push_notification(
        self, request: DeleteTaskPushNotificationConfigRequest
    ) -> DeleteTaskPushNotificationConfigResponse:
        """Delete a push notification configuration for a task."""
        if not self._push_supported():
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

        removed = self._remove_push_config(task_id)
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

    @trace_task_operation("list_tasks", include_params=False)
    async def list_tasks(self, request: ListTasksRequest) -> ListTasksResponse:
        """List all tasks in storage."""
        tasks = await self.storage.list_tasks(request["params"].get("length"))

        if tasks is None:
            return self._create_error_response(
                ListTasksResponse, request["id"], TaskNotFoundError, "No tasks found"
            )

        return ListTasksResponse(jsonrpc="2.0", id=request["id"], result=tasks)

    @trace_context_operation("list_contexts")
    async def list_contexts(self, request: ListContextsRequest) -> ListContextsResponse:
        """List all contexts in storage."""
        contexts = await self.storage.list_contexts(request["params"].get("length"))

        if contexts is None:
            return self._create_error_response(
                ListContextsResponse,
                request["id"],
                ContextNotFoundError,
                "No contexts found",
            )

        return ListContextsResponse(jsonrpc="2.0", id=request["id"], result=contexts)

    @trace_context_operation("clear_context")
    async def clear_context(
        self, request: ClearContextsRequest
    ) -> ClearContextsResponse:
        """Clear a context from storage."""
        context_id = request["params"].get("context_id")

        try:
            await self.storage.clear_context(context_id)
        except ValueError as e:
            # Context not found
            return self._create_error_response(
                ClearContextsResponse, request["id"], ContextNotFoundError, str(e)
            )

        return ClearContextsResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "message": f"Context {context_id} and all associated tasks cleared successfully"
            },
        )

    @trace_task_operation("task_feedback")
    async def task_feedback(self, request: TaskFeedbackRequest) -> TaskFeedbackResponse:
        """Submit feedback for a completed task."""
        task_id = request["params"]["task_id"]
        task = await self.storage.load_task(task_id)

        if task is None:
            return self._create_error_response(
                TaskFeedbackResponse, request["id"], TaskNotFoundError, "Task not found"
            )

        feedback_data = {
            "task_id": task_id,
            "feedback": request["params"]["feedback"],
            "rating": request["params"]["rating"],
            "metadata": request["params"]["metadata"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if hasattr(self.storage, "store_task_feedback"):
            await self.storage.store_task_feedback(task_id, feedback_data)

        return TaskFeedbackResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "message": "Feedback submitted successfully",
                "task_id": str(task_id),
            },
        )

    async def resubscribe_task(self, request: ResubscribeTaskRequest) -> None:
        """Resubscribe to task updates."""
        raise NotImplementedError("Resubscribe is not implemented yet.")
