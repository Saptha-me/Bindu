"""
|---------------------------------------------------------|
|                                                         |
|                 Give Feedback / Get Help                |
| https://github.com/Pebbling-ai/pebble/issues/new/choose |
|                                                         |
|---------------------------------------------------------|

🍔 **The Pebbling Task Manager: A Burger Restaurant Architecture**

This module defines the TaskManager - the **Restaurant Manager** of our AI agent ecosystem.
Think of it like running a high-end burger restaurant where customers place orders,
and we coordinate the entire kitchen operation to deliver perfect results.

## 🏢 **Restaurant Components**

- **TaskManager** (Restaurant Manager): Coordinates the entire operation, handles customer requests
- **Scheduler** (Order Queue System): Manages the flow of orders to the kitchen
- **Worker** (Chef): Actually cooks the burgers (executes AI agent tasks)
- **Runner** (Recipe Book): Defines how each dish is prepared and plated
- **Storage** (Restaurant Database): Keeps track of orders, ingredients, and completed dishes

## 🏗️ **Restaurant Architecture**

```
  +-----------------+
  |   Front Desk    |  🎯 Customer Interface
  |  (HTTP Server)  |     (Takes Orders)
  +-------+---------+
          |
          | 📝 Order Placed
          v
  +-------+---------+
  |                 |  👨‍💼 Restaurant Manager
  |   TaskManager   |     (Coordinates Everything)
  |   (Manager)     |<-----------------+
  +-------+---------+                  |
          |                            |
          | 📋 Send to Kitchen         | 💾 Track Everything
          v                            v
  +------------------+         +----------------+
  |                  |         |                |  📊 Restaurant Database
  |    Scheduler     |         |    Storage     |     (Orders & History)
  |  (Order Queue)   |         |  (Database)    |
  +------------------+         +----------------+
          |                            ^
          | 🍳 Kitchen Ready           |
          v                            | 📝 Update Status
  +------------------+                 |
  |                  |                 |  👨‍🍳 Head Chef
  |     Worker       |-----------------+     (Executes Tasks)
  |     (Chef)       |
  +------------------+
          |
          | 📖 Follow Recipe
          v
  +------------------+
  |     Runner       |  📚 Recipe Book
  |  (Recipe Book)   |     (Task Execution Logic)
  +------------------+
```

## 🔄 **Restaurant Workflow**

1. **📞 Order Received**: Customer places order at Front Desk (HTTP Server)
2. **👨‍💼 Manager Takes Control**: TaskManager receives the order and logs it
3. **💾 Order Logged**: Initial order details stored in Restaurant Database (Storage)
4. **📋 Kitchen Queue**: TaskManager sends order to Scheduler (Order Queue System)
5. **🍳 Chef Assignment**: Scheduler determines when Chef (Worker) is available
6. **📖 Recipe Lookup**: Worker consults Runner (Recipe Book) for execution steps
7. **👨‍🍳 Cooking Process**: Runner defines how the task is prepared and executed
8. **📝 Progress Updates**: Worker continuously updates order status in Database
9. **🍔 Order Complete**: Final result stored and marked as ready
10. **📞 Customer Notification**: Manager can provide status updates anytime
11. **✅ Order Delivered**: Customer receives their perfectly prepared result

## 🎯 **Key Benefits**

- **🔄 Scalable**: Multiple chefs can work simultaneously
- **📊 Trackable**: Every order is logged and monitored
- **🛡️ Reliable**: Failed orders can be retried or cancelled
- **⚡ Efficient**: Smart queue management prevents kitchen overload
- **📈 Observable**: Full visibility into restaurant operations

*"Just like a well-run restaurant, every task gets the attention it deserves!"* 🌟

Thank you users! We ❤️ you! - 🐧
"""

from __future__ import annotations

import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pebbling.common.protocol.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    ClearContextsRequest,
    ClearContextsResponse,
    ContextNotFoundError,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    GetTaskRequest,
    GetTaskResponse,
    ListContextsRequest,
    ListContextsResponse,
    ListTasksRequest,
    ListTasksResponse,
    ResubscribeTaskRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    StreamMessageRequest,
    StreamMessageResponse,
    Task,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
    TaskNotFoundError,
    TaskSendParams,
)

