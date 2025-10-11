"""Base scheduler module."""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, TypeVar

from opentelemetry.trace import Span, get_tracer
from pydantic import Discriminator
from typing_extensions import Self, TypedDict

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.utils.logging import get_logger

tracer = get_tracer(__name__)
logger = get_logger("bindu.server.scheduler.base")


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
    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager."""
        ...

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

TaskOperation = Annotated[
    "_RunTask | _CancelTask | _PauseTask | _ResumeTask", Discriminator("operation")
]
