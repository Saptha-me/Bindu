from __future__ import annotations as _annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic

from typing_extensions import TypeVar

from .schema import Artifact, Message, Task, TaskState, TaskStatus

ContextT = TypeVar('ContextT', default=Any)

class Store(ABC, Generic[ContextT]):
    """A store to retrieve and save tasks, as well as retrieve and save context.

    The store serves two purposes:
    1. Task store: Stores tasks in A2A protocol format with their status, artifacts, and message history
    2. Context store: Stores conversation context in a format optimized for the specific agent implementation
    """

    @abstractmethod
    async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
        """Load a task from storage.

        If the task is not found, return None.
        """

    @abstractmethod
    async def submit_task(self, context_id: str, message: Message) -> Task:
        """Submit a task to storage."""

    @abstractmethod
    async def update_task(
        self,
        task_id: str,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task. Appends artifacts and messages, if specified."""

    @abstractmethod
    async def load_context(self, context_id: str) -> ContextT | None:
        """Retrieve the stored context given the `context_id`."""

    @abstractmethod
    async def update_context(self, context_id: str, context: ContextT) -> None:
        """Updates the context for a `context_id`.

        Implementing agent can decide what to store in context.
        """