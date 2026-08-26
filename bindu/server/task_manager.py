# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
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
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from bindu.common.protocol.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    ClearContextsRequest,
    ClearContextsResponse,
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
    SendMessageRequest,
    SendMessageResponse,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    StreamMessageRequest,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
)

from ..utils.logging import get_logger
from .errors import MalformedContextIdError
from .handlers import ContextHandlers, MessageHandlers, TaskHandlers
from .notifications import PushNotificationManager
from .scheduler import Scheduler
from .storage import Storage
from .workers import ManifestWorker

logger = get_logger("pebbling.server.task_manager")

# Constants
JSONRPC_VERSION = "2.0"
DEFAULT_JSONRPC_ERROR_CODE = -32001


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks and coordinating the AI agent ecosystem."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None  # AgentManifest for creating workers

    _aexit_stack: AsyncExitStack | None = field(default=None, init=False)
    _workers: list[ManifestWorker] = field(default_factory=list, init=False)
    _reconciliation_task: asyncio.Task | None = field(default=None, init=False)
    _push_manager: PushNotificationManager = field(init=False)
    _message_handlers: MessageHandlers = field(init=False)
    _task_handlers: TaskHandlers = field(init=False)
    _context_handlers: ContextHandlers = field(init=False)

    def __post_init__(self) -> None:
        """Initialize push notification manager after dataclass initialization."""
        self._push_manager = PushNotificationManager(
            manifest=self.manifest,
            storage=self.storage,
        )

    async def __aenter__(self) -> TaskManager:
        """Initialize the task manager and start all components."""
        self._aexit_stack = AsyncExitStack()
        await self._aexit_stack.__aenter__()
        await self._aexit_stack.enter_async_context(self.scheduler)

        # Initialize push notification manager (loads persisted webhook configs)
        await self._push_manager.initialize()

        if self.manifest:
            worker = ManifestWorker(
                scheduler=self.scheduler,
                storage=self.storage,
                manifest=self.manifest,
                lifecycle_notifier=self._push_manager.notify_lifecycle,
            )
            self._workers.append(worker)
            await self._aexit_stack.enter_async_context(worker.run())

            # Start background x402 payment reconciliation loop
            from .workers.x402_reconciliation import run_x402_reconciliation_loop

            self._reconciliation_task = asyncio.create_task(
                run_x402_reconciliation_loop(self.storage),
                name="x402-reconciliation-loop",
            )

        # Initialize handlers after workers are created
        self._message_handlers = MessageHandlers(
            scheduler=self.scheduler,
            storage=self.storage,
            manifest=self.manifest,
            workers=self._workers,
            context_id_parser=self._parse_context_id,
            push_manager=self._push_manager,
            error_response_creator=self._create_error_response,
        )
        self._task_handlers = TaskHandlers(
            scheduler=self.scheduler,
            storage=self.storage,
            error_response_creator=self._create_error_response,
        )
        self._context_handlers = ContextHandlers(
            storage=self.storage,
            error_response_creator=self._create_error_response,
        )

        return self

    @property
    def is_running(self) -> bool:
        """Check if the task manager is currently running."""
        return self._aexit_stack is not None

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Clean up resources and stop all components."""
        if self._reconciliation_task:
            self._reconciliation_task.cancel()
            try:
                await self._reconciliation_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning("x402 reconciliation task exited with error: %s", e)
            self._reconciliation_task = None

        if self._aexit_stack is None:
            raise RuntimeError("TaskManager was not properly initialized.")
        await self._aexit_stack.__aexit__(exc_type, exc_value, traceback)
        self._aexit_stack = None

    def _create_error_response(
        self,
        response_class: type,
        request_id: str,
        error_class: type,
        message: str,
        code: int = DEFAULT_JSONRPC_ERROR_CODE,
    ) -> Any:
        """Create a standardized error response."""
        return response_class(
            jsonrpc=JSONRPC_VERSION,
            id=request_id,
            error=error_class(code=code, message=message),
        )

    def _parse_context_id(self, context_id: Any) -> uuid.UUID:
        """Parse and validate context_id.

        Returns a fresh UUID only when the client omitted ``context_id``
        (i.e. starting a new conversation). A malformed string raises
        ``MalformedContextIdError`` so the caller surfaces JSON-RPC -32602
        instead of fabricating a new context — see the explanation on the
        exception class.
        """
        if context_id is None:
            return uuid.uuid4()

        if isinstance(context_id, uuid.UUID):
            return context_id

        if isinstance(context_id, str):
            try:
                return uuid.UUID(context_id)
            except ValueError as exc:
                logger.warning(
                    "Rejected malformed context_id",
                    extra={"context_id": context_id},
                )
                raise MalformedContextIdError(context_id) from exc

        raise MalformedContextIdError(context_id)

    # Message handler methods
    #
    # The ``caller_did`` argument is threaded in by the A2A endpoint from the
    # authenticated request (``scope.state.user.client_id``). Phase 1 uses it
    # only to stamp ``owner_did`` on newly-created tasks and contexts inside
    # ``storage.submit_task``. Phase 2 will consult it in reads to enforce
    # ownership. ``None`` is allowed and means "no authenticated identity" —
    # expected in deployments that run with auth disabled.
    async def send_message(
        self,
        request: SendMessageRequest,
        caller_did: str | None = None,
    ) -> SendMessageResponse:
        """Send a message using the A2A protocol."""
        return await self._message_handlers.send_message(request, caller_did=caller_did)

    async def stream_message(
        self,
        request: StreamMessageRequest,
        caller_did: str | None = None,
    ):
        """Stream messages using Server-Sent Events."""
        return await self._message_handlers.stream_message(
            request, caller_did=caller_did
        )

    # Task handler methods
    async def get_task(
        self,
        request: GetTaskRequest,
        caller_did: str | None = None,
    ) -> GetTaskResponse:
        """Get a task and return it to the client."""
        return await self._task_handlers.get_task(request, caller_did=caller_did)

    async def list_tasks(
        self,
        request: ListTasksRequest,
        caller_did: str | None = None,
    ) -> ListTasksResponse:
        """List all tasks in storage."""
        return await self._task_handlers.list_tasks(request, caller_did=caller_did)

    async def cancel_task(
        self,
        request: CancelTaskRequest,
        caller_did: str | None = None,
    ) -> CancelTaskResponse:
        """Cancel a running task."""
        return await self._task_handlers.cancel_task(request, caller_did=caller_did)

    async def task_feedback(
        self,
        request: TaskFeedbackRequest,
        caller_did: str | None = None,
    ) -> TaskFeedbackResponse:
        """Submit feedback for a completed task."""
        return await self._task_handlers.task_feedback(request, caller_did=caller_did)

    # Context handler methods
    async def list_contexts(
        self,
        request: ListContextsRequest,
        caller_did: str | None = None,
    ) -> ListContextsResponse:
        """List all contexts in storage."""
        return await self._context_handlers.list_contexts(
            request, caller_did=caller_did
        )

    async def clear_context(
        self,
        request: ClearContextsRequest,
        caller_did: str | None = None,
    ) -> ClearContextsResponse:
        """Clear a context from storage."""
        return await self._context_handlers.clear_context(
            request, caller_did=caller_did
        )

    # Push notification handler methods
    async def set_task_push_notification(
        self,
        request: SetTaskPushNotificationRequest,
        caller_did: str | None = None,
    ) -> SetTaskPushNotificationResponse:
        """Set push notification settings for a task."""
        return await self._push_manager.set_task_push_notification(
            request, self.storage.load_task, caller_did=caller_did
        )

    async def get_task_push_notification(
        self,
        request: GetTaskPushNotificationRequest,
        caller_did: str | None = None,
    ) -> GetTaskPushNotificationResponse:
        """Get push notification settings for a task."""
        return await self._push_manager.get_task_push_notification(
            request, caller_did=caller_did
        )

    async def list_task_push_notifications(
        self,
        request: ListTaskPushNotificationConfigRequest,
        caller_did: str | None = None,
    ) -> ListTaskPushNotificationConfigResponse:
        """List push notification configurations for a task."""
        return await self._push_manager.list_task_push_notifications(
            request, caller_did=caller_did
        )

    async def delete_task_push_notification(
        self,
        request: DeleteTaskPushNotificationConfigRequest,
        caller_did: str | None = None,
    ) -> DeleteTaskPushNotificationConfigResponse:
        """Delete a push notification configuration for a task."""
        return await self._push_manager.delete_task_push_notification(
            request, caller_did=caller_did
        )
