"""In-memory storage implementation for A2A protocol task and context management.

This implementation provides a simple, non-persistent storage backend suitable for:
- Development and testing
- Prototyping agents
- Single-session applications

Hybrid Agent Pattern Support:
- Stores tasks with flexible state transitions (working → input-required → completed)
- Maintains conversation context across multiple tasks
- Supports incremental message history updates
- Enables task refinements through context-based task lookup

Note: All data is lost when the application stops. Use persistent storage for production.
"""

from __future__ import annotations as _annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from typing_extensions import TypeVar

from bindu.common.protocol.types import Artifact, Context, Message, Task, TaskState, TaskStatus
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.storage.memory_storage")

from .base import Storage

ContextT = TypeVar("ContextT", default=Any)


class InMemoryStorage(Storage[ContextT]):
    """In-memory storage implementation for tasks and contexts.
    
    Storage Structure:
    - tasks: Dict[UUID, Task] - All tasks indexed by task_id
    - contexts: Dict[UUID, Context] - All contexts indexed by context_id
    - task_feedback: Dict[UUID, List[dict]] - Optional feedback storage
    """

    def __init__(self):
        self.tasks: dict[UUID, Task] = {}
        self.contexts: dict[UUID, ContextT] = {}
        self.task_feedback: dict[UUID, list[dict[str, Any]]] = {}
        # Performance optimization: Index tasks by context_id for O(1) lookup
        self._context_task_index: dict[UUID, list[UUID]] = {}

    async def load_task(self, task_id: UUID, history_length: int | None = None) -> Task | None:
        """Load a task from memory.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise
        """
        task = self.tasks.get(task_id)
        if task is None:
            return None

        # Return copy with limited history to avoid mutating stored task
        if history_length and "history" in task:
            task_copy = task.copy()
            task_copy["history"] = task["history"][-history_length:]
            return task_copy
        
        return task

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create and store a new task.

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request

        Returns:
            Newly created task in 'submitted' state
        """
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

        # Update context index for O(1) lookup
        if context_id not in self._context_task_index:
            self._context_task_index[context_id] = []
        self._context_task_index[context_id].append(task_id)

        return task

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update task state and append new content.

        Hybrid Pattern Support:
        - Message only: update_task(task_id, "input-required", new_messages=[...])
        - Completion: update_task(task_id, "completed", new_artifacts=[...], new_messages=[...])

        Args:
            task_id: Task to update
            state: New task state (working, completed, failed, etc.)
            new_artifacts: Optional artifacts to append (for completion)
            new_messages: Optional messages to append to history

        Returns:
            Updated task object
        """
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
        """Store or update context.

        Args:
            context_id: Context identifier
            context: Context data (format determined by agent implementation)
        """
        # Now we expect properly structured Context objects from the source
        self.contexts[context_id] = context

    async def load_context(self, context_id: UUID) -> Context | None:
        """Load context from storage.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Context object if found, None otherwise
        """
        return self.contexts.get(context_id)

    async def append_to_contexts(self, context_id: UUID, messages: list[Message]) -> None:
        """Append messages to context history.

        Efficient operation that updates context without full rebuild.
        Creates new context if it doesn't exist.

        Args:
            context_id: Context to update
            messages: Messages to append to history
        """
        if not messages:
            return

        existing_context = self.contexts.get(context_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        if existing_context is None:
            # Create new context with message history
            self.contexts[context_id] = {
                "context_id": context_id,
                "kind": "context",
                "created_at": timestamp,
                "updated_at": timestamp,
                "status": "active",
                "message_history": messages,  # No need to copy, we own this list
            }
        else:
            # Append to existing message history
            if "message_history" not in existing_context:
                existing_context["message_history"] = []
            existing_context["message_history"].extend(messages)
            existing_context["updated_at"] = timestamp

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks in storage.

        Args:
            length: Optional limit on number of tasks to return (most recent)

        Returns:
            List of tasks
        """
        if length is None:
            return list(self.tasks.values())
        
        # Optimize: Only convert to list what we need
        all_tasks = list(self.tasks.values())
        return all_tasks[-length:] if length < len(all_tasks) else all_tasks

    async def list_tasks_by_context(self, context_id: UUID, length: int | None = None) -> list[Task]:
        """List tasks belonging to a specific context.

        Used for building conversation history and supporting task refinements.
        Optimized with O(1) index lookup instead of O(n) scan.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return (most recent)

        Returns:
            List of tasks in the context
        """
        # Use index for O(1) lookup instead of O(n) scan
        task_ids = self._context_task_index.get(context_id, [])
        tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
        
        if length and length < len(tasks):
            return tasks[-length:]
        return tasks

    async def list_contexts(self, length: int | None = None) -> list[Context]:
        """List all contexts in storage.

        Args:
            length: Optional limit on number of contexts to return (most recent)

        Returns:
            List of context objects
        """
        if length is None:
            return list(self.contexts.values())
        
        all_contexts = list(self.contexts.values())
        return all_contexts[-length:] if length < len(all_contexts) else all_contexts

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """
        self.tasks.clear()
        self.contexts.clear()
        self.task_feedback.clear()
        self._context_task_index.clear()

    async def store_task_feedback(self, task_id: UUID, feedback_data: dict[str, Any]) -> None:
        """Store user feedback for a task.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content (rating, comments, etc.)
        """
        if task_id not in self.task_feedback:
            self.task_feedback[task_id] = []
        self.task_feedback[task_id].append(feedback_data)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists
        """
        return self.task_feedback.get(task_id)
