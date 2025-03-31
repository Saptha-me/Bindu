"""Tests for the logging middleware."""

import pytest
import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from pebble.logging.middleware import RequestLoggingMiddleware


class TestLoggingMiddleware:
    """Tests for the RequestLoggingMiddleware."""
    
    def test_middleware_init(self):
        """Test middleware initialization."""
        logger = MagicMock()
        middleware = RequestLoggingMiddleware(logger=logger)
        
        assert middleware.logger == logger
        assert middleware.log_level == "INFO"
        
        # Test with custom log level
        middleware = RequestLoggingMiddleware(logger=logger, log_level="DEBUG")
        assert middleware.log_level == "DEBUG"
    
    @pytest.mark.asyncio
    async def test_middleware_dispatch(self):
        """Test middleware dispatch method."""
        # Setup
        logger = MagicMock()
        middleware = RequestLoggingMiddleware(logger=logger)
        
        # Create a mock request
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/test"
        request.headers = {"content-type": "application/json"}
        request.client.host = "127.0.0.1"
        
        # Create a mock call_next function
        async def call_next(request):
            return Response(content="Test response", status_code=200)
        
        # Mock _log_request and _log_response
        middleware._log_request = MagicMock()
        middleware._log_response = MagicMock()
        
        # Call dispatch
        response = await middleware.dispatch(request, call_next)
        
        # Verify
        assert response.status_code == 200
        middleware._log_request.assert_called_once()
        middleware._log_response.assert_called_once()
    
    def test_log_request(self):
        """Test _log_request method."""
        logger = MagicMock()
        middleware = RequestLoggingMiddleware(logger=logger)
        
        # Create a mock request
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/endpoint"
        request.headers = {"content-type": "application/json", "authorization": "Bearer token"}
        request.client.host = "127.0.0.1"
        
        # Call _log_request
        middleware._log_request(request, "request-123")
        
        # Verify logger was called
        logger.log.assert_called_once()
        args, kwargs = logger.log.call_args
        assert args[0] == "INFO"  # Log level
        
        # Parse the JSON log entry
        log_entry = json.loads(args[1])
        assert log_entry["request_id"] == "request-123"
        assert log_entry["type"] == "request"
        assert log_entry["method"] == "POST"
        assert log_entry["path"] == "/api/endpoint"
        assert "authorization" in log_entry["headers"]
        assert log_entry["headers"]["authorization"] == "[REDACTED]"  # Should mask auth header