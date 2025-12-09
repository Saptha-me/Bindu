"""In-memory scheduler implementation."""

from __future__ import annotations as _annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Any

import anyio
from opentelemetry.trace import get_current_span

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.server.scheduler.base import (
    Scheduler,
    TaskOperation,
    _CancelTask,
    _PauseTask,
    _ResumeTask,
    _RunTask,
)
from bindu.utils.logging import get_logger
from bindu.utils.retry import retry_scheduler_operation

logger = get_logger("bindu.server.scheduler.memory_scheduler")


class InMemoryScheduler(Scheduler):
    """A scheduler that schedules tasks in memory."""

    async def __aenter__(self):
        """Enter async context manager."""
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        self._write_stream, self._read_stream = anyio.create_memory_object_stream[
            TaskOperation
        ]()
        await self.aexit_stack.enter_async_context(self._read_stream)
        await self.aexit_stack.enter_async_context(self._write_stream)

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Exit async context manager."""
        await self.aexit_stack.__aexit__(exc_type, exc_value, traceback)

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def run_task(self, params: TaskSendParams) -> None:
        """Schedule a task for execution."""
        logger.debug(f"Running task: {params}")
        await self._write_stream.send(
            _RunTask(operation="run", params=params, _current_span=get_current_span())
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a scheduled task."""
        logger.debug(f"Canceling task: {params}")
        await self._write_stream.send(
            _CancelTask(
                operation="cancel", params=params, _current_span=get_current_span()
            )
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def pause_task(self, params: TaskIdParams) -> None:
        """Pause a running task."""
        logger.debug(f"Pausing task: {params}")
        await self._write_stream.send(
            _PauseTask(
                operation="pause", params=params, _current_span=get_current_span()
            )
        )

    @retry_scheduler_operation(max_attempts=3, min_wait=0.1, max_wait=1)
    async def resume_task(self, params: TaskIdParams) -> None:
        """Resume a paused task."""
        logger.debug(f"Resuming task: {params}")
        await self._write_stream.send(
            _ResumeTask(
                operation="resume", params=params, _current_span=get_current_span()
            )
        )

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the scheduler."""
        async for task_operation in self._read_stream:
            yield task_operation
