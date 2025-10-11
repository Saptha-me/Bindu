"""Base storage interface for task and context management."""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from typing import Any, Generic
from uuid import UUID

from typing_extensions import TypeVar

from bindu.common.protocol.types import Artifact, Message, Task, TaskState

ContextT = TypeVar("ContextT", default=Any)


class Storage(ABC, Generic[ContextT]):
    """Abstract storage interface for A2A protocol task and context management.

    Responsibilities:
    - Task Lifecycle: Store, retrieve, and update tasks following A2A protocol
    - Context Management: Maintain conversation context across multiple tasks
    - History Tracking: Preserve message history and task artifacts

    Hybrid Agent Pattern Support:
    - Messages during execution: update_task(state="input-required", new_messages=[...])
    - Artifacts at completion: update_task(state="completed", new_artifacts=[...], new_messages=[...])
    - Context continuity: append_to_contexts() for incremental message history
    - Task refinements: list_tasks_by_context() to build conversation from related tasks

    Type Parameters:
        ContextT: Custom context type for agent-specific implementations
    """

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from storage.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise
        """

    @abstractmethod
    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create and store a new task.

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request

        Returns:
            Newly created task in 'submitted' state
        """

    @abstractmethod
    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Update task state and append new content.

        Args:
            task_id: Task to update
            state: New task state (working, completed, failed, etc.)
            new_artifacts: Optional artifacts to append
            new_messages: Optional messages to append to history
            metadata: Optional metadata to update/merge with task metadata

        Returns:
            Updated task object
        """

    @abstractmethod
    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks in storage.

        Args:
            length: Optional limit on number of tasks to return (most recent)

        Returns:
            List of tasks
        """

    @abstractmethod
    async def list_tasks_by_context(
        self, context_id: UUID, length: int | None = None
    ) -> list[Task]:
        """List tasks belonging to a specific context.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return (most recent)

        Returns:
            List of tasks in the context
        """

    # -------------------------------------------------------------------------
    # Context Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def load_context(self, context_id: UUID) -> ContextT | None:
        """Load context from storage.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Context object if found, None otherwise
        """

    @abstractmethod
    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history.

        Efficient operation that updates context without full rebuild.

        Args:
            context_id: Context to update
            messages: Messages to append to history
        """

    @abstractmethod
    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context.

        Args:
            context_id: Context identifier
            context: Context data (format determined by agent implementation)
        """

    @abstractmethod
    async def list_contexts(self, length: int | None = None) -> list[dict]:
        """List all contexts in storage.

        Args:
            length: Optional limit on number of contexts to return (most recent)

        Returns:
            List of context objects
        """

    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context.

        Args:
            context_id: The context ID to clear

        Warning: This is a destructive operation.
        """

    @abstractmethod
    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """

    # -------------------------------------------------------------------------
    # Feedback Operations (Optional)
    # -------------------------------------------------------------------------

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task.

        Optional operation - implementations may choose to store feedback
        as task metadata or in dedicated storage.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content (rating, comments, etc.)
        """
        # Optional - override in subclass if feedback storage is needed
        pass

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists
        """
        # Optional - override in subclass if feedback retrieval is needed
        return None
