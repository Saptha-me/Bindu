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

import copy
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from typing_extensions import TypeVar

from bindu.common.protocol.types import Artifact, Message, Task, TaskState, TaskStatus
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import Storage

logger = get_logger("bindu.server.storage.memory_storage")

ContextT = TypeVar("ContextT", default=Any)


class InMemoryStorage(Storage[ContextT]):
    """In-memory storage implementation for tasks and contexts.

    Storage Structure:
    - tasks: Dict[UUID, Task] - All tasks indexed by task_id
    - contexts: Dict[UUID, list[UUID]] - Task IDs grouped by context_id
    - task_feedback: Dict[UUID, List[dict]] - Optional feedback storage
    """

    def __init__(self):
        """Initialize in-memory storage.

        Note: This is an __init__ method.
        """
        self.tasks: dict[UUID, Task] = {}
        self.contexts: dict[UUID, list[UUID]] = {}
        self.task_feedback: dict[UUID, list[dict[str, Any]]] = {}

    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from memory.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        task = self.tasks.get(task_id)
        if task is None:
            return None

        # Always return a deep copy to prevent mutations affecting stored task
        task_copy = cast(Task, copy.deepcopy(task))

        # Limit history if requested
        if history_length is not None and history_length > 0 and "history" in task:
            task_copy["history"] = task["history"][-history_length:]

        return task_copy

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create a new task or continue an existing non-terminal task.

        Task-First Pattern (Bindu):
        - If task exists and is in non-terminal state: Append message and reset to 'submitted'
        - If task exists and is in terminal state: Raise error (immutable)
        - If task doesn't exist: Create new task

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request

        Returns:
            Task in 'submitted' state (new or continued)

        Raises:
            TypeError: If IDs are invalid types
            ValueError: If attempting to continue a terminal task
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        # Parse task ID from message (handle both snake_case and camelCase)
        task_id_raw = message.get("task_id")
        task_id: UUID

        if isinstance(task_id_raw, str):
            task_id = UUID(task_id_raw)
        elif isinstance(task_id_raw, UUID):
            task_id = task_id_raw
        else:
            raise TypeError(
                f"task_id must be UUID or str, got {type(task_id_raw).__name__}"
            )

        # Ensure all UUID fields are proper UUID objects (normalize to snake_case)
        message["task_id"] = task_id
        message["context_id"] = context_id

        message_id_raw = message.get("message_id")
        if isinstance(message_id_raw, str):
            message["message_id"] = UUID(message_id_raw)
        elif message_id_raw is not None and not isinstance(message_id_raw, UUID):
            raise TypeError(
                f"message_id must be UUID or str, got {type(message_id_raw).__name__}"
            )

        # Validate and normalize reference_task_ids if present (handle both formats)
        ref_ids_key = "reference_task_ids"
        if ref_ids_key in message:
            ref_ids = message[ref_ids_key]
            if ref_ids is not None:
                normalized_refs = []
                for ref_id in ref_ids:
                    if isinstance(ref_id, str):
                        normalized_refs.append(UUID(ref_id))
                    elif isinstance(ref_id, UUID):
                        normalized_refs.append(ref_id)
                    else:
                        raise TypeError(
                            f"reference_task_id must be UUID or str, got {type(ref_id).__name__}"
                        )
                message["reference_task_ids"] = normalized_refs

        # Check if task already exists
        existing_task = self.tasks.get(task_id)

        if existing_task:
            # Task exists - check if it's mutable
            current_state = existing_task["status"]["state"]

            # Check if task is in terminal state (immutable)
            if current_state in app_settings.agent.terminal_states:
                raise ValueError(
                    f"Cannot continue task {task_id}: Task is in terminal state '{current_state}' and is immutable. "
                    f"Create a new task with referenceTaskIds to continue the conversation."
                )

            # Non-terminal states (mutable) - append message and continue
            logger.info(
                f"Continuing existing task {task_id} from state '{current_state}'"
            )

            if "history" not in existing_task:
                existing_task["history"] = []
            existing_task["history"].append(message)

            # Reset to submitted state for re-execution
            existing_task["status"] = TaskStatus(
                state="submitted", timestamp=datetime.now(timezone.utc).isoformat()
            )

            return existing_task

        # Task doesn't exist - create new task
        task_status = TaskStatus(
            state="submitted", timestamp=datetime.now(timezone.utc).isoformat()
        )
        task = Task(
            id=task_id,
            context_id=context_id,
            kind="task",
            status=task_status,
            history=[message],
        )
        self.tasks[task_id] = task

        # Add task to context
        if context_id not in self.contexts:
            self.contexts[context_id] = []
        self.contexts[context_id].append(task_id)

        return task

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Update task state and append new content.

        Hybrid Pattern Support:
        - Message only: update_task(task_id, "input-required", new_messages=[...], metadata={...})
        - Completion: update_task(task_id, "completed", new_artifacts=[...], new_messages=[...])

        Args:
            task_id: Task to update
            state: New task state (working, completed, failed, etc.)
            new_artifacts: Optional artifacts to append (for completion)
            new_messages: Optional messages to append to history
            metadata: Optional metadata to update/merge with task metadata

        Returns:
            Updated task object

        Raises:
            TypeError: If task_id is not UUID
            KeyError: If task not found
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        task["status"] = TaskStatus(
            state=state, timestamp=datetime.now(timezone.utc).isoformat()
        )

        if metadata:
            if "metadata" not in task:
                task["metadata"] = {}
            task["metadata"].update(metadata)

        if new_artifacts:
            if "artifacts" not in task:
                task["artifacts"] = []
            task["artifacts"].extend(new_artifacts)

        if new_messages:
            if "history" not in task:
                task["history"] = []
            # Add IDs to messages for consistency
            for message in new_messages:
                if not isinstance(message, dict):
                    raise TypeError(
                        f"Message must be dict, got {type(message).__name__}"
                    )
                message["task_id"] = task_id
                message["context_id"] = task["context_id"]
                task["history"].append(message)

        return task

    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context metadata.

        Note: This stores additional context metadata. Task associations are
        managed automatically via submit_task().

        Args:
            context_id: Context identifier
            context: Context data (format determined by agent implementation)

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        # Note: This method is kept for backward compatibility but contexts
        # are now primarily managed as task lists

    async def load_context(self, context_id: UUID) -> list[UUID] | None:
        """Load context task list from storage.

        Args:
            context_id: Unique identifier of the context

        Returns:
            List of task UUIDs if context exists, None otherwise

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        return self.contexts.get(context_id)

    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history.

        Note: This method is deprecated as contexts now store task lists.
        Messages are stored in task history instead.

        Args:
            context_id: Context to update
            messages: Messages to append to history

        Raises:
            TypeError: If context_id is not UUID or messages is not a list
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        if not isinstance(messages, list):
            raise TypeError(f"messages must be list, got {type(messages).__name__}")

        # Ensure context exists
        if context_id not in self.contexts:
            self.contexts[context_id] = []

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

    async def list_tasks_by_context(
        self, context_id: UUID, length: int | None = None
    ) -> list[Task]:
        """List tasks belonging to a specific context.

        Used for building conversation history and supporting task refinements.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return (most recent)

        Returns:
            List of tasks in the context

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        # Get task IDs from context
        task_ids = self.contexts.get(context_id, [])
        tasks: list[Task] = [
            self.tasks[task_id] for task_id in task_ids if task_id in self.tasks
        ]

        if length is not None and length > 0 and length < len(tasks):
            return tasks[-length:]
        return tasks

    async def list_contexts(self, length: int | None = None) -> list[dict[str, Any]]:
        """List all contexts in storage.

        Args:
            length: Optional limit on number of contexts to return (most recent)

        Returns:
            List of context objects with task counts
        """
        contexts = [
            {"context_id": ctx_id, "task_count": len(task_ids), "task_ids": task_ids}
            for ctx_id, task_ids in self.contexts.items()
        ]

        if length is not None and length > 0 and length < len(contexts):
            return contexts[-length:]
        return contexts

    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context.

        Args:
            context_id: The context ID to clear

        Raises:
            TypeError: If context_id is not UUID
            ValueError: If context does not exist

        Warning: This is a destructive operation.
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        # Check if context exists
        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")

        # Get task IDs from the context
        task_ids = self.contexts.get(context_id, [])

        # Remove all tasks associated with this context
        for task_id in task_ids:
            if task_id in self.tasks:
                del self.tasks[task_id]
            # Also clear feedback for these tasks
            if task_id in self.task_feedback:
                del self.task_feedback[task_id]

        # Remove the context itself
        del self.contexts[context_id]

        logger.info(f"Cleared context {context_id}: removed {len(task_ids)} tasks")

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """
        self.tasks.clear()
        self.contexts.clear()
        self.task_feedback.clear()

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content (rating, comments, etc.)

        Raises:
            TypeError: If task_id is not UUID or feedback_data is not dict
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if not isinstance(feedback_data, dict):
            raise TypeError(
                f"feedback_data must be dict, got {type(feedback_data).__name__}"
            )

        if task_id not in self.task_feedback:
            self.task_feedback[task_id] = []
        self.task_feedback[task_id].append(feedback_data)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists

        Raises:
            TypeError: If task_id is not UUID
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        return self.task_feedback.get(task_id)
