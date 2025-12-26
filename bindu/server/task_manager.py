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

import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any


from ..utils.logging import get_logger
from .handlers import ContextHandlers, MessageHandlers, TaskHandlers
from .notifications import PushNotificationManager
from .scheduler import Scheduler
from .storage import Storage
from .workers import ManifestWorker

logger = get_logger("pebbling.server.task_manager")


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks and coordinating the AI agent ecosystem."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None  # AgentManifest for creating workers

    _aexit_stack: AsyncExitStack | None = field(default=None, init=False)
    _workers: list[ManifestWorker] = field(default_factory=list, init=False)
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

        # Initialize handlers after workers are created
        self._message_handlers = MessageHandlers(
            scheduler=self.scheduler,
            storage=self.storage,
            manifest=self.manifest,
            workers=self._workers,
            context_id_parser=self._parse_context_id,
            push_manager=self._push_manager,
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

    def _jsonrpc_error(
        self, response_class: type, request_id: Any, message: str, code: int = -32001
    ):
        return response_class(
            jsonrpc="2.0", id=request_id, error={"code": code, "message": message}
        )

    def __getattr__(self, name: str):
        """Automatically delegate method calls to appropriate handlers.

        This DRY approach routes method calls to the correct handler based on method name.
        """
        # Message handler methods
        if name in ("send_message", "stream_message"):
            return getattr(self._message_handlers, name)

        # Task handler methods
        if name in ("get_task", "list_tasks", "cancel_task", "task_feedback"):
            return getattr(self._task_handlers, name)

        # Context handler methods
        if name in ("list_contexts", "clear_context"):
            return getattr(self._context_handlers, name)

        # Special case for set_task_push_notification which needs storage
        if name == "set_task_push_notification":

            async def _set_with_storage(request):
                return await self._push_manager.set_task_push_notification(
                    request, self.storage.load_task
                )

            return _set_with_storage

        # Other push notification handler methods
        if name in (
            "get_task_push_notification",
            "list_task_push_notifications",
            "delete_task_push_notification",
        ):
            return getattr(self._push_manager, name)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )
