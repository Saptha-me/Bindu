"""Unit tests for A2A protocol endpoint."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import (
    InternalError,
    JSONParseError,
    MethodNotFoundError,
)
from bindu.server.applications import BinduApplication
from bindu.server.endpoints.a2a_protocol import agent_run_endpoint


@pytest.fixture
def mock_app():
    """Create a mock BinduApplication."""
    app = MagicMock(spec=BinduApplication)
    app.task_manager = MagicMock()
    # Mock the handler to echo the request's JSON-RPC id back, so success-path
    # tests can assert correlation-id round-tripping instead of a hardcoded value.
    app.task_manager.mock_handler = AsyncMock(
        side_effect=lambda request, **_: {
            "jsonrpc": "2.0",
            "result": "success",
            "id": request["id"],
        }
    )
    return app


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    with patch("bindu.server.endpoints.a2a_protocol.app_settings") as mock:
        mock.agent.method_handlers = {
            "tasks/list": "mock_handler",
            "message/send": "mock_handler",
        }
        mock.auth.enabled = False
        mock.auth.require_permissions = False
        yield mock


@pytest.mark.asyncio
async def test_valid_request(mock_app, mock_settings):
    """Test successful processing of a valid A2A request."""
    # Setup request with valid JSON body
    body = {
        "jsonrpc": "2.0",
        "method": "tasks/list",
        "params": {},
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
    
    class MockState:
        pass
    mock_request.state = MockState()

    with patch("bindu.server.endpoints.a2a_protocol.get_client_ip", return_value="127.0.0.1"):
        # Call endpoint
        response = await agent_run_endpoint(mock_app, mock_request)

    # Verify task manager handler was called
    mock_app.task_manager.mock_handler.assert_called_once()
    
    # Verify response
    assert isinstance(response, Response)
    assert response.status_code == 200
    content = json.loads(response.body)
    assert content["jsonrpc"] == "2.0"
    assert content["result"] == "success"
    assert content["id"] == body["id"]


@pytest.mark.asyncio
async def test_invalid_json(mock_app):
    """Test handling of invalid JSON body."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b"invalid json")

    with patch("bindu.server.endpoints.a2a_protocol.get_client_ip", return_value="127.0.0.1"):
        response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 400
    content = json.loads(response.body)
    assert "error" in content
    assert content["error"]["code"] == -32700
    assert "message" in content["error"]


@pytest.mark.asyncio
async def test_unsupported_method_schema_validation_error(mock_app, mock_settings):
    """Test that an unrecognized method tag causes discriminated union validation to fail, returning 400."""
    body = {
        "jsonrpc": "2.0",
        "method": "unknown/method",
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())

    with patch("bindu.server.endpoints.a2a_protocol.get_client_ip", return_value="127.0.0.1"):
        response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 400
    content = json.loads(response.body)
    assert "error" in content
    assert content["error"]["code"] == -32700
    assert "message" in content["error"]


@pytest.mark.asyncio
async def test_method_not_found_error(mock_app, mock_settings):
    """Test that a valid method literal that has no handler triggers MethodNotFoundError and returns 404."""
    # "tasks/get" is a valid union discriminator method, but it is not present in mock_settings handler list
    body = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {"taskId": str(uuid.uuid4())},
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
    
    class MockState:
        pass
    mock_request.state = MockState()

    with patch("bindu.server.endpoints.a2a_protocol.get_client_ip", return_value="127.0.0.1"):
        response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 404
    content = json.loads(response.body)
    assert "error" in content
    assert content["error"]["code"] == -32601
    assert "message" in content["error"]


@pytest.mark.asyncio
async def test_internal_error(mock_app, mock_settings):
    """Test handling of internal errors."""
    body = {
        "jsonrpc": "2.0",
        "method": "tasks/list",
        "params": {},
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
    
    class MockState:
        pass
    mock_request.state = MockState()
    
    # Simulate handler raising exception
    mock_app.task_manager.mock_handler.side_effect = Exception("Crash")

    response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 500
    content = json.loads(response.body)
    assert "error" in content
    assert content["error"]["code"] == -32603  # Internal error


@pytest.mark.asyncio
async def test_payment_context_injection(mock_app):
    """Test injection of payment context into message metadata."""
    # Mock settings specifically for this test to ensure handler is found
    with patch("bindu.server.endpoints.a2a_protocol.app_settings") as mock_settings:
        mock_settings.agent.method_handlers = {"message/send": "mock_handler"}
        mock_settings.auth.enabled = False
        mock_settings.auth.require_permissions = False
        
        body = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "configuration": {
                    "acceptedOutputModes": ["text"]
                },
                "message": {
                    "messageId": "123e4567-e89b-12d3-a456-426614174000",
                    "contextId": "123e4567-e89b-12d3-a456-426614174001",
                    "taskId": "123e4567-e89b-12d3-a456-426614174002",
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "hello"}]
                }
            },
            "id": str(uuid.uuid4()),
        }
        
        mock_request = MagicMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
        
        # Setup payment context in request state
        class MockState:
            payment_payload = {"amount": 100}
            payment_requirements = {"token": "USDC"}
            verify_response = {"status": "verified"}
        mock_request.state = MockState()

        # Call endpoint
        await agent_run_endpoint(mock_app, mock_request)

        # Verify handler called with modified request
        call_args = mock_app.task_manager.mock_handler.call_args[0][0]
        metadata = call_args["params"]["message"]["metadata"]
        
        assert "_payment_context" in metadata
        context = metadata["_payment_context"]
        assert context["payment_payload"] == {"amount": 100}
        assert context["payment_requirements"] == {"token": "USDC"}
        assert context["verify_response"] == {"status": "verified"}
