"""Unit tests for Circuit Breaker pattern implementation.

Tests follow the TDD approach, covering:
- State machine transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure threshold behavior
- Recovery timeout behavior
- Async context manager usage
- Decorator pattern usage
- Exception handling
- Observability integration
- Registry pattern for monitoring

Reference: Michael T. Nygard's "Release It!" pattern
"""

import asyncio

import pytest


class TestCircuitBreakerState:
    """Test circuit breaker state enumeration."""

    def test_state_values(self):
        """Should define CLOSED, OPEN, and HALF_OPEN states."""
        from bindu.utils.circuit_breaker import CircuitBreakerState

        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_state_is_enum(self):
        """State should be a proper enum."""
        from bindu.utils.circuit_breaker import CircuitBreakerState
        from enum import Enum

        assert issubclass(CircuitBreakerState, Enum)


class TestCircuitBreakerError:
    """Test circuit breaker exception."""

    def test_error_attributes(self):
        """Error should contain breaker name and state."""
        from bindu.utils.circuit_breaker import CircuitBreakerError

        error = CircuitBreakerError("test_breaker", "Circuit is open")
        assert error.breaker_name == "test_breaker"
        assert "Circuit is open" in str(error)

    def test_error_inheritance(self):
        """Error should inherit from Exception."""
        from bindu.utils.circuit_breaker import CircuitBreakerError

        assert issubclass(CircuitBreakerError, Exception)


class TestCircuitBreakerInit:
    """Test circuit breaker initialization."""

    def test_default_values(self):
        """Should use sensible defaults from settings."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="test")
        assert breaker.name == "test"
        assert breaker.failure_threshold > 0
        assert breaker.recovery_timeout > 0
        assert breaker.half_open_max_calls > 0

    def test_custom_values(self):
        """Should accept custom configuration."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            name="custom",
            failure_threshold=10,
            recovery_timeout=60.0,
            half_open_max_calls=3,
        )
        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 60.0
        assert breaker.half_open_max_calls == 3

    def test_initial_state_is_closed(self):
        """Should start in CLOSED state."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_repr_shows_useful_info(self):
        """__repr__ should show name, state, and failure count."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="repr_test", failure_threshold=5)
        repr_str = repr(breaker)
        assert "CircuitBreaker(" in repr_str
        assert "repr_test" in repr_str
        assert "closed" in repr_str
        assert "failures=0/5" in repr_str


class TestCircuitBreakerClosedState:
    """Test behavior in CLOSED state."""

    @pytest.mark.asyncio
    async def test_successful_call_stays_closed(self):
        """Successful calls should keep circuit closed."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="test", failure_threshold=3)

        async def success():
            return "ok"

        result = await breaker.call(success)
        assert result == "ok"
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failed_call_increments_counter(self):
        """Failed calls should increment failure counter."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="test", failure_threshold=3)

        async def fail():
            raise ConnectionError("test error")  # Use ConnectionError (not excluded)

        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_threshold_reached_opens_circuit(self):
        """Circuit should open when failure threshold is reached."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="test", failure_threshold=3)

        async def fail():
            raise ConnectionError("test")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Successful call should reset failure counter."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="test", failure_threshold=3)

        async def fail():
            raise ConnectionError("test")  # Use ConnectionError (not excluded)

        async def success():
            return "ok"

        # Fail twice
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.failure_count == 2

        # Success should reset
        await breaker.call(success)
        assert breaker.failure_count == 0


class TestCircuitBreakerOpenState:
    """Test behavior in OPEN state."""

    @pytest.mark.asyncio
    async def test_calls_fail_fast(self):
        """Calls should fail immediately when circuit is open."""
        from bindu.utils.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerError,
            CircuitBreakerState,
        )

        breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60)

        async def fail():
            raise ConnectionError("test")

        # Open the circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitBreakerState.OPEN

        # Next call should fail fast
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(fail)

        assert exc_info.value.breaker_name == "test"

    @pytest.mark.asyncio
    async def test_function_not_called_when_open(self):
        """Function should not be executed when circuit is open."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError

        breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60)
        call_count = [0]

        async def fail():
            call_count[0] += 1
            raise ConnectionError("test")

        # Open the circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert call_count[0] == 1

        # Should not call function again
        with pytest.raises(CircuitBreakerError):
            await breaker.call(fail)

        assert call_count[0] == 1  # Still 1, not called


class TestCircuitBreakerHalfOpenState:
    """Test behavior in HALF_OPEN state."""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(
            name="test", failure_threshold=1, recovery_timeout=0.1
        )

        async def fail():
            raise ConnectionError("test")

        # Open the circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Check state (calling _check_state simulates next call attempt)
        breaker._check_state()
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_success_closes_circuit(self):
        """Successful call in HALF_OPEN should close circuit."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(
            name="test", failure_threshold=1, recovery_timeout=0.1
        )

        async def fail():
            raise ConnectionError("test")

        async def success():
            return "ok"

        # Open circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Successful call should close circuit
        result = await breaker.call(success)
        assert result == "ok"
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_reopens_circuit(self):
        """Failed call in HALF_OPEN should reopen circuit."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(
            name="test", failure_threshold=1, recovery_timeout=0.1
        )

        async def fail():
            raise ConnectionError("test")

        # Open circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Failed call should reopen circuit
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerExcludedExceptions:
    """Test exception exclusion behavior."""

    @pytest.mark.asyncio
    async def test_excluded_exception_not_counted(self):
        """Excluded exceptions should not count as failures."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        async def raise_value_error():
            raise ValueError("business error")

        # Should not count as failure
        with pytest.raises(ValueError):
            await breaker.call(raise_value_error)

        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_non_excluded_exception_counted(self):
        """Non-excluded exceptions should count as failures."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        async def raise_connection_error():
            raise ConnectionError("transient error")

        with pytest.raises(ConnectionError):
            await breaker.call(raise_connection_error)

        assert breaker.failure_count == 1


