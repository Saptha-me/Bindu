from __future__ import annotations as _annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic

from typing_extensions import TypeVar

from .schema import Artifact, Message, Task, TaskState, TaskStatus

ContextT = TypeVar('ContextT', default=Any)


class InMemoryStore(Store[ContextT]):
    """A store to retrieve and save tasks in memory."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.contexts: dict[str, ContextT] = {}

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
        if history_length and 'history' in task:
            task['history'] = task['history'][-history_length:]
        return task

    async def submit_task(self, context_id: str, message: Message) -> Task:
        """Submit a task to storage."""
        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Add IDs to the message for A2A protocol
        message['task_id'] = task_id
        message['context_id'] = context_id

        task_status = TaskStatus(state='submitted', timestamp=datetime.now().isoformat())
        task = Task(id=task_id, context_id=context_id, kind='task', status=task_status, history=[message])
        self.tasks[task_id] = task

        return task

    async def update_task(
        self,
        task_id: str,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task."""
        task = self.tasks[task_id]
        task['status'] = TaskStatus(state=state, timestamp=datetime.now().isoformat())

        if new_artifacts:
            if 'artifacts' not in task:
                task['artifacts'] = []
            task['artifacts'].extend(new_artifacts)

        if new_messages:
            if 'history' not in task:
                task['history'] = []
            # Add IDs to messages for consistency
            for message in new_messages:
                message['task_id'] = task_id
                message['context_id'] = task['context_id']
                task['history'].append(message)

        return task

    async def update_context(self, context_id: str, context: ContextT) -> None:
        """Updates the context given the `context_id`."""
        self.contexts[context_id] = context

    async def load_context(self, context_id: str) -> ContextT | None:
        """Retrieve the stored context given the `context_id`."""
        return self.contexts.get(context_id)