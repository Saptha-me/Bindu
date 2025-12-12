"""Retry configuration and decorators using Tenacity.

This module provides retry mechanisms for various operations in Bindu:
- Worker task execution
- Storage operations (database, redis)
- External API calls
- Scheduler operations

Retry Strategies:
- Exponential backoff with jitter
- Configurable max attempts
- Custom retry conditions
- Logging and observability integration
"""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)
from tenacity.wait import wait_random_exponential

from bindu.utils.logging import get_logger
from bindu.settings import app_settings

logger = get_logger("bindu.utils.retry")

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])

# Common transient errors that should trigger retries
# Note: Only includes truly transient errors (network, timeout, connection)
# Application logic errors (ValueError, KeyError, etc.) should not be retried
TRANSIENT_EXCEPTIONS = (
    # Network errors
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    ConnectionAbortedError,
    # Timeout errors
    TimeoutError,
    asyncio.TimeoutError,
    # OS errors
    OSError,  # Covers BrokenPipeError, etc.
)


def retry_worker_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for worker task execution operations.

    Retries on transient failures with exponential backoff and jitter.
    Logs retry attempts for observability.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_worker_operation()
        async def run_task(self, params):
            # Task execution logic
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.worker_max_attempts
            _min_wait = min_wait or app_settings.retry.worker_min_wait
            _max_wait = max_wait or app_settings.retry.worker_max_wait

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing {func.__name__} (attempt {attempt.retry_state.attempt_number}/{_max_attempts})"  # type: ignore[attr-defined]
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def retry_storage_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for storage operations (database, redis).

    Handles transient database connection issues, deadlocks, and timeouts.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_storage_operation()
        async def update_task(self, task_id, state):
            # Database update logic
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.storage_max_attempts
            _min_wait = min_wait or app_settings.retry.storage_min_wait
            _max_wait = max_wait or app_settings.retry.storage_max_wait

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_exponential(multiplier=1, min=_min_wait, max=_max_wait),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing storage operation {func.__name__} "  # type: ignore[attr-defined]
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def retry_scheduler_operation(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for scheduler operations.

    Handles transient failures in task scheduling and broker communication.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_scheduler_operation()
        async def run_task(self, params):
            # Scheduler logic
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.scheduler_max_attempts
            _min_wait = min_wait or app_settings.retry.scheduler_min_wait
            _max_wait = max_wait or app_settings.retry.scheduler_max_wait

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing scheduler operation {func.__name__} "  # type: ignore[attr-defined]
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def retry_api_call(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> Callable[[F], F]:
    """Retry decorator for external API calls.

    Handles transient network failures, rate limits, and timeouts.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_api_call()
        async def call_external_service(self, data):
            # API call logic
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_attempts = max_attempts or app_settings.retry.api_max_attempts
            _min_wait = min_wait or app_settings.retry.api_min_wait
            _max_wait = max_wait or app_settings.retry.api_max_wait

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_max_attempts),
                wait=wait_random_exponential(
                    multiplier=1, min=_min_wait, max=_max_wait
                ),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                after=after_log(logger, logging.INFO),
                reraise=True,
            ):
                with attempt:
                    logger.debug(
                        f"Executing API call {func.__name__} "  # type: ignore[attr-defined]
                        f"(attempt {attempt.retry_state.attempt_number}/{_max_attempts})"
                    )
                    return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception should trigger a retry.

    Args:
        exception: Exception to check

    Returns:
        True if the exception is retryable, False otherwise
    """
    return isinstance(exception, TRANSIENT_EXCEPTIONS)


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic.

    Utility function for ad-hoc retry logic without decorators.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function execution

    Raises:
        RetryError: If all retry attempts fail

    Example:
        result = await execute_with_retry(
            some_async_function,
            arg1, arg2,
            max_attempts=5,
            kwarg1=value1
        )
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    ):
        with attempt:
            logger.debug(
                f"Executing {func.__name__} "  # type: ignore[attr-defined]
                f"(attempt {attempt.retry_state.attempt_number}/{max_attempts})"
            )
            return await func(*args, **kwargs)