class TestCircuitBreakerContextManager:
    """Test async context manager interface."""

    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Context manager should work with successful code."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="test")

        async with breaker:
            result = "success"

        assert result == "success"
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_context_manager_failure(self):
        """Context manager should track failures."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="test", failure_threshold=3)

        with pytest.raises(ConnectionError):  # Use ConnectionError (not excluded)
            async with breaker:
                raise ConnectionError("test")

        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_context_manager_fail_fast(self):
        """Context manager should fail fast when open."""
        from bindu.utils.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerError,
            CircuitBreakerState,
        )

        breaker = CircuitBreaker(name="test", failure_threshold=1)

        # Open the circuit (use ConnectionError which is not excluded)
        with pytest.raises(ConnectionError):
            async with breaker:
                raise ConnectionError("test")

        assert breaker.state == CircuitBreakerState.OPEN

        # Should fail fast
        with pytest.raises(CircuitBreakerError):
            async with breaker:
                pass


class TestCircuitBreakerDecorator:
    """Test decorator interface."""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Decorator should work with successful functions."""
        from bindu.utils.circuit_breaker import circuit_breaker

        @circuit_breaker(name="test_decorator")
        async def my_function():
            return "success"

        result = await my_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_failure(self):
        """Decorator should track failures."""
        from bindu.utils.circuit_breaker import circuit_breaker, get_circuit_breaker

        @circuit_breaker(name="test_decorator_fail", failure_threshold=3)
        async def failing_function():
            raise ConnectionError("test")

        with pytest.raises(ConnectionError):
            await failing_function()

        breaker = get_circuit_breaker("test_decorator_fail")
        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_decorator_fail_fast(self):
        """Decorator should fail fast when circuit is open."""
        from bindu.utils.circuit_breaker import (
            circuit_breaker,
            CircuitBreakerError,
        )

        @circuit_breaker(name="test_decorator_fast", failure_threshold=1)
        async def failing_function():
            raise ConnectionError("test")

        # Open circuit
        with pytest.raises(ConnectionError):
            await failing_function()

        # Should fail fast
        with pytest.raises(CircuitBreakerError):
            await failing_function()


class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry."""

    def test_get_or_create(self):
        """Should get existing or create new breaker."""
        from bindu.utils.circuit_breaker import CircuitBreaker, get_circuit_breaker

        # Create new
        breaker1 = get_circuit_breaker("registry_test")
        assert isinstance(breaker1, CircuitBreaker)
        assert breaker1.name == "registry_test"

        # Get existing
        breaker2 = get_circuit_breaker("registry_test")
        assert breaker1 is breaker2

    def test_list_breakers(self):
        """Should list all registered breakers."""
        from bindu.utils.circuit_breaker import (
            get_circuit_breaker,
            list_circuit_breakers,
        )

        # Create some breakers
        get_circuit_breaker("list_test_1")
        get_circuit_breaker("list_test_2")

        breakers = list_circuit_breakers()
        names = [b.name for b in breakers]

        assert "list_test_1" in names
        assert "list_test_2" in names

    def test_get_breaker_stats(self):
        """Should return stats for all breakers."""
        from bindu.utils.circuit_breaker import (
            get_circuit_breaker,
            get_circuit_breaker_stats,
        )

        # Create a breaker to ensure it's in the registry
        get_circuit_breaker("stats_test")
        stats = get_circuit_breaker_stats()

        assert "stats_test" in stats
        assert "state" in stats["stats_test"]
        assert "failure_count" in stats["stats_test"]


class TestCircuitBreakerThreadSafety:
    """Test thread safety of circuit breaker."""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Circuit breaker should handle concurrent calls safely."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="concurrent_test", failure_threshold=100)
        success_count = [0]

        async def increment():
            success_count[0] += 1
            return "ok"

        # Run many concurrent calls
        tasks = [breaker.call(increment) for _ in range(50)]
        results = await asyncio.gather(*tasks)

        assert all(r == "ok" for r in results)
        assert success_count[0] == 50
        assert breaker.failure_count == 0


class TestCircuitBreakerMetrics:
    """Test metrics and observability."""

    def test_metrics_properties(self):
        """Should expose useful metrics."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="metrics_test")

        # Should have these properties
        assert hasattr(breaker, "state")
        assert hasattr(breaker, "failure_count")
        assert hasattr(breaker, "last_failure_time")
        assert hasattr(breaker, "last_success_time")

    @pytest.mark.asyncio
    async def test_timestamps_updated(self):
        """Timestamps should be updated on calls."""
        from bindu.utils.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(name="timestamp_test")

        async def success():
            return "ok"

        async def fail():
            raise ConnectionError("test")  # Use ConnectionError (not excluded)

        await breaker.call(success)
        assert breaker.last_success_time is not None

        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.last_failure_time is not None


class TestCircuitBreakerManualControl:
    """Test manual circuit control."""

    def test_manual_open(self):
        """Should allow manually opening the circuit."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="manual_test")
        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.open()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_manual_close(self):
        """Should allow manually closing the circuit."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="manual_close_test")
        breaker.open()
        assert breaker.state == CircuitBreakerState.OPEN

        breaker.close()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_manual_reset(self):
        """Should allow resetting the circuit breaker."""
        from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerState

        breaker = CircuitBreaker(name="reset_test", failure_threshold=5)

        # Simulate some failures
        breaker._failure_count = 3
        breaker._state = CircuitBreakerState.OPEN

        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