from ..utils.task_telemetry import trace_context_operation, trace_task_operation, track_active_task
from .scheduler import Scheduler
from .storage import Storage
from .workers import ManifestWorker


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks and coordinating the AI agent ecosystem."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Optional[Any] = None  # AgentManifest for creating workers

    _aexit_stack: Optional[AsyncExitStack] = field(default=None, init=False)
    _workers: list[ManifestWorker] = field(default_factory=list, init=False)

    async def __aenter__(self) -> "TaskManager":
        """Initialize the task manager and start all components."""
        self._aexit_stack = AsyncExitStack()
        await self._aexit_stack.__aenter__()
        await self._aexit_stack.enter_async_context(self.scheduler)

        # Create and start workers if manifest is provided
        if self.manifest:
            worker = ManifestWorker(scheduler=self.scheduler, storage=self.storage, manifest=self.manifest)
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

    def _create_error_response(self, response_class: type, request_id: str, error_class: type, message: str) -> Any:
        """Create a standardized error response."""
        return response_class(jsonrpc="2.0", id=request_id, error=error_class(code=-32001, message=message))

    def _parse_context_id(self, context_id: Any) -> uuid.UUID:
        """Parse and validate context_id, generating a new one if needed."""
        if context_id is None:
            return uuid.uuid4()
        if isinstance(context_id, str):
            return uuid.UUID(context_id)
        if isinstance(context_id, uuid.UUID):
            return context_id
        return uuid.uuid4()

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the Pebble protocol."""
        request_id = str(request["id"])
        message = request["params"]["message"]
        context_id = self._parse_context_id(message.get("context_id"))

        task: Task = await self.storage.submit_task(context_id, message)

        scheduler_params: TaskSendParams = {"task_id": task["task_id"], "context_id": context_id, "message": message}

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc="2.0", id=request_id, result=task)

    @trace_task_operation("get_task")
    async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Get a task and return it to the client."""
        task_id = request["params"]["task_id"]
        history_length = request["params"].get("history_length")

        task = await self.storage.load_task(task_id, history_length)
        if task is None:
            return self._create_error_response(GetTaskResponse, request["id"], TaskNotFoundError, "Task not found")

        return GetTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("cancel_task")
    @track_active_task
    async def cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        """Cancel a running task."""
        task_id = request["params"]["task_id"]

        await self.scheduler.cancel_task(request["params"])
        task = await self.storage.load_task(task_id)

        if task is None:
            return self._create_error_response(CancelTaskResponse, request["id"], TaskNotFoundError, "Task not found")

        return CancelTaskResponse(jsonrpc="2.0", id=request["id"], result=task)

    async def stream_message(self, request: StreamMessageRequest) -> StreamMessageResponse:
        """Stream messages using Server-Sent Events."""
        raise NotImplementedError("message/stream method is not implemented yet.")

    async def set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        """Set push notification settings for a task."""
        raise NotImplementedError("SetTaskPushNotification is not implemented yet.")

    async def get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        """Get push notification settings for a task."""
        raise NotImplementedError("GetTaskPushNotification is not implemented yet.")

    @trace_task_operation("list_tasks", include_params=False)
    async def list_tasks(self, request: ListTasksRequest) -> ListTasksResponse:
        """List all tasks in storage."""
        length = request["params"].get("length")
        tasks = await self.storage.list_tasks(length)

        if tasks is None:
            return self._create_error_response(ListTasksResponse, request["id"], TaskNotFoundError, "No tasks found")

        return ListTasksResponse(jsonrpc="2.0", id=request["id"], result=tasks)

    @trace_context_operation("list_contexts")
    async def list_contexts(self, request: ListContextsRequest) -> ListContextsResponse:
        """List all contexts in storage."""
        length = request["params"].get("length")
        contexts = await self.storage.list_contexts(length)

        if contexts is None:
            return self._create_error_response(
                ListContextsResponse, request["id"], ContextNotFoundError, "No contexts found"
            )

        return ListContextsResponse(jsonrpc="2.0", id=request["id"], result=contexts)

    @trace_context_operation("clear_context")
    async def clear_context(self, request: ClearContextsRequest) -> ClearContextsResponse:
        """Clear a context from storage."""
        context_id = request["params"].get("context_id")
        await self.storage.clear_context(context_id)

        return ClearContextsResponse(
            jsonrpc="2.0", id=request["id"], result={"message": "All tasks and contexts cleared successfully"}
        )

    @trace_task_operation("task_feedback")
    async def task_feedback(self, request: TaskFeedbackRequest) -> TaskFeedbackResponse:
        """Submit feedback for a completed task."""
        task_id = request["params"]["task_id"]

        # Verify task exists
        task = await self.storage.load_task(task_id)
        if task is None:
            return self._create_error_response(TaskFeedbackResponse, request["id"], TaskNotFoundError, "Task not found")

        # Prepare feedback data
        feedback_data = {
            "task_id": task_id,
            "feedback": request["params"]["feedback"],
            "rating": request["params"]["rating"],
            "metadata": request["params"]["metadata"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store feedback if storage supports it
        if hasattr(self.storage, "store_task_feedback"):
            await self.storage.store_task_feedback(task_id, feedback_data)

        return TaskFeedbackResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={"message": "Feedback submitted successfully", "task_id": str(task_id)},
        )

    async def resubscribe_task(self, request: ResubscribeTaskRequest) -> None:
        """Resubscribe to task updates."""
        raise NotImplementedError("Resubscribe is not implemented yet.")
