"""Redis scheduler implementation."""

from __future__ import annotations as _annotations

import json
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Any

import redis.asyncio as redis
from opentelemetry.trace import get_current_span
from pydantic import BaseModel

from bindu.common.protocol.types import TaskIdParams, TaskSendParams
from bindu.utils.logging import get_logger

from .base import (
    Scheduler,
    TaskOperation,
    _CancelTask,
    _PauseTask,
    _ResumeTask,
    _RunTask,
)

logger = get_logger("bindu.server.scheduler.redis_scheduler")


class RedisScheduler(Scheduler):
    """A Redis-based scheduler using Redis for distributed task operations."""

    def __init__(
        self,
        redis_url: str,
        queue_name: str = "bindu:tasks",
        max_connections: int = 10,
        retry_on_timeout: bool = True,
        socket_connect_timeout: int = 5,
    ):
        """Initialize Redis scheduler.

        Args:
            redis_url: Redis URL (redis://localhost:6379 or redis://...)
            queue_name: Redis queue name for task operations
            max_connections: Maximum Redis connection pool size
            retry_on_timeout: Whether to retry on Redis timeout
            socket_connect_timeout: Socket connection timeout in seconds
        """
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self._redis_client: redis.Redis | None = None
        self.aexit_stack: AsyncExitStack | None = None

    async def __aenter__(self):
        """Initialize Redis connection pool."""
        self.aexit_stack = AsyncExitStack()
        await self.aexit_stack.__aenter__()

        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )

            # Test connection
            await self._redis_client.ping()
            logger.info(f"Redis scheduler connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            await self.aexit_stack.__aexit__(None, None, None)
            raise

        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Close Redis connection pool."""
        if self._redis_client:
            try:
                await self._redis_client.aclose()
                logger.info("Redis scheduler connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._redis_client = None

        if self.aexit_stack:
            await self.aexit_stack.__aexit__(exc_type, exc_value, traceback)

    async def run_task(self, params: TaskSendParams) -> None:
        """Send a run task operation to Redis queue."""
        logger.debug(f"Running task: {params}")
        task_operation = _RunTask(
            operation="run", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    async def cancel_task(self, params: TaskIdParams) -> None:
        """Send a cancel task operation to Redis queue."""
        logger.debug(f"Canceling task: {params}")
        task_operation = _CancelTask(
            operation="cancel", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    async def pause_task(self, params: TaskIdParams) -> None:
        """Send a pause task operation to Redis queue."""
        logger.debug(f"Pausing task: {params}")
        task_operation = _PauseTask(
            operation="pause", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    async def resume_task(self, params: TaskIdParams) -> None:
        """Send a resume task operation to Redis queue."""
        logger.debug(f"Resuming task: {params}")
        task_operation = _ResumeTask(
            operation="resume", params=params, _current_span=get_current_span()
        )
        await self._push_task_operation(task_operation)

    async def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from Redis queue using blocking pop."""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized. Use async context manager.")

        logger.info(f"Starting to receive task operations from queue: {self.queue_name}")

        while True:
            try:
                # Blocking pop with 1 second timeout
                result = await self._redis_client.blpop(self.queue_name, timeout=1)

                if result:
                    _, task_data = result
                    task_operation = self._deserialize_task_operation(task_data)
                    logger.debug(
                        f"Received task operation: {task_operation['operation']}"
                    )
                    yield task_operation

            except redis.RedisError as e:
                # Log error and continue (could add exponential backoff here)
                logger.error(f"Redis error in receive_task_operations: {e}")
                continue
            except Exception as e:
                # Log unexpected errors
                logger.error(f"Unexpected error in receive_task_operations: {e}")
                continue

    async def _push_task_operation(self, task_operation: TaskOperation) -> None:
        """Push a task operation to Redis queue."""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized. Use async context manager.")

        serialized_task = self._serialize_task_operation(task_operation)
        await self._redis_client.rpush(self.queue_name, serialized_task)
        logger.debug(
            f"Pushed task operation {task_operation['operation']} to queue {self.queue_name}"
        )

    def _serialize_task_operation(self, task_operation: TaskOperation) -> str:
        """Serialize task operation to JSON string for Redis storage."""
        # Convert span to string representation (spans are not JSON serializable)
        span = task_operation["_current_span"]
        span_id = None
        trace_id = None

        # Try to get span context if available (handle both real and mock spans)
        if hasattr(span, "get_span_context"):
            span_context = span.get_span_context()
            if hasattr(span_context, "span_id") and span_context.span_id:
                span_id = format(span_context.span_id, "016x")
            if hasattr(span_context, "trace_id") and span_context.trace_id:
                trace_id = format(span_context.trace_id, "032x")

        serializable_task = {
            "operation": task_operation["operation"],
            "params": task_operation["params"],
            "span_id": span_id,
            "trace_id": trace_id,
        }
        return json.dumps(serializable_task, default=str)

    def _deserialize_task_operation(self, task_data: str) -> TaskOperation:
        """Deserialize task operation from JSON string."""
        data = json.loads(task_data)

        # Reconstruct the task operation (span will be recreated by the worker)
        operation = data["operation"]
        params = data["params"]
        current_span = get_current_span()

        if operation == "run":
            return _RunTask(
                operation="run",
                params=params,
                _current_span=current_span,
            )
        elif operation == "cancel":
            return _CancelTask(
                operation="cancel", params=params, _current_span=current_span
            )
        elif operation == "pause":
            return _PauseTask(
                operation="pause", params=params, _current_span=current_span
            )
        elif operation == "resume":
            return _ResumeTask(
                operation="resume", params=params, _current_span=current_span
            )
        else:
            raise ValueError(f"Unknown operation type: {operation}")

    async def get_queue_length(self) -> int:
        """Get the current length of the task queue."""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized. Use async context manager.")

        length = await self._redis_client.llen(self.queue_name)
        return length

    async def clear_queue(self) -> int:
        """Clear all tasks from the queue. Returns number of tasks removed."""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized. Use async context manager.")

        deleted = await self._redis_client.delete(self.queue_name)
        logger.info(f"Cleared {deleted} tasks from queue {self.queue_name}")
        return deleted

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if not self._redis_client:
                return False
            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
