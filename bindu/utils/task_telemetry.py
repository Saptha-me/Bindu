"""
TaskManager-specific OpenTelemetry instrumentation.

This module provides decorators and utilities for instrumenting TaskManager operations
with comprehensive tracing, metrics, and logging.
"""

import functools
import time
from typing import Any, Callable, TypeVar, cast
from uuid import UUID

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from pebbling.utils.logging import get_logger

# Get tracer and meter for TaskManager operations
tracer = trace.get_tracer("pebbling.server.task_manager")
meter = metrics.get_meter("pebbling.server.task_manager")

# Metrics
task_counter = meter.create_counter("pebbling_tasks_total", description="Total number of tasks processed", unit="1")

task_duration = meter.create_histogram(
    "pebbling_task_duration_seconds", description="Task processing duration", unit="s"
)

active_tasks = meter.create_up_down_counter(
    "pebbling_active_tasks", description="Number of currently active tasks", unit="1"
)

context_counter = meter.create_counter(
    "pebbling_contexts_total", description="Total number of contexts managed", unit="1"
)

logger = get_logger()

F = TypeVar("F", bound=Callable[..., Any])


def trace_task_operation(operation_name: str, include_params: bool = True):
    """
    Decorator to trace TaskManager operations with comprehensive telemetry.

    Args:
        operation_name: Name of the operation for span naming
        include_params: Whether to include request parameters in span attributes
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            # Extract key identifiers
            request_id = str(request.get("id", "unknown"))
            params = request.get("params", {})

            # Create span with hierarchical naming
            span_name = f"task_manager.{operation_name}"

            with tracer.start_as_current_span(span_name) as span:
                start_time = time.time()

                # Set basic span attributes
                span.set_attributes(
                    {
                        "pebbling.operation": operation_name,
                        "pebbling.request_id": request_id,
                        "pebbling.component": "task_manager",
                    }
                )

                # Add operation-specific attributes
                if include_params:
                    if "task_id" in params:
                        span.set_attribute("pebbling.task_id", str(params["task_id"]))
                    if "context_id" in params:
                        span.set_attribute("pebbling.context_id", str(params["context_id"]))
                    if "message" in params:
                        # Add message metadata without sensitive content
                        message = params["message"]
                        if isinstance(message, dict):
                            span.set_attribute("pebbling.message_type", message.get("type", "unknown"))
                            if "parts" in message:
                                span.set_attribute("pebbling.message_parts_count", len(message["parts"]))

                try:
                    # Execute the operation
                    result = await func(self, request, *args, **kwargs)

                    # Record success metrics
                    duration = time.time() - start_time
                    task_duration.record(duration, {"operation": operation_name, "status": "success"})

                    task_counter.add(1, {"operation": operation_name, "status": "success"})

                    # Set success status
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("pebbling.success", True)

                    # Add result metadata
                    if hasattr(result, "get") and "result" in result:
                        result_data = result["result"]
                        if isinstance(result_data, dict):
                            if "task_id" in result_data:
                                span.set_attribute("pebbling.result_task_id", str(result_data["task_id"]))
                            if "status" in result_data:
                                span.set_attribute("pebbling.task_status", result_data["status"])

                    logger.info(
                        f"TaskManager.{operation_name} completed successfully",
                        extra={"request_id": request_id, "duration": duration, "operation": operation_name},
                    )

                    return result

                except Exception as e:
                    # Record error metrics
                    duration = time.time() - start_time
                    task_duration.record(duration, {"operation": operation_name, "status": "error"})

                    task_counter.add(
                        1, {"operation": operation_name, "status": "error", "error_type": type(e).__name__}
                    )

                    # Set error status
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attributes(
                        {
                            "pebbling.success": False,
                            "pebbling.error_type": type(e).__name__,
                            "pebbling.error_message": str(e),
                        }
                    )

                    logger.error(
                        f"TaskManager.{operation_name} failed",
                        extra={
                            "request_id": request_id,
                            "duration": duration,
                            "operation": operation_name,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

                    raise

        return cast(F, wrapper)

    return decorator


def track_active_task(func: F) -> F:
    """Decorator to track active task count for operations that create/destroy tasks."""

    @functools.wraps(func)
    async def wrapper(self, request, *args, **kwargs):
        operation = func.__name__

        # Increment active tasks for creation operations
        if operation in ["send_message"]:
            active_tasks.add(1, {"operation": "create"})

        try:
            result = await func(self, request, *args, **kwargs)

            # Decrement active tasks for completion/cancellation operations
            if operation in ["cancel_task"]:
                active_tasks.add(-1, {"operation": "cancel"})

            return result

        except Exception:
            # Decrement on error for creation operations
            if operation in ["send_message"]:
                active_tasks.add(-1, {"operation": "error"})
            raise

    return cast(F, wrapper)


def trace_context_operation(operation_name: str):
    """Decorator specifically for context management operations."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            request_id = str(request.get("id", "unknown"))
            params = request.get("params", {})

            with tracer.start_as_current_span(f"context_manager.{operation_name}") as span:
                span.set_attributes(
                    {
                        "pebbling.operation": operation_name,
                        "pebbling.request_id": request_id,
                        "pebbling.component": "context_manager",
                    }
                )

                if "context_id" in params:
                    span.set_attribute("pebbling.context_id", str(params["context_id"]))

                try:
                    result = await func(self, request, *args, **kwargs)

                    # Record context metrics
                    context_counter.add(1, {"operation": operation_name, "status": "success"})

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    context_counter.add(
                        1, {"operation": operation_name, "status": "error", "error_type": type(e).__name__}
                    )

                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("pebbling.error_type", type(e).__name__)
                    raise

        return cast(F, wrapper)

    return decorator


# Custom span creation utilities
def create_task_span(task_id: UUID, operation: str, context_id: UUID | None = None):
    """Create a task-specific span with standard attributes."""
    span = tracer.start_span(f"task.{operation}")
    span.set_attributes(
        {"pebbling.task_id": str(task_id), "pebbling.operation": operation, "pebbling.component": "task"}
    )

    if context_id:
        span.set_attribute("pebbling.context_id", str(context_id))

    return span


def record_task_metrics(operation: str, duration: float, status: str, **labels):
    """Record task-related metrics with consistent labeling."""
    base_labels = {"operation": operation, "status": status}
    base_labels.update(labels)

    task_duration.record(duration, base_labels)
    task_counter.add(1, base_labels)
