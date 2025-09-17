# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# IN-MEMORY SCHEDULER IMPLEMENTATION:
#
# This is a concrete implementation of the Scheduler that keeps all task
# operations in memory using async streams. Perfect for development,
# testing, and single-process deployments.
#
# BURGER STORE ANALOGY - MEMORY IMPLEMENTATION:
#
# Think of a small burger joint with a simple order board:
#
# 1. ORDER BOARD (Memory Streams):
#    - Simple whiteboard where orders are written down
#    - Orders flow from "incoming" side to "kitchen" side
#    - No external database - everything stays on the board
#
# 2. ORDER FLOW:
#    - Customer order comes in → Written on board (write_stream)
#    - Kitchen staff reads from board → Takes order (read_stream)
#    - Special requests: pause, cancel, resume orders
#
# 3. ADVANTAGES:
#    - Fast: No network calls or disk writes
#    - Simple: Easy to understand and debug
#    - Reliable: No external dependencies
#
# 4. LIMITATIONS:
#    - Single process only (one restaurant location)
#    - Lost on restart (board gets erased)
#    - No persistence (orders don't survive power outage)
#
# WHEN TO USE:
# - Development and testing environments
# - Single-agent deployments
# - Proof of concepts and demos
# - When you need fast, simple task scheduling
#
# FOR PRODUCTION:
# - Consider RedisScheduler for multi-process deployments
# - Consider DatabaseScheduler for persistence requirements
# - Consider CloudScheduler for distributed systems
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Any

import anyio
from opentelemetry.trace import get_current_span

from pebbling.common.protocol.types import TaskIdParams, TaskSendParams
from pebbling.server.scheduler.base import (
    Scheduler,
    TaskOperation,
    _CancelTask,
    _PauseTask,
    _ResumeTask,
    _RunTask,
)


class InMemoryScheduler(Scheduler):
    """A scheduler that schedules tasks in memory."""

    async def __aenter__(self):
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        self._write_stream, self._read_stream = anyio.create_memory_object_stream[TaskOperation]()
        await self.aexit_stack.enter_async_context(self._read_stream)
        await self.aexit_stack.enter_async_context(self._write_stream)

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        await self.aexit_stack.__aexit__(exc_type, exc_value, traceback)

    async def run_task(self, params: TaskSendParams) -> None:
        await self._write_stream.send(_RunTask(operation="run", params=params, _current_span=get_current_span()))

    async def cancel_task(self, params: TaskIdParams) -> None:
        await self._write_stream.send(_CancelTask(operation="cancel", params=params, _current_span=get_current_span()))

    async def pause_task(self, params: TaskIdParams) -> None:
        await self._write_stream.send(_PauseTask(operation="pause", params=params, _current_span=get_current_span()))

    async def resume_task(self, params: TaskIdParams) -> None:
        await self._write_stream.send(_ResumeTask(operation="resume", params=params, _current_span=get_current_span()))

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the scheduler."""
        async for task_operation in self._read_stream:
            yield task_operation
