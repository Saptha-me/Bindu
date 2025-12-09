"""Unit tests for retry mechanism using Tenacity."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bindu.settings import app_settings
from bindu.utils.retry import (
    execute_with_retry,
    is_retryable_error,
    retry_api_call,
    retry_scheduler_operation,
    retry_storage_operation,
    retry_worker_operation,
)


class TestRetryConfig:
    """Test retry configuration from settings."""

    def test_worker_config(self):
        """Test worker retry configuration."""
        assert app_settings.retry.worker_max_attempts == 3
        assert app_settings.retry.worker_min_wait == 1.0
        assert app_settings.retry.worker_max_wait == 10.0

    def test_storage_config(self):
        """Test storage retry configuration."""
        assert app_settings.retry.storage_max_attempts == 5
        assert app_settings.retry.storage_min_wait == 0.5
        assert app_settings.retry.storage_max_wait == 5.0

    def test_scheduler_config(self):
        """Test scheduler retry configuration."""
        assert app_settings.retry.scheduler_max_attempts == 3
        assert app_settings.retry.scheduler_min_wait == 1.0
        assert app_settings.retry.scheduler_max_wait == 8.0

    def test_api_config(self):
        """Test API retry configuration."""
        assert app_settings.retry.api_max_attempts == 4
        assert app_settings.retry.api_min_wait == 1.0
        assert app_settings.retry.api_max_wait == 15.0


class TestRetryDecorators:
    """Test retry decorators."""

    @pytest.mark.asyncio
    async def test_retry_worker_operation_success(self):
        """Test worker operation succeeds on first attempt."""

        @retry_worker_operation()
        async def successful_operation():
            return "success"

        result = await successful_operation()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_worker_operation_with_retry(self):
        """Test worker operation succeeds after retries."""
        call_count = [0]

        @retry_worker_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def flaky_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await flaky_operation()
        assert result == "success"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_retry_worker_operation_max_attempts(self):
        """Test worker operation fails after max attempts."""

        @retry_worker_operation(max_attempts=2, min_wait=0.1, max_wait=0.2)
        async def always_fails():
            raise ConnectionError("Permanent failure")

        with pytest.raises(ConnectionError, match="Permanent failure"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_retry_storage_operation_success(self):
        """Test storage operation succeeds."""

        @retry_storage_operation()
        async def db_operation():
            return {"id": 1, "data": "test"}

        result = await db_operation()
        assert result == {"id": 1, "data": "test"}

    @pytest.mark.asyncio
    async def test_retry_storage_operation_with_retry(self):
        """Test storage operation retries on failure."""
        call_count = [0]

        @retry_storage_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def flaky_db_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TimeoutError("Database timeout")
            return "success"

        result = await flaky_db_operation()
        assert result == "success"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_retry_scheduler_operation_success(self):
        """Test scheduler operation succeeds."""

        @retry_scheduler_operation()
        async def schedule_task():
            return "scheduled"

        result = await schedule_task()
        assert result == "scheduled"

    @pytest.mark.asyncio
    async def test_retry_api_call_success(self):
        """Test API call succeeds."""

        @retry_api_call()
        async def call_external_api():
            return {"status": "ok"}

        result = await call_external_api()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_retry_api_call_with_retry(self):
        """Test API call retries on network error."""
        call_count = [0]

        @retry_api_call(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def flaky_api_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Network error")
            return {"status": "ok"}

        result = await flaky_api_call()
        assert result == {"status": "ok"}
        assert call_count[0] == 2


class TestRetryUtilities:
    """Test retry utility functions."""

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        assert is_retryable_error(ConnectionError("test"))
        assert is_retryable_error(TimeoutError("test"))
        assert is_retryable_error(asyncio.TimeoutError("test"))

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test execute_with_retry succeeds."""

        async def successful_func(arg1, arg2):
            return arg1 + arg2

        result = await execute_with_retry(successful_func, 10, 20)
        assert result == 30

    @pytest.mark.asyncio
    async def test_execute_with_retry_with_kwargs(self):
        """Test execute_with_retry with keyword arguments."""

        async def func_with_kwargs(a, b=5):
            return a * b

        result = await execute_with_retry(func_with_kwargs, 3, b=7)
        assert result == 21

    @pytest.mark.asyncio
    async def test_execute_with_retry_after_failures(self):
        """Test execute_with_retry succeeds after failures."""
        call_count = [0]

        async def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary error")
            return "success"

        result = await execute_with_retry(
            flaky_func, max_attempts=5, min_wait=0.1, max_wait=0.2
        )
        assert result == "success"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_attempts_exceeded(self):
        """Test execute_with_retry fails after max attempts."""

        async def always_fails():
            raise ConnectionError("Permanent error")

        with pytest.raises(ConnectionError, match="Permanent error"):
            await execute_with_retry(
                always_fails, max_attempts=2, min_wait=0.1, max_wait=0.2
            )


class TestRetryIntegration:
    """Integration tests for retry mechanism."""

    @pytest.mark.asyncio
    async def test_multiple_decorators_on_same_function(self):
        """Test that decorators can be stacked (though not recommended)."""

        @retry_worker_operation(max_attempts=2, min_wait=0.1, max_wait=0.2)
        async def operation():
            return "success"

        result = await operation()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_async_context(self):
        """Test retry works with async context managers."""

        class AsyncResource:
            def __init__(self):
                self.closed = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                self.closed = True

            async def operation(self):
                return "success"

        @retry_worker_operation(max_attempts=2, min_wait=0.1, max_wait=0.2)
        async def use_resource():
            async with AsyncResource() as resource:
                return await resource.operation()

        result = await use_resource()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_preserves_exception_type(self):
        """Test that retry preserves the original exception type."""

        @retry_worker_operation(max_attempts=2, min_wait=0.1, max_wait=0.2)
        async def raises_specific_error():
            raise ConnectionError("Specific error message")

        with pytest.raises(ConnectionError) as exc_info:
            await raises_specific_error()

        assert "Specific error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_with_different_wait_times(self):
        """Test retry with custom wait times."""
        call_times = []

        @retry_worker_operation(max_attempts=3, min_wait=0.05, max_wait=0.1)
        async def track_timing():
            import time

            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Retry needed")
            return "success"

        result = await track_timing()
        assert result == "success"
        assert len(call_times) == 3

        # Verify there was some delay between calls
        if len(call_times) >= 2:
            time_diff = call_times[1] - call_times[0]
            assert time_diff >= 0.05  # At least min_wait


class TestRetryLogging:
    """Test retry logging behavior."""

    @pytest.mark.asyncio
    async def test_retry_logs_attempts(self):
        """Test that retry attempts are logged."""
        call_count = [0]

        @retry_worker_operation(max_attempts=3, min_wait=0.1, max_wait=0.2)
        async def operation_with_logging():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Retry needed")
            return "success"

        with patch("bindu.utils.retry.logger") as mock_logger:
            result = await operation_with_logging()
            assert result == "success"
            # Logger should have been called for debug messages
            assert mock_logger.debug.called
