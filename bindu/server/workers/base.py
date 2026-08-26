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
from datetime import datetime

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
    # Future Operations (Not Yet Implemented)
    # -------------------------------------------------------------------------

    async def _handle_pause(self, params: TaskIdParams) -> None:
        """Handle pause operation.

        TODO: Implement task pause functionality
        - Save current execution state
        - Update task to 'suspended' state
        - Release resources while preserving context
        """
        task_id = self._normalize_uuid(params["task_id"])

        # Load task and prepare metadata
        task = await self.storage.load_task(task_id)
        if not task:
            logger.warning(f"Pause requested for unknown task {task_id}")
            return

        metadata = dict(task.get("metadata") or {})

        # Allow subclasses to capture rich execution state
        checkpoint = None
        capture = getattr(self, "capture_execution_state", None)
        if callable(capture):
            try:
                maybe = capture(task_id)
                if hasattr(maybe, "__await__"):
                    checkpoint = await maybe
                else:
                    checkpoint = maybe
            except Exception:
                logger.exception("capture_execution_state hook failed")

        metadata["suspended"] = True
        metadata["suspended_at"] = datetime.utcnow().isoformat() + "Z"
        if checkpoint is not None:
            # Checkpoint must be JSON-serializable; storage implementations
            # may enforce further constraints.
            metadata["suspended_checkpoint"] = checkpoint

        # Allow subclass hook to release resources (best-effort)
        on_pause = getattr(self, "on_pause", None)
        if callable(on_pause):
            try:
                maybe = on_pause(task_id)
                if hasattr(maybe, "__await__"):
                    await maybe
            except Exception:
                logger.exception("on_pause hook failed")

        await self.storage.update_task(task_id, state="suspended", metadata=metadata)

    async def _handle_resume(self, params: TaskIdParams) -> None:
        """Handle resume operation.

        TODO: Implement task resume functionality
        - Restore execution state
        - Update task to 'resumed' state
        - Continue from last checkpoint
        """
        task_id = self._normalize_uuid(params["task_id"])

        task = await self.storage.load_task(task_id)
        if not task:
            logger.warning(f"Resume requested for unknown task {task_id}")
            return

        metadata = dict(task.get("metadata") or {})

        checkpoint = metadata.get("suspended_checkpoint")

        # Allow subclass to restore execution state
        restore = getattr(self, "restore_execution_state", None)
        if callable(restore):
            try:
                maybe = restore(task_id, checkpoint)
                if hasattr(maybe, "__await__"):
                    await maybe
            except Exception:
                logger.exception("restore_execution_state hook failed")

        # Allow subclass hook to re-acquire resources
        on_resume = getattr(self, "on_resume", None)
        if callable(on_resume):
            try:
                maybe = on_resume(task_id)
                if hasattr(maybe, "__await__"):
                    await maybe
            except Exception:
                logger.exception("on_resume hook failed")

        # Clean up suspended metadata and mark resumed
        metadata.pop("suspended", None)
        metadata.pop("suspended_checkpoint", None)
        metadata["resumed_at"] = datetime.utcnow().isoformat() + "Z"

        await self.storage.update_task(task_id, state="resumed", metadata=metadata)
