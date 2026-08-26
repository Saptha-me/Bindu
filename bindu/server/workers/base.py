"""Base worker implementation for A2A protocol task execution.

Workers are the execution engines that process tasks from the scheduler.
They bridge the gap between the A2A protocol and actual agent implementation,
handling task lifecycle, error recovery, and observability.

Architecture:
- Workers receive task operations from the Scheduler
- Execute tasks using agent-specific logic (ManifestWorker, etc.)
- Update task state in Storage
- Handle errors and state transitions
- Provide observability through OpenTelemetry tracing

Hybrid Agent Pattern:
Workers implement the hybrid pattern by:
- Processing tasks through multiple state transitions
- Supporting input-required and auth-required states
- Generating artifacts only on task completion
"""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass
from typing import Any, AsyncIterator

import anyio
from opentelemetry.trace import get_tracer, use_span

from bindu.server.scheduler import TaskOperation

from bindu.common.protocol.types import Artifact, Message, TaskIdParams, TaskSendParams
from bindu.server.scheduler.base import Scheduler
from bindu.server.storage.base import Storage
from bindu.utils.logging import get_logger

tracer = get_tracer(__name__)
logger = get_logger(__name__)


@dataclass
class Worker(ABC):
    """Abstract base worker for A2A protocol task execution.

    Responsibilities:
    - Task Execution: Process tasks received from scheduler
    - State Management: Update task states through lifecycle
    - Error Handling: Gracefully handle failures and update task status
    - Observability: Trace task operations with OpenTelemetry

    Lifecycle:
    1. Worker starts and connects to scheduler
    2. Receives task operations (run, cancel, pause, resume)
    3. Executes operations with proper error handling
    4. Updates task state in storage
    5. Provides tracing for monitoring

    Subclasses must implement:
    - run_task(): Execute task logic
    - cancel_task(): Handle task cancellation
    - build_message_history(): Convert protocol messages to execution format
    - build_artifacts(): Convert results to protocol artifacts
    """

    scheduler: Scheduler
    """Scheduler that provides task operations to execute."""

    storage: Storage[Any]
    """Storage backend for task and context persistence."""

    # -------------------------------------------------------------------------
    # Worker Lifecycle
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Start the worker and begin processing tasks.

        Context manager that:
        1. Starts the worker loop in a task group
        2. Yields control to caller
        3. Cancels worker on exit

        Usage:
            async with worker.run():
                # Worker is running
                ...
            # Worker stopped
        """
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        """Process task operations continuously.

        Receives task operations from scheduler and dispatches them to handlers.
        Runs until cancelled by the task group.
        """
        async for task_operation in self.scheduler.receive_task_operations():
            await self._handle_task_operation(task_operation)

    async def _handle_task_operation(self, task_operation: TaskOperation) -> None:
        """Dispatch task operation to appropriate handler.

        Args:
            task_operation: Operation dict with 'operation', 'params', and '_current_span'

        Supported Operations:
        - run: Execute a task
        - cancel: Cancel a running task
        - pause: Pause task execution (future)
        - resume: Resume paused task (future)

        Error Handling:
        - Any exception during execution marks task as 'failed'
        - Preserves OpenTelemetry trace context
        """
        operation_handlers: dict[str, Any] = {
            "run": self.run_task,
            "cancel": self.cancel_task,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
        }

        try:
            # Preserve trace context from scheduler (if available)
            span = task_operation.get("_current_span")
            ctx_manager = use_span(span) if span else nullcontext()
            with ctx_manager:
                with tracer.start_as_current_span(
                    f"{task_operation['operation']} task",
                    attributes={"logfire.tags": ["bindu"]},
                ):
                    handler = operation_handlers.get(task_operation["operation"])
                    if handler:
                        await handler(task_operation["params"])
                    else:
                        logger.warning(
                            f"Unknown operation: {task_operation['operation']}"
                        )
        except Exception as e:  # noqa: BLE001 - intentionally broad: any unhandled worker failure must mark the task as failed
            # Update task status to failed on any exception
            task_id = self._normalize_uuid(task_operation["params"]["task_id"])
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self.storage.update_task(task_id, state="failed")

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_uuid(value: Any) -> Any:
        """Normalize UUID value from string or UUID object.

        Args:
            value: UUID value (string, UUID object, or other)

        Returns:
            UUID object if input is string or UUID, otherwise returns input as-is
        """
        from uuid import UUID

        if isinstance(value, str):
            return UUID(value)
        return value

    # -------------------------------------------------------------------------
    # Abstract Methods (Must Implement)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task with given parameters.

        Args:
            params: Task execution parameters including task_id, context_id, message

        Implementation should:
        1. Load task from storage
        2. Build message history from context
        3. Execute agent logic
        4. Handle state transitions (working → input-required → completed)
        5. Generate artifacts on completion
        6. Update storage with results
        """
        ...

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters

        Implementation should:
        1. Stop task execution if running
        2. Update task state to 'canceled'
        3. Clean up any resources
        """
        ...

    @abstractmethod
    def build_message_history(self, history: list[Message]) -> list[Any]:
        """Convert A2A protocol messages to agent-specific format.

        Args:
            history: List of protocol Message objects

        Returns:
            List in format suitable for agent execution (e.g., chat format for LLMs)

        Example:
            Protocol: [{"role": "user", "parts": [{"text": "Hello"}]}]
            Agent: [{"role": "user", "content": "Hello"}]
        """
        ...

    @abstractmethod
    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert agent execution result to A2A protocol artifacts.

        Args:
            result: Agent execution result (any format)

        Returns:
            List of Artifact objects with proper structure

        Hybrid Pattern:
        - Only called when task completes successfully
        - Artifacts represent final deliverable
        - Must include artifact_id, parts, and optional metadata
        """
        ...

    # -------------------------------------------------------------------------
    # Pause/Resume Operations
    # -------------------------------------------------------------------------

    async def _handle_pause(self, params: TaskIdParams) -> None:
        task_id = params["task_id"]
        logger.info(f"Pausing task: {task_id}")

        try:
            existing_task = await self.storage.load_task(task_id)
            if not existing_task:
                logger.warning(f"Task {task_id} not found for pause operation")
                return

            current_state = existing_task.get("status", {}).get("state", "working")
            if current_state in ("completed", "canceled", "failed"):
                logger.warning(f"Cannot pause task {task_id} in state: {current_state}")
                return

            checkpoint_data = await self._create_task_checkpoint(task_id)

            metadata = existing_task.get("metadata") or {}
            metadata["_checkpoint"] = checkpoint_data
            metadata["_paused_at"] = str(anyio.current_time())

            await self.storage.update_task(
                task_id=task_id,
                state="suspended",
                metadata=metadata,
            )
            logger.info(f"Task {task_id} paused successfully")

        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}", exc_info=True)
            await self.storage.update_task(task_id, state="failed")

    async def _handle_resume(self, params: TaskIdParams) -> None:
        task_id = params["task_id"]
        logger.info(f"Resuming task: {task_id}")

        try:
            existing_task = await self.storage.load_task(task_id)
            if not existing_task:
                logger.warning(f"Task {task_id} not found for resume operation")
                return

            current_state = existing_task.get("status", {}).get("state")
            if current_state != "suspended":
                logger.warning(
                    f"Cannot resume task {task_id} in state: {current_state}. Task must be in 'suspended' state."
                )
                return

            metadata = existing_task.get("metadata") or {}
            checkpoint_data = metadata.get("_checkpoint")

            if checkpoint_data:
                await self._restore_task_checkpoint(task_id, checkpoint_data)

            metadata.pop("_checkpoint", None)
            metadata.pop("_paused_at", None)

            await self.storage.update_task(
                task_id=task_id,
                state="resumed",
                metadata=metadata,
            )
            logger.info(f"Task {task_id} resumed successfully")

        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}", exc_info=True)
            await self.storage.update_task(task_id, state="failed")

    async def _create_task_checkpoint(self, task_id: Any) -> dict[str, Any]:
        task = await self.storage.load_task(task_id)
        if not task:
            return {}

        checkpoint = {
            "state": task.get("status", {}).get("state", "working"),
            "metadata": task.get("metadata", {}),
            "context_id": task.get("contextId"),
        }

        context_id = task.get("contextId")
        if context_id:
            context = await self.storage.load_context(context_id)
            if context:
                checkpoint["context"] = context

        return checkpoint

    async def _restore_task_checkpoint(
        self, task_id: Any, checkpoint: dict[str, Any]
    ) -> None:
        logger.debug(
            f"Restored checkpoint for task {task_id}: {checkpoint.get('state')}"
        )
