"""
Shared pytest fixtures for testing the pebbling package.
"""
import json
import uuid
from unittest.mock import MagicMock, patch
import pytest

from pebbling.core.protocol import pebblingProtocol
from pebbling.server.schemas.model import (
    AgentRequest, AgentResponse, HealthResponse, ErrorResponse,
    JsonRpcRequest, JsonRpcResponse, JsonRpcError
)


@pytest.fixture
def mock_agent():
    """Mock Agno agent with necessary methods."""
    agent = MagicMock()
    agent.get_status.return_value = "healthy"
    
    # Mock response object with to_dict method
    response = MagicMock()
    response.to_dict.return_value = {
        "content": "Test response",
        "messages": [{"role": "assistant", "content": "Test response"}],
        "metrics": {"tokens": 10}
    }
    agent.run.return_value = response
    
    return agent


@pytest.fixture
def mock_protocol_handler(mock_agent):
    """Mock protocol handler with necessary methods."""
    handler = MagicMock()
    handler.agent = mock_agent
    
    # Mock Context handler method
    async def handle_Context(params):
        return {"status": "success", "message": "Context handled successfully"}
    
    handler.handle_Context = handle_Context
    return handler


@pytest.fixture
def protocol():
    """Create a pebblingProtocol instance."""
    return pebblingProtocol()


@pytest.fixture
def sample_request_json():
    """Sample request JSON for testing."""
    return {
        "input": "Test input"
    }


@pytest.fixture
def sample_jsonrpc_request():
    """Sample JSON-RPC request for testing."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "Context",
        "params": {
            "operation": "add",
            "key": "test_key",
            "value": "test_value"
        }
    }