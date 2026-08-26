"""
bindu/retry.py

Production-grade retry mechanism for Bindu agent handlers.
Supports exponential backoff, jitter, custom retry conditions,
and async/sync handlers.

Roadmap item: "Retry Mechanism add."
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class RetryConfig:
    """Configuration for the retry decorator.

    Attributes:
        max_attempts:    Total number of attempts (1 = no retry).
        base_delay:      Initial delay in seconds before the first retry.
        max_delay:       Hard cap on delay between retries (seconds).
        backoff_factor:  Multiplier applied to delay after each attempt.
        jitter:          Add random jitter to avoid thundering-herd problems.
        retry_on:        Exception types that should trigger a retry.
                         Defaults to (Exception,) — retry on any error.
        reraise:         Re-raise the last exception when retries are
                         exhausted. If False, returns None instead.
        on_retry:        Optional callback invoked before each retry.
                         Signature: on_retry(attempt: int, exc: Exception)
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on: Sequence[Type[BaseException]] = field(
        default_factory=lambda: (Exception,)
    )
    reraise: bool = True
    on_retry: Callable[[int, BaseException], None] | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_delay(config: RetryConfig, attempt: int) -> float:
    """Return the delay (seconds) to wait before attempt *attempt* (1-indexed)."""
    delay = min(
        config.base_delay * (config.backoff_factor ** (attempt - 1)),
        config.max_delay,
    )
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


def _should_retry(exc: BaseException, retry_on: Sequence[Type[BaseException]]) -> bool:
    return isinstance(exc, tuple(retry_on))


# ---------------------------------------------------------------------------
# Synchronous retry
# ---------------------------------------------------------------------------

def retry(config: RetryConfig | None = None, **kwargs: Any) -> Callable:
    """Decorator that retries a synchronous callable on failure.

    Can be used with or without arguments:

        @retry
        def my_handler(messages): ...

        @retry(config=RetryConfig(max_attempts=5))
        def my_handler(messages): ...

        @retry(max_attempts=5, base_delay=0.5)
        def my_handler(messages): ...
    """
    if config is None:
        config = RetryConfig(**kwargs)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kw: Any) -> Any:
            last_exc: BaseException | None = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kw)
                except BaseException as exc:
                    if not _should_retry(exc, config.retry_on):
                        raise

                    last_exc = exc

                    if attempt == config.max_attempts:
                        break

                    delay = _compute_delay(config, attempt)
                    logger.warning(
                        "[bindu.retry] %s failed (attempt %d/%d). "
                        "Retrying in %.2fs. Error: %s",
                        func.__qualname__, attempt, config.max_attempts,
                        delay, exc,
                    )

                    if config.on_retry:
                        config.on_retry(attempt, exc)

                    time.sleep(delay)

            logger.error(
                "[bindu.retry] %s exhausted %d attempts. Last error: %s",
                func.__qualname__, config.max_attempts, last_exc,
            )
            if config.reraise and last_exc is not None:
                raise last_exc
            return None

        wrapper._retry_config = config  # expose for introspection / testing
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Async retry
# ---------------------------------------------------------------------------

def async_retry(config: RetryConfig | None = None, **kwargs: Any) -> Callable:
    """Decorator that retries an *async* callable on failure.

    Usage mirrors the synchronous ``retry`` decorator.
    """
    if config is None:
        config = RetryConfig(**kwargs)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kw: Any) -> Any:
            last_exc: BaseException | None = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kw)
                except BaseException as exc:
                    if not _should_retry(exc, config.retry_on):
                        raise

                    last_exc = exc

                    if attempt == config.max_attempts:
                        break

                    delay = _compute_delay(config, attempt)
                    logger.warning(
                        "[bindu.retry] %s failed (attempt %d/%d). "
                        "Retrying in %.2fs. Error: %s",
                        func.__qualname__, attempt, config.max_attempts,
                        delay, exc,
                    )

                    if config.on_retry:
                        config.on_retry(attempt, exc)

                    await asyncio.sleep(delay)

            logger.error(
                "[bindu.retry] %s exhausted %d attempts. Last error: %s",
                func.__qualname__, config.max_attempts, last_exc,
            )
            if config.reraise and last_exc is not None:
                raise last_exc
            return None

        wrapper._retry_config = config
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Convenience: wrap_handler
# ---------------------------------------------------------------------------

def wrap_handler(
    handler: Callable,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Callable:
    """Wrap an existing handler function with retry logic at runtime.

    This is useful when you don't own the handler source or want to attach
    retry configuration from a ``bindufy`` config dict.

    Example::

        from bindu.retry import wrap_handler, RetryConfig

        def my_handler(messages):
            ...

        resilient_handler = wrap_handler(
            my_handler,
            RetryConfig(max_attempts=4, base_delay=0.5),
        )
        bindufy(config, resilient_handler)
    """
    decorator = retry(config, **kwargs)
    return decorator(handler)
