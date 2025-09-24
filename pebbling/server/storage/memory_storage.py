# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# IN-MEMORY STORAGE IMPLEMENTATION:
#
# This is the in-memory implementation of the Storage interface for the Pebbling framework.
# It provides fast, temporary storage for tasks and contexts during agent execution.
#
# BURGER STORE ANALOGY:
#
# Think of this as the restaurant's whiteboard order tracking system:
#
# 1. WHITEBOARD ORDERS (InMemoryStorage):
#    - Orders written on whiteboard for current shift
#    - Fast to read and update during busy periods
#    - Gets erased at end of day (when server restarts)
#    - Perfect for high-speed order processing
#
# 2. ORDER TRACKING:
#    - self.tasks: Dictionary of all current orders on the whiteboard
#    - self.contexts: Customer preferences and conversation history
#    - Quick lookup by order ID or customer ID
#    - Immediate updates when order status changes
#
# 3. PERFORMANCE CHARACTERISTICS:
#    - Lightning fast: O(1) lookups and updates
#    - Memory efficient: Only stores current active orders
#    - No persistence: Data lost when restaurant closes (server restarts)
#    - Perfect for development and testing environments
#
# WHEN TO USE IN-MEMORY STORAGE:
# - Development and testing environments
# - High-performance scenarios with temporary data
# - Prototyping and experimentation
# - Single-server deployments without persistence needs
# - Agent interactions that don't require durability
#
# LIMITATIONS:
# - Data lost on server restart
# - Not suitable for production with persistence requirements
# - Memory usage grows with number of tasks
# - No data sharing between multiple server instances
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from typing_extensions import TypeVar

from pebbling.common.protocol.types import Artifact, Context, Message, Task, TaskState, TaskStatus

from .base import Storage

ContextT = TypeVar("ContextT", default=Any)


class InMemoryStorage(Storage[ContextT]):
    """A store to retrieve and save tasks in memory."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.contexts: dict[str, ContextT] = {}
        self.task_feedback: dict[str, list[dict[str, Any]]] = {}

    async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
        """Load a task from memory.

        Args:
            task_id: The id of the task to load.
            history_length: The number of messages to return in the history.

        Returns:
            The task.
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        if history_length and "history" in task:
            task["history"] = task["history"][-history_length:]
        return task

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Submit a task to storage."""
        # Use existing task ID from message or generate new one
        task_id = message.get("task_id")
        if isinstance(task_id, str):
            task_id = UUID(task_id)

        # Ensure all UUID fields are proper UUID objects
        message["task_id"] = task_id
        message["context_id"] = context_id

        if "message_id" in message and isinstance(message["message_id"], str):
            message["message_id"] = UUID(message["message_id"])

        task_status = TaskStatus(state="submitted", timestamp=datetime.now(timezone.utc).isoformat())
        task = Task(task_id=task_id, context_id=context_id, kind="task", status=task_status, history=[message])
        self.tasks[task_id] = task

        return task

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task."""
        task = self.tasks[task_id]
        task["status"] = TaskStatus(state=state, timestamp=datetime.now(timezone.utc).isoformat())

        if new_artifacts:
            if "artifacts" not in task:
                task["artifacts"] = []
            task["artifacts"].extend(new_artifacts)

        if new_messages:
            if "history" not in task:
                task["history"] = []
            # Add IDs to messages for consistency
            for message in new_messages:
                message["task_id"] = task_id
                message["context_id"] = task["context_id"]
                task["history"].append(message)

        return task

    async def update_context(self, context_id: UUID, context: Context) -> None:
        """Updates the context given the `context_id`."""
        # Now we expect properly structured Context objects from the source
        self.contexts[context_id] = context

    async def load_context(self, context_id: UUID) -> Context | None:
        """Retrieve the stored context given the `context_id`."""
        return self.contexts.get(context_id)

    async def append_to_contexts(self, context_id: UUID, messages: list[Message]) -> None:
        """Efficiently append new messages to context history without rebuilding entire context."""
        if not messages:
            return

        existing_context = self.contexts.get(context_id)

        if existing_context is None:
            # Create new context with message history
            self.contexts[context_id] = {
                "context_id": context_id,
                "kind": "context",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "message_history": messages.copy(),
            }
        else:
            # Append to existing message history
            if "message_history" not in existing_context:
                existing_context["message_history"] = []
            existing_context["message_history"].extend(messages)
            existing_context["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks in storage."""
        tasks = list(self.tasks.values())
        if length:
            tasks = tasks[-length:]
        return tasks

    async def list_tasks_by_context(self, context_id: UUID, length: int | None = None) -> list[Task]:
        """List all tasks in storage."""
        tasks = [task for task in self.tasks.values() if task["context_id"] == context_id]
        if length:
            tasks = tasks[-length:]
        return tasks

    async def list_contexts(self, length: int | None = None) -> list[Context]:
        """List all contexts in storage."""
        contexts_list = list(self.contexts.values())
        if length:
            contexts_list = contexts_list[-length:]
        return contexts_list

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage."""
        self.tasks.clear()
        self.contexts.clear()
        self.task_feedback.clear()

    async def store_task_feedback(self, task_id: UUID, feedback_data: dict[str, Any]) -> None:
        """Store feedback for a task."""
        if task_id not in self.task_feedback:
            self.task_feedback[task_id] = []
        self.task_feedback[task_id].append(feedback_data)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task."""
        return self.task_feedback.get(task_id)
