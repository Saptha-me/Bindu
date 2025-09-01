# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# STORAGE OVERVIEW:
# 
# The Storage is the order tracking system in the Pebbling framework.
# It stores and retrieves tasks, contexts, and maintains the complete order history
# for the burger restaurant (agent execution system).
#
# BURGER STORE ANALOGY:
# 
# Think of a busy burger restaurant's order tracking system:
# 
# 1. CUSTOMER ORDERS (TaskManager):
#    - Customer places order: "I want a cheeseburger"
#    - TaskManager creates the order and sends it to Storage
# 
# 2. ORDER QUEUE (Scheduler):
#    - Scheduler acts like the kitchen order board
#    - Queues orders: [Order #1: Cheeseburger, Order #2: Fries, ...]
#    - Decides which orders go to which kitchen stations (workers)
#    - Handles special requests: pause order, cancel order, resume order
# 
# 3. KITCHEN WORKERS (Workers):
#    - Receive orders from the Scheduler
#    - Cook the food (execute the task)
#    - Report back when done
# 
# 4. ORDER TRACKING (Storage):
#    - Keeps track of order status: submitted, cooking, ready, delivered
#    - Stores order history and customer preferences
#    - Maintains receipts and order details for future reference
#    - Tracks customer conversation history and special requests
#
# STORAGE RESPONSIBILITIES:
# - Task persistence: Store complete task lifecycle and status updates
# - Context management: Maintain conversation history and customer preferences
# - Order history: Keep detailed records of all orders and their outcomes
# - Data retrieval: Quickly find past orders and customer information
# - Artifact storage: Store order receipts, special instructions, and results
#
# IMPLEMENTATION:
# - Abstract base class defines the storage interface
# - Concrete implementations (InMemoryStorage, FileStorage, DatabaseStorage, etc.)
# - Integrates with TaskManager for task submission and updates
# - Provides context storage for maintaining conversation state
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic

from typing_extensions import TypeVar

from pebbling.protocol.types import Artifact, Message, Task, TaskState, TaskStatus

ContextT = TypeVar('ContextT', default=Any)


class Storage(ABC, Generic[ContextT]):
    """A storage to retrieve and save tasks, as well as retrieve and save context.

    The storage serves two purposes:
    1. Task storage: Stores tasks in A2A protocol format with their status, artifacts, and message history
    2. Context storage: Stores conversation context in a format optimized for the specific agent implementation
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


class InMemoryStorage(Storage[ContextT]):
    """A storage to retrieve and save tasks in memory."""

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
