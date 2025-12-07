"""Tests for payment session endpoints.

This module tests the x402 payment session endpoints:
- POST /api/start-payment-session
- GET /payment-capture
- GET /api/payment-status/{session_id}
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.testclient import TestClient

from bindu.server.endpoints.payment_sessions import (
    start_payment_session_endpoint,
    payment_capture_endpoint,
    payment_status_endpoint,
)
from bindu.server.applications import BinduApplication
from bindu.common.models import AgentManifest
from tests.mocks import MockManifest


class MockPaymentSession:
    """Mock payment session for testing."""

    def __init__(self, session_id: str, status: str = "pending"):
        self.session_id = session_id
        self.status = status
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        self.payment_token = None
        self.payment_payload = None

    def is_completed(self) -> bool:
        return self.status == "completed"

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def complete(self, payment_token: str, payment_payload: dict):
        self.payment_token = payment_token
        self.payment_payload = payment_payload
        self.status = "completed"


class MockPaymentSessionManager:
    """Mock payment session manager for testing."""

    def __init__(self):
        self.sessions = {}

    def create_session(self) -> MockPaymentSession:
        session_id = str(uuid4())
        session = MockPaymentSession(session_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> MockPaymentSession | None:
        return self.sessions.get(session_id)


class TestStartPaymentSessionEndpoint:
    """Test start_payment_session_endpoint."""

    @pytest.mark.asyncio
    async def test_start_payment_session_success(self):
        """Test successful payment session creation."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MockPaymentSessionManager()
        app.manifest = MagicMock()
        app.manifest.url = "http://localhost:3773"

        request = MagicMock(spec=Request)

        response = await start_payment_session_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        # Parse response content
        import json
        content = json.loads(response.body.decode())
        assert "session_id" in content
        assert "browser_url" in content
        assert "expires_at" in content
        assert content["status"] == "pending"
        assert "payment-capture" in content["browser_url"]

    @pytest.mark.asyncio
    async def test_start_payment_session_no_manager(self):
        """Test when payment session manager is not enabled."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = None

        request = MagicMock(spec=Request)

        response = await start_payment_session_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        
        import json
        content = json.loads(response.body.decode())
        assert "error" in content
        assert "not enabled" in content["error"]

    @pytest.mark.asyncio
    async def test_start_payment_session_no_manifest(self):
        """Test when manifest is not configured."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MockPaymentSessionManager()
        app.manifest = None

        request = MagicMock(spec=Request)

        response = await start_payment_session_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        
        import json
        content = json.loads(response.body.decode())
        assert "error" in content
        assert "manifest not configured" in content["error"]


