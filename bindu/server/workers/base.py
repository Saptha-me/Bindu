"""Base worker classes for task execution."""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

import anyio
from opentelemetry.trace import get_tracer, use_span

from pebbling.common.protocol.types import Artifact, Message, TaskIdParams, TaskSendParams
from pebbling.server.scheduler.base import Scheduler
from pebbling.server.storage.base import Storage

tracer = get_tracer(__name__)


@dataclass
class Worker(ABC):
    """Base worker class for executing tasks.

    This worker bridges the gap between the pebble task execution system
    and the execution logic. It follows the Pebble pattern for
    proper lifecycle management.
    """

    scheduler: Scheduler
    storage: Storage

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Run the worker.

        It connects to the scheduler, and it makes itself available to receive commands.
        """
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        """Main worker loop to process tasks from scheduler."""
        async for task_operation in self.scheduler.receive_task_operations():
            await self._handle_task_operation(task_operation)

    async def _handle_task_operation(self, task_operation) -> None:
        """Handle a task operation from the scheduler."""
        operation_handlers = {
            "run": self.run_task,
            "cancel": self.cancel_task,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
        }

        try:
            with use_span(task_operation["_current_span"]):
                with tracer.start_as_current_span(
                    f"{task_operation['operation']} task", attributes={"logfire.tags": ["pebble"]}
                ):
                    handler = operation_handlers.get(task_operation["operation"])
                    if handler:
                        await handler(task_operation["params"])
        except Exception:
            # Update task status to failed on any exception
            task_id = task_operation["params"]["task_id"]
            await self.storage.update_task(task_id, state="failed")

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task."""
        ...

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task."""
        ...

    @abstractmethod
    def build_message_history(self, history: list[Message]) -> list[Any]:
        """Convert pebble protocol messages to format suitable for execution."""
        ...

    @abstractmethod
    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert execution result to pebble protocol artifacts."""
        ...

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Handle pause operation. Override in subclasses if pause is supported."""
        pass

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Handle resume operation. Override in subclasses if resume is supported."""
        pass
