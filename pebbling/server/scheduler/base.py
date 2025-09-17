# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# SCHEDULER OVERVIEW:
#
# The Scheduler is the task queue manager in the Pebbling framework.
# It receives tasks from the TaskManager and coordinates their execution
# by workers, handling task lifecycle operations like run, cancel, pause, resume.
#
# BURGER STORE ANALOGY:
#
# Think of a busy burger restaurant:
#
# 1. CUSTOMER ORDERS (TaskManager):
#    - Customer places order: "I want a cheeseburger"
#    - TaskManager creates the order and sends it to Scheduler
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
#
# SCHEDULER RESPONSIBILITIES:
# - Queue management: Decide which tasks run when
# - Load balancing: Distribute tasks across available workers
# - Task lifecycle: Handle run, cancel, pause, resume operations
# - Worker coordination: Send tasks to appropriate workers
# - Failure handling: Retry failed tasks, handle worker crashes
#
# IMPLEMENTATION:
# - Abstract base class defines the scheduler interface
# - Concrete implementations (InMemoryScheduler, RedisScheduler, etc.)
# - Integrates with TaskManager for task submission
# - Communicates with Workers for task execution
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, TypeVar

from opentelemetry.trace import Span, get_tracer
from pydantic import Discriminator
from typing_extensions import Self, TypedDict

from pebbling.common.protocol.types import TaskIdParams, TaskSendParams

tracer = get_tracer(__name__)


@dataclass
class Scheduler(ABC):
    """The scheduler class is in charge of scheduling the tasks."""

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Send a task to be executed by the worker."""
        raise NotImplementedError("send_run_task is not implemented yet.")

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a task."""
        raise NotImplementedError("send_cancel_task is not implemented yet.")

    @abstractmethod
    async def pause_task(self, params: TaskIdParams) -> None:
        """Pause a task."""
        raise NotImplementedError("send_pause_task is not implemented yet.")

    @abstractmethod
    async def resume_task(self, params: TaskIdParams) -> None:
        """Resume a task."""
        raise NotImplementedError("send_resume_task is not implemented yet.")

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any): ...

    @abstractmethod
    def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the broker.

        On a multi-worker setup, the broker will need to round-robin the task operations
        between the workers.
        """


OperationT = TypeVar("OperationT")
ParamsT = TypeVar("ParamsT")


class _TaskOperation(TypedDict, Generic[OperationT, ParamsT]):
    """A task operation."""

    operation: OperationT
    params: ParamsT
    _current_span: Span


_RunTask = _TaskOperation[Literal["run"], TaskSendParams]
_CancelTask = _TaskOperation[Literal["cancel"], TaskIdParams]
_PauseTask = _TaskOperation[Literal["pause"], TaskIdParams]
_ResumeTask = _TaskOperation[Literal["resume"], TaskIdParams]

TaskOperation = Annotated["_RunTask | _CancelTask | _PauseTask | _ResumeTask", Discriminator("operation")]
