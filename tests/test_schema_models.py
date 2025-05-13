"""
Tests for the pebbling schema models.
"""

import uuid

from pebbling.server.schemas.model import (
    AgentRequest,
    AgentResponse,
    JsonRpcError,
    JsonRpcErrorDetail,
    JsonRpcRequest,
    MessageRole,
)


class TestAgentRequest:
    """Tests for the AgentRequest model."""

    def test_valid_request(self):
        """Test that a valid request is accepted."""
        request = AgentRequest(input="Test input")
        assert request.input == "Test input"

    def test_empty_input(self):
        """Test that empty input is accepted by the model (validation to be done in the server)."""
        # Models don't validate empty strings, this is handled at the server level
        request = AgentRequest(input="")
        assert request.input == ""

    def test_whitespace_input(self):
        """Test that whitespace-only input is accepted by the model (validation to be done in the server)."""
        # Models don't validate whitespace, this is handled at the server level
        request = AgentRequest(input="   ")
        assert request.input == "   "

    def test_input_not_stripped(self):
        """Test that input is not automatically stripped (stripping to be done in the server)."""
        # Model doesn't strip input, this would be handled at the server level
        request = AgentRequest(input="  Test input  ")
        assert request.input == "  Test input  "

    def test_long_input(self):
        """Test that long input is accepted by the model (length validation to be done in the server)."""
        # Model doesn't limit input length, this would be handled at the server level
        long_input = "x" * 10001
        request = AgentRequest(input=long_input)
        assert request.input == long_input


class TestAgentResponse:
    """Tests for the AgentResponse model."""

    def test_valid_response(self):
        """Test that a valid response is accepted."""
        response = AgentResponse(
            agent_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            content="Test content",
            metadata={"test_key": "test_value"},
        )
        assert response.status == "success"
        assert response.content == "Test content"
        assert response.metadata == {"test_key": "test_value"}

    def test_invalid_status_code(self):
        """Test that custom status values are accepted."""
        response = AgentResponse(
            agent_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            status="error",
            content="Test content",
        )
        assert response.status == "error"

    def test_default_values(self):
        """Test the default values in the response."""
        response = AgentResponse(agent_id=uuid.uuid4(), session_id=uuid.uuid4(), content="Test content")
        assert response.status == "success"
        assert response.role == MessageRole.AGENT
        assert response.metrics == {}

    def test_custom_values(self):
        """Test setting custom values."""
        response = AgentResponse(
            agent_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            status="created",
            content="Created content",
            role=MessageRole.USER,
            metrics={"response_time": 0.5},
        )
        assert response.status == "created"
        assert response.content == "Created content"
        assert response.role == MessageRole.USER
        assert response.metrics == {"response_time": 0.5}


class TestJsonRpcModels:
    """Tests for the JSON-RPC models."""

    def test_jsonrpc_request(self):
        """Test that a valid JSON-RPC request is accepted."""
        request = JsonRpcRequest(id="test-id", method="Run", params={"input": "Test input"})
        assert request.jsonrpc == "2.0"
        assert request.id == "test-id"
        assert request.method == "Run"
        assert request.params == {"input": "Test input"}

    def test_jsonrpc_error(self):
        """Test that a valid JSON-RPC error is accepted."""
        error_detail = JsonRpcErrorDetail(code=-32600, message="Invalid Request")
        error = JsonRpcError(id="test-id", error=error_detail)
        assert error.jsonrpc == "2.0"
        assert error.id == "test-id"
        assert error.error.code == -32600
        assert error.error.message == "Invalid Request"
