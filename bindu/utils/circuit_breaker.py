"""Circuit Breaker pattern implementation for production resilience.

This module provides a production-grade circuit breaker to prevent cascade
failures when external services (LLMs, APIs, databases) are degraded or
unavailable.

The circuit breaker pattern is described in Michael T. Nygard's book
"Release It!" and is essential for building resilient distributed systems.

States:
    CLOSED: Normal operation - requests pass through, failures tracked
    OPEN: Fail-fast mode - requests rejected immediately without calling service
    HALF_OPEN: Recovery testing - limited requests allowed to test if service recovered

State Transitions:
    CLOSED → OPEN: When failure_threshold consecutive failures occur
    OPEN → HALF_OPEN: After recovery_timeout seconds elapse
    HALF_OPEN → CLOSED: When a test call succeeds
    HALF_OPEN → OPEN: When a test call fails

Usage:
    # Decorator pattern
    @circuit_breaker(name="openai", failure_threshold=5)
    async def call_openai(prompt: str) -> str:
        ...

    # Context manager pattern
    breaker = CircuitBreaker(name="anthropic")
    async with breaker:
        result = await anthropic_client.messages.create(...)

    # Direct call pattern
    breaker = get_circuit_breaker("external_api")
    result = await breaker.call(my_async_function, arg1, arg2)

    # Monitoring
    stats = get_circuit_breaker_stats()
    breakers = list_circuit_breakers()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.circuit_breaker")

# Type variables for generic typing
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


# -----------------------------------------------------------------------------
# State Enumeration
# -----------------------------------------------------------------------------


class CircuitBreakerState(Enum):
    """Circuit breaker states following the standard pattern."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# -----------------------------------------------------------------------------
# Custom Exception
# -----------------------------------------------------------------------------


class CircuitBreakerError(Exception):
    """Raised when a call is rejected because the circuit is open.

    Attributes:
        breaker_name: Name of the circuit breaker that rejected the call
        message: Human-readable error message
    """

    def __init__(self, breaker_name: str, message: str = "Circuit is open"):
        self.breaker_name = breaker_name
        self.message = message
        super().__init__(f"CircuitBreaker '{breaker_name}': {message}")


# -----------------------------------------------------------------------------
# Global Registry
# -----------------------------------------------------------------------------

# Thread-safe registry of all circuit breakers
_registry: dict[str, "CircuitBreaker"] = {}
_registry_lock = asyncio.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
    half_open_max_calls: int | None = None,
    excluded_exceptions: tuple[type[Exception], ...] | None = None,
) -> "CircuitBreaker":
    """Get or create a circuit breaker by name.

    This function provides a singleton pattern for circuit breakers,
    ensuring that the same breaker instance is used throughout the application.

    Args:
        name: Unique identifier for the circuit breaker
        failure_threshold: Override default failure threshold
        recovery_timeout: Override default recovery timeout
        half_open_max_calls: Override default half-open max calls
        excluded_exceptions: Override default excluded exceptions

    Returns:
        CircuitBreaker instance (existing or newly created)
    """
    if name not in _registry:
        _registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            excluded_exceptions=excluded_exceptions,
        )
    return _registry[name]


def list_circuit_breakers() -> list["CircuitBreaker"]:
    """List all registered circuit breakers.

    Returns:
        List of all CircuitBreaker instances
    """
    return list(_registry.values())


