"""
Tests for the pebble schema models.
"""
import pytest
from pydantic import ValidationError

from pebble.server.schemas.model import (
    HealthResponse, ErrorResponse, AgentRequest, AgentResponse,
    JsonRpcRequest, JsonRpcResponse, JsonRpcError, JsonRpcErrorDetail
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
            status_code=200,
            content="Test content",
            messages=[{"role": "assistant", "content": "Test content"}],
            metrics={"tokens": 10}
        )
        assert response.status_code == 200
        assert response.status == "success"
        assert response.content == "Test content"
    
    def test_invalid_status_code(self):
        """Test that any status code is accepted (validation to be done in the server)."""
        # Model doesn't validate status codes, this would be handled at the server level
        response = AgentResponse(
            status_code=999,  # Invalid status code
            content="Test content"
        )
        assert response.status_code == 999
    
    def test_default_values(self):
        """Test the default values in the response."""
        response = AgentResponse(
            status_code=200,
            content="Test content"
        )
        assert response.status == "success"
        assert response.messages == []
        assert response.metrics == {}
    
    def test_custom_values(self):
        """Test setting custom values."""
        response = AgentResponse(
            status_code=201,
            status="created",
            content="Created content",
            messages=[{"role": "user", "content": "Hello"}],
            metrics={"response_time": 0.5}
        )
        assert response.status_code == 201
        assert response.status == "created"
        assert response.content == "Created content"
        assert response.messages == [{"role": "user", "content": "Hello"}]
        assert response.metrics == {"response_time": 0.5}


class TestJsonRpcModels:
    """Tests for the JSON-RPC models."""
    
    def test_jsonrpc_request(self):
        """Test that a valid JSON-RPC request is accepted."""
        request = JsonRpcRequest(
            id="test-id",
            method="Run",
            params={"input": "Test input"}
        )
        assert request.jsonrpc == "2.0"
        assert request.id == "test-id"
        assert request.method == "Run"
        assert request.params == {"input": "Test input"}
    
    def test_jsonrpc_error(self):
        """Test that a valid JSON-RPC error is accepted."""
        error_detail = JsonRpcErrorDetail(
            code=-32600,
            message="Invalid Request"
        )
        error = JsonRpcError(
            id="test-id",
            error=error_detail
        )
        assert error.jsonrpc == "2.0"
        assert error.id == "test-id"
        assert error.error.code == -32600
        assert error.error.message == "Invalid Request"