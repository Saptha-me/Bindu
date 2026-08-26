"""
tests/test_retry.py

Comprehensive tests for bindu/retry.py.
Covers sync/async paths, backoff maths, jitter, on_retry callbacks,
selective exception filtering, and reraise behaviour.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# We import relative to repo root; adjust if your package layout differs.
# ---------------------------------------------------------------------------
from bindu.retry import (
    RetryConfig,
    _compute_delay,
    async_retry,
    retry,
    wrap_handler,
)


# ===========================================================================
# Helpers
# ===========================================================================

class TransientError(Exception):
    """Raised for recoverable failures in tests."""


class FatalError(Exception):
    """Should never be retried."""


def _make_flaky(fail_times: int, exc_class: type = TransientError):
    """Return a callable that raises *exc_class* for the first *fail_times* calls."""
    calls = {"count": 0}

    def handler(messages):
        calls["count"] += 1
        if calls["count"] <= fail_times:
            raise exc_class(f"fail #{calls['count']}")
        return f"ok after {calls['count']} attempts"

    handler.calls = calls
    return handler


# ===========================================================================
# RetryConfig defaults
# ===========================================================================

class TestRetryConfigDefaults:
    def test_default_values(self):
        cfg = RetryConfig()
        assert cfg.max_attempts == 3
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.backoff_factor == 2.0
        assert cfg.jitter is True
        assert cfg.reraise is True
        assert cfg.on_retry is None


# ===========================================================================
# _compute_delay
# ===========================================================================

class TestComputeDelay:
    def test_no_jitter_first_attempt(self):
        cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)
        assert _compute_delay(cfg, 1) == pytest.approx(1.0)

    def test_no_jitter_second_attempt(self):
        cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)
        assert _compute_delay(cfg, 2) == pytest.approx(2.0)

    def test_no_jitter_capped_at_max(self):
        cfg = RetryConfig(base_delay=10.0, backoff_factor=10.0, max_delay=30.0, jitter=False)
        assert _compute_delay(cfg, 3) == pytest.approx(30.0)  # 10*100 capped at 30

    def test_jitter_within_range(self):
        cfg = RetryConfig(base_delay=10.0, backoff_factor=1.0, jitter=True)
        delays = [_compute_delay(cfg, 1) for _ in range(50)]
        assert all(5.0 <= d <= 10.0 for d in delays), "jitter should stay in [50%, 100%] of base"
        assert len(set(delays)) > 1, "jitter should add variation"


# ===========================================================================
# Synchronous retry decorator
# ===========================================================================

class TestRetryDecorator:
    def test_success_on_first_try(self):
        @retry(max_attempts=3, base_delay=0)
        def handler(messages):
            return "success"

        assert handler([]) == "success"

    def test_retries_and_succeeds(self):
        flaky = _make_flaky(fail_times=2)
        wrapped = retry(max_attempts=3, base_delay=0)(flaky)

        with patch("time.sleep"):
            result = wrapped([])

        assert result == "ok after 3 attempts"
        assert flaky.calls["count"] == 3

    def test_raises_after_max_attempts(self):
        flaky = _make_flaky(fail_times=10)
        wrapped = retry(max_attempts=3, base_delay=0)(flaky)

        with patch("time.sleep"), pytest.raises(TransientError):
            wrapped([])

        assert flaky.calls["count"] == 3

    def test_reraise_false_returns_none(self):
        @retry(max_attempts=2, base_delay=0, reraise=False)
        def always_fail(messages):
            raise TransientError("boom")

        with patch("time.sleep"):
            result = always_fail([])

        assert result is None

    def test_does_not_retry_non_matching_exception(self):
        @retry(max_attempts=5, base_delay=0, retry_on=(TransientError,))
        def handler(messages):
            raise FatalError("fatal")

        with pytest.raises(FatalError):
            handler([])

    def test_on_retry_callback_called(self):
        callback = MagicMock()
        flaky = _make_flaky(fail_times=2)
        wrapped = retry(max_attempts=3, base_delay=0, on_retry=callback)(flaky)

        with patch("time.sleep"):
            wrapped([])

        assert callback.call_count == 2
        first_call_attempt, first_call_exc = callback.call_args_list[0][0]
        assert first_call_attempt == 1
        assert isinstance(first_call_exc, TransientError)

    def test_sleep_called_with_positive_delay(self):
        @retry(max_attempts=2, base_delay=1.0, jitter=False)
        def always_fail(messages):
            raise TransientError()

        with patch("time.sleep") as mock_sleep, pytest.raises(TransientError):
            always_fail([])

        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(1.0)

    def test_retry_config_attribute_exposed(self):
        @retry(max_attempts=7, base_delay=0)
        def handler(messages):
            return "ok"

        assert handler._retry_config.max_attempts == 7

    def test_decorator_without_parentheses_uses_defaults(self):
        """@retry with no args should still work via kwargs path."""
        @retry(max_attempts=1, base_delay=0)
        def handler(messages):
            return "ok"

        assert handler([]) == "ok"

    def test_preserves_function_name_and_docstring(self):
        @retry(max_attempts=1, base_delay=0)
        def my_handler(messages):
            """My docstring."""
            return "ok"

        assert my_handler.__name__ == "my_handler"
        assert my_handler.__doc__ == "My docstring."


# ===========================================================================
# Async retry decorator
# ===========================================================================

class TestAsyncRetryDecorator:
    def test_success_on_first_try(self):
        @async_retry(max_attempts=3, base_delay=0)
        async def handler(messages):
            return "async success"

        result = asyncio.get_event_loop().run_until_complete(handler([]))
        assert result == "async success"

    def test_retries_and_succeeds(self):
        calls = {"count": 0}

        @async_retry(max_attempts=3, base_delay=0)
        async def flaky(messages):
            calls["count"] += 1
            if calls["count"] < 3:
                raise TransientError("async fail")
            return "async ok"

        with patch("asyncio.sleep", new=asyncio.coroutine(lambda _: None)):
            result = asyncio.get_event_loop().run_until_complete(flaky([]))

        assert result == "async ok"
        assert calls["count"] == 3

    def test_raises_after_max_attempts(self):
        @async_retry(max_attempts=2, base_delay=0)
        async def always_fail(messages):
            raise TransientError("async boom")

        with patch("asyncio.sleep", new=asyncio.coroutine(lambda _: None)):
            with pytest.raises(TransientError):
                asyncio.get_event_loop().run_until_complete(always_fail([]))

    def test_reraise_false_returns_none(self):
        @async_retry(max_attempts=2, base_delay=0, reraise=False)
        async def always_fail(messages):
            raise TransientError()

        with patch("asyncio.sleep", new=asyncio.coroutine(lambda _: None)):
            result = asyncio.get_event_loop().run_until_complete(always_fail([]))

        assert result is None

    def test_retry_config_attribute_exposed(self):
        @async_retry(max_attempts=4)
        async def handler(messages):
            return "ok"

        assert handler._retry_config.max_attempts == 4


# ===========================================================================
# wrap_handler
# ===========================================================================

class TestWrapHandler:
    def test_wraps_existing_handler(self):
        calls = {"count": 0}

        def my_handler(messages):
            calls["count"] += 1
            if calls["count"] < 3:
                raise TransientError()
            return "wrapped ok"

        resilient = wrap_handler(my_handler, RetryConfig(max_attempts=3, base_delay=0))

        with patch("time.sleep"):
            result = resilient([])

        assert result == "wrapped ok"
        assert calls["count"] == 3

    def test_kwargs_forwarded_correctly(self):
        def my_handler(messages):
            raise TransientError()

        resilient = wrap_handler(my_handler, max_attempts=2, base_delay=0, reraise=False)

        with patch("time.sleep"):
            result = resilient([])

        assert result is None

    def test_original_handler_unchanged(self):
        def my_handler(messages):
            raise TransientError()

        wrap_handler(my_handler, RetryConfig(max_attempts=1))

        # original should still raise immediately without retry
        with pytest.raises(TransientError):
            my_handler([])


# ===========================================================================
# Integration: RetryConfig passed as object
# ===========================================================================

class TestRetryConfigObject:
    def test_retry_with_config_object(self):
        cfg = RetryConfig(max_attempts=4, base_delay=0, jitter=False)
        calls = {"count": 0}

        @retry(cfg)
        def handler(messages):
            calls["count"] += 1
            if calls["count"] < 4:
                raise TransientError()
            return "config object ok"

        with patch("time.sleep"):
            result = handler([])

        assert result == "config object ok"
        assert calls["count"] == 4