def get_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all registered circuit breakers.

    Returns:
        Dictionary mapping breaker names to their stats
    """
    return {
        name: {
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
            "failure_threshold": breaker.failure_threshold,
            "recovery_timeout": breaker.recovery_timeout,
            "last_failure_time": breaker.last_failure_time,
            "last_success_time": breaker.last_success_time,
            "last_state_change": breaker._last_state_change,
        }
        for name, breaker in _registry.items()
    }


# -----------------------------------------------------------------------------
# Circuit Breaker Implementation
# -----------------------------------------------------------------------------


@dataclass
class CircuitBreaker:
    """Production-grade circuit breaker for async operations.

    Implements the circuit breaker pattern with:
    - Three-state machine (CLOSED, OPEN, HALF_OPEN)
    - Configurable failure thresholds and timeouts
    - Thread-safe state transitions using asyncio.Lock
    - Excluded exceptions for business logic errors
    - Observability integration (logging, Sentry)
    - Multiple usage patterns (decorator, context manager, direct call)

    Attributes:
        name: Unique identifier for this circuit breaker
        failure_threshold: Failures before circuit opens
        recovery_timeout: Seconds before attempting recovery
        half_open_max_calls: Max calls allowed in HALF_OPEN state
        excluded_exceptions: Exception types that don't count as failures

    Example:
        breaker = CircuitBreaker(name="openai_api", failure_threshold=5)

        # Direct call
        result = await breaker.call(my_async_function, arg1, arg2)

        # Context manager
        async with breaker:
            result = await my_async_function()
    """

    name: str
    failure_threshold: int = field(default=None)  # type: ignore
    recovery_timeout: float = field(default=None)  # type: ignore
    half_open_max_calls: int = field(default=None)  # type: ignore
    excluded_exceptions: tuple[type[Exception], ...] = field(default=None)  # type: ignore

    # Internal state
    _state: CircuitBreakerState = field(
        default=CircuitBreakerState.CLOSED, init=False, repr=False
    )
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float | None = field(default=None, init=False, repr=False)
    _last_success_time: float | None = field(default=None, init=False, repr=False)
    _last_state_change: float | None = field(default=None, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)
    _half_open_calls: int = field(default=0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def __post_init__(self):
        """Initialize with settings defaults if not provided."""
        settings = app_settings.circuit_breaker

        if self.failure_threshold is None:
            self.failure_threshold = settings.failure_threshold

        if self.recovery_timeout is None:
            self.recovery_timeout = settings.recovery_timeout

        if self.half_open_max_calls is None:
            self.half_open_max_calls = settings.half_open_max_calls

        if self.excluded_exceptions is None:
            # Convert string exception names to actual exception classes
            self.excluded_exceptions = tuple(
                _resolve_exception(name) for name in settings.excluded_exceptions
            )

        logger.debug(
            f"CircuitBreaker '{self.name}' initialized: "
            f"threshold={self.failure_threshold}, "
            f"timeout={self.recovery_timeout}s"
        )

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return (
            f"CircuitBreaker(name={self.name!r}, state={self._state.value!r}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def state(self) -> CircuitBreakerState:
        """Current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    @property
    def last_failure_time(self) -> float | None:
        """Timestamp of last failure (Unix epoch)."""
        return self._last_failure_time

    @property
    def last_success_time(self) -> float | None:
        """Timestamp of last success (Unix epoch)."""
        return self._last_success_time

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def _check_state(self) -> None:
        """Check and potentially transition state based on timeout.

        Called before each operation to handle OPEN → HALF_OPEN transition.
        """
        if self._state == CircuitBreakerState.OPEN and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                self._half_open_calls = 0

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Transition to a new state with logging and notifications.

        Args:
            new_state: Target state to transition to
        """
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self._last_state_change = time.monotonic()

        if new_state == CircuitBreakerState.OPEN:
            self._opened_at = time.monotonic()

        # Log state change
        if app_settings.circuit_breaker.log_state_changes:
            logger.warning(
                f"CircuitBreaker '{self.name}' state change: "
                f"{old_state.value} → {new_state.value} "
                f"(failures: {self._failure_count})"
            )

        # Notify Sentry if enabled
        if app_settings.circuit_breaker.notify_sentry and app_settings.sentry.enabled:
            self._notify_sentry(old_state, new_state)

    def _notify_sentry(
        self, old_state: CircuitBreakerState, new_state: CircuitBreakerState
    ) -> None:
        """Send state change notification to Sentry."""
        try:
            from bindu.observability.sentry import add_breadcrumb, capture_message

            # Add breadcrumb for context
            add_breadcrumb(
                message=f"Circuit breaker '{self.name}' state: {old_state.value} → {new_state.value}",
                category="circuit_breaker",
                level="warning" if new_state == CircuitBreakerState.OPEN else "info",
                data={
                    "breaker_name": self.name,
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    "failure_count": self._failure_count,
                },
            )

            # Capture message for OPEN state transitions
            if new_state == CircuitBreakerState.OPEN:
                capture_message(
                    f"Circuit breaker '{self.name}' opened after {self._failure_count} failures",
                    level="warning",
                    tags={"circuit_breaker": self.name},
                    extra={
                        "failure_threshold": self.failure_threshold,
                        "recovery_timeout": self.recovery_timeout,
                    },
                )
        except Exception as e:
            logger.debug(f"Failed to notify Sentry: {e}")

    def _record_success(self) -> None:
        """Record a successful call."""
        self._last_success_time = time.monotonic()
        self._failure_count = 0

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._transition_to(CircuitBreakerState.CLOSED)

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call.

        Args:
            exception: The exception that caused the failure
        """
        # Check if exception should be excluded
        if isinstance(exception, self.excluded_exceptions):
            logger.debug(
                f"CircuitBreaker '{self.name}': Excluded exception {type(exception).__name__}"
            )
            return

        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitBreakerState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately reopens the circuit
            self._transition_to(CircuitBreakerState.OPEN)

    # -------------------------------------------------------------------------
    # Manual Control
    # -------------------------------------------------------------------------

    def open(self) -> None:
        """Manually open the circuit breaker."""
        self._transition_to(CircuitBreakerState.OPEN)

    def close(self) -> None:
        """Manually close the circuit breaker and reset failure count."""
        self._failure_count = 0
        self._transition_to(CircuitBreakerState.CLOSED)

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._failure_count = 0
        self._half_open_calls = 0
        self._opened_at = None
        self._transition_to(CircuitBreakerState.CLOSED)

    # -------------------------------------------------------------------------
    # Call Execution
    # -------------------------------------------------------------------------

    async def call(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by the function
        """
        async with self._lock:
            self._check_state()

            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    self.name,
                    f"Circuit is open. Recovery in {self._time_until_recovery():.1f}s",
                )

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._record_success()
            return result

        except Exception as e:
            async with self._lock:
                self._record_failure(e)
            raise

    def _time_until_recovery(self) -> float:
        """Calculate time until circuit attempts recovery."""
        if self._opened_at is None:
            return 0.0
        elapsed = time.monotonic() - self._opened_at
        remaining = self.recovery_timeout - elapsed
        return max(0.0, remaining)

    # -------------------------------------------------------------------------
    # Context Manager Interface
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> "CircuitBreaker":
        """Enter async context manager.

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            self._check_state()

            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    self.name,
                    f"Circuit is open. Recovery in {self._time_until_recovery():.1f}s",
                )

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit async context manager.

        Records success or failure based on exception state.
        """
        async with self._lock:
            if exc_val is None:
                self._record_success()
            else:
                self._record_failure(exc_val)

        # Don't suppress the exception
        return False


# -----------------------------------------------------------------------------
# Decorator
# -----------------------------------------------------------------------------


def circuit_breaker(
    name: str,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
    half_open_max_calls: int | None = None,
    excluded_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[F], F]:
    """Decorator to wrap an async function with a circuit breaker.

    Args:
        name: Unique identifier for the circuit breaker
        failure_threshold: Override default failure threshold
        recovery_timeout: Override default recovery timeout
        half_open_max_calls: Override default half-open max calls
        excluded_exceptions: Override default excluded exceptions

    Returns:
        Decorated function

    Example:
        @circuit_breaker(name="openai", failure_threshold=5)
        async def call_openai(prompt: str) -> str:
            async with httpx.AsyncClient() as client:
                response = await client.post(...)
                return response.json()
    """

    def decorator(func: F) -> F:
        breaker = get_circuit_breaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            excluded_exceptions=excluded_exceptions,
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.call(func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def _resolve_exception(name: str) -> type[Exception]:
    """Resolve an exception class from its name.

    Args:
        name: Simple name or fully qualified name of exception class

    Returns:
        Exception class
    """
    # Common built-in exceptions
    builtins = {
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "IndexError": IndexError,
        "FileNotFoundError": FileNotFoundError,
        "PermissionError": PermissionError,
        "NotImplementedError": NotImplementedError,
    }

    if name in builtins:
        return builtins[name]

    # Try to import fully qualified name
    if "." in name:
        module_name, class_name = name.rsplit(".", 1)
        try:
            import importlib

            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            logger.warning(f"Could not resolve exception: {name}, defaulting to Exception")
            return Exception

    return Exception