class TestPaymentCaptureEndpoint:
    """Test payment_capture_endpoint."""

    @pytest.mark.asyncio
    async def test_payment_capture_no_manager(self):
        """Test when payment session manager is not enabled."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = None

        request = MagicMock(spec=Request)
        request.query_params = {}

        response = await payment_capture_endpoint(app, request)

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_payment_capture_no_session_id(self):
        """Test when session_id is missing."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MockPaymentSessionManager()

        request = MagicMock(spec=Request)
        request.query_params = {}

        response = await payment_capture_endpoint(app, request)

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_payment_capture_session_not_found(self):
        """Test when session does not exist."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MockPaymentSessionManager()

        request = MagicMock(spec=Request)
        request.query_params = {"session_id": "nonexistent"}

        response = await payment_capture_endpoint(app, request)

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_payment_capture_already_completed(self):
        """Test when payment is already completed."""
        app = MagicMock(spec=BinduApplication)
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        session.complete("test_token", {"test": "payload"})
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.query_params = {"session_id": session.session_id}
        request.headers = {}

        response = await payment_capture_endpoint(app, request)

        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_payment_capture_with_payment_token_header(self):
        """Test payment capture with payment token in header."""
        app = MagicMock(spec=BinduApplication)
        app.manifest = MagicMock()
        app.manifest.x402_config = {"facilitator_url": "http://test"}
        
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.query_params = {"session_id": session.session_id}
        request.headers = {"X-PAYMENT": "test_payment_token"}

        with patch('bindu.server.endpoints.payment_sessions.safe_base64_decode') as mock_decode:
            mock_decode.return_value = b'{"test": "payload"}'
            
            with patch('bindu.server.endpoints.payment_sessions.PaymentPayload') as mock_payload:
                mock_payload.model_validate.return_value = MagicMock()
                mock_payload.model_validate.return_value.model_dump.return_value = {"test": "payload"}
                
                response = await payment_capture_endpoint(app, request)

                assert isinstance(response, HTMLResponse)
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_payment_capture_with_payment_token_query(self):
        """Test payment capture with payment token in query params."""
        app = MagicMock(spec=BinduApplication)
        app.manifest = MagicMock()
        app.manifest.x402_config = {"facilitator_url": "http://test"}
        
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.query_params = {
            "session_id": session.session_id,
            "payment": "test_payment_token"
        }
        request.headers = {}

        with patch('bindu.server.endpoints.payment_sessions.safe_base64_decode') as mock_decode:
            mock_decode.return_value = b'{"test": "payload"}'
            
            with patch('bindu.server.endpoints.payment_sessions.PaymentPayload') as mock_payload:
                mock_payload.model_validate.return_value = MagicMock()
                mock_payload.model_validate.return_value.model_dump.return_value = {"test": "payload"}
                
                response = await payment_capture_endpoint(app, request)

                assert isinstance(response, HTMLResponse)
                assert response.status_code == 200


class TestPaymentStatusEndpoint:
    """Test payment_status_endpoint."""

    @pytest.mark.asyncio
    async def test_payment_status_no_manager(self):
        """Test when payment session manager is not enabled."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = None

        request = MagicMock(spec=Request)
        request.path_params = {"session_id": "test"}

        response = await payment_status_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_payment_status_session_not_found(self):
        """Test when session does not exist."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MockPaymentSessionManager()

        request = MagicMock(spec=Request)
        request.path_params = {"session_id": "nonexistent"}

        response = await payment_status_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_payment_status_pending(self):
        """Test status check for pending payment."""
        app = MagicMock(spec=BinduApplication)
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.path_params = {"session_id": session.session_id}

        response = await payment_status_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        import json
        content = json.loads(response.body.decode())
        assert content["status"] == "pending"
        assert "payment_token" not in content

    @pytest.mark.asyncio
    async def test_payment_status_completed(self):
        """Test status check for completed payment."""
        app = MagicMock(spec=BinduApplication)
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        session.complete("test_token", {"test": "payload"})
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.path_params = {"session_id": session.session_id}

        response = await payment_status_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        import json
        content = json.loads(response.body.decode())
        assert content["status"] == "completed"
        assert content["payment_token"] == "test_token"

    @pytest.mark.asyncio
    async def test_payment_status_expired(self):
        """Test status check for expired payment."""
        app = MagicMock(spec=BinduApplication)
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        # Make session expired
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.path_params = {"session_id": session.session_id}

        response = await payment_status_endpoint(app, request)

        assert isinstance(response, JSONResponse)
        # Should still return 200 with expired status
        assert response.status_code == 200


class TestPaymentSessionErrorHandling:
    """Test error handling in payment session endpoints."""

    @pytest.mark.asyncio
    async def test_payment_capture_invalid_payment_token(self):
        """Test payment capture with invalid payment token."""
        app = MagicMock(spec=BinduApplication)
        app.manifest = MagicMock()
        app.manifest.x402_config = {"facilitator_url": "http://test"}
        
        manager = MockPaymentSessionManager()
        session = manager.create_session()
        app._payment_session_manager = manager

        request = MagicMock(spec=Request)
        request.query_params = {"session_id": session.session_id}
        request.headers = {"X-PAYMENT": "invalid_token"}

        with patch('bindu.server.endpoints.payment_sessions.safe_base64_decode') as mock_decode:
            mock_decode.side_effect = Exception("Invalid base64")
            
            response = await payment_capture_endpoint(app, request)

            # Should handle error gracefully
            assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_start_payment_session_with_exception(self):
        """Test start_payment_session with unexpected exception."""
        app = MagicMock(spec=BinduApplication)
        app._payment_session_manager = MagicMock()
        app._payment_session_manager.create_session.side_effect = Exception("Unexpected error")
        app.manifest = MagicMock()
        app.manifest.url = "http://localhost:3773"

        request = MagicMock(spec=Request)

        # The handle_endpoint_errors decorator should catch this
        response = await start_payment_session_endpoint(app, request)
        
        # Should return error response
        assert isinstance(response, JSONResponse)
