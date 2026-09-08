"""Minimal tests for metrics middleware."""

from unittest.mock import AsyncMock, Mock, patch
import pytest

from bindu.server.middleware.metrics import (
    MetricsMiddleware,
    UUID_PATTERN,
    NUMERIC_ID_PATTERN,
)


class TestMetricsMiddleware:
    """Test metrics middleware functionality."""

    def test_uuid_pattern_matches_uuid(self):
        """Test UUID pattern matches valid UUIDs."""
        path = "/tasks/550e8400-e29b-41d4-a716-446655440000/status"
        result = UUID_PATTERN.sub("/:id", path)

        assert result == "/tasks/:id/status"

    def test_numeric_pattern_matches_numbers(self):
        """Test numeric pattern matches numeric IDs."""
        path = "/users/12345/profile"
        result = NUMERIC_ID_PATTERN.sub("/:id", path)

        assert result == "/users/:id/profile"

    @pytest.mark.asyncio
    async def test_dispatch_skips_metrics_endpoint(self):
        """Test that metrics endpoint itself is skipped."""
        mock_request = Mock()
        mock_request.url.path = "/metrics"

        mock_call_next = AsyncMock(return_value=Mock())

        middleware = MetricsMiddleware(app=Mock())

        with patch("bindu.server.middleware.metrics.get_metrics"):
            await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_records_metrics(self):
        """Test that metrics are recorded for normal requests."""
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"
        mock_request.headers = {"content-length": "100"}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "500"}

        mock_call_next = AsyncMock(return_value=mock_response)

        mock_metrics = Mock()
        mock_metrics.increment_requests_in_flight = Mock()
        mock_metrics.decrement_requests_in_flight = Mock()
        mock_metrics.record_http_request = Mock()

        middleware = MetricsMiddleware(app=Mock())

        with patch(
            "bindu.server.middleware.metrics.get_metrics", return_value=mock_metrics
        ):
            result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        mock_metrics.increment_requests_in_flight.assert_called_once()
        mock_metrics.decrement_requests_in_flight.assert_called_once()
        mock_metrics.record_http_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_decrements_on_error(self):
        """Test that requests in flight is decremented even on error."""
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.headers = {}

        mock_call_next = AsyncMock(side_effect=Exception("Test error"))

        mock_metrics = Mock()
        mock_metrics.increment_requests_in_flight = Mock()
        mock_metrics.decrement_requests_in_flight = Mock()

        middleware = MetricsMiddleware(app=Mock())

        with patch(
            "bindu.server.middleware.metrics.get_metrics", return_value=mock_metrics
        ):
            with pytest.raises(Exception, match="Test error"):
                await middleware.dispatch(mock_request, mock_call_next)

        mock_metrics.increment_requests_in_flight.assert_called_once()
        mock_metrics.decrement_requests_in_flight.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_ignores_recording_error(self):
        """Test that errors during metric recording don't crash request."""
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.headers = {}

        mock_response = Mock()
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)

        mock_metrics = Mock()
        mock_metrics.increment_requests_in_flight = Mock()
        mock_metrics.decrement_requests_in_flight = Mock()
        # Simulate error in recording
        mock_metrics.record_http_request = Mock(side_effect=Exception("Metrics DB down"))

        middleware = MetricsMiddleware(app=Mock())

        with patch(
            "bindu.server.middleware.metrics.get_metrics", return_value=mock_metrics
        ):
            # Should not raise exception
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert response == mock_response
        mock_metrics.increment_requests_in_flight.assert_called_once()
        mock_metrics.record_http_request.assert_called_once()
        mock_metrics.decrement_requests_in_flight.assert_called_once()  # cleanup always runs

