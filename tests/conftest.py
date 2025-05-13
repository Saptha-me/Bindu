"""Pytest configuration for test fixtures."""

import uuid
from unittest.mock import MagicMock

import pytest

from pebbling.core.protocol import pebblingProtocol
from pebbling.server.schemas.model import AgentResponse


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
        "metrics": {"tokens": 10},
    }
    agent.run.return_value = response

    return agent


@pytest.fixture
def mock_protocol_handler(mock_agent):
    """Mock protocol handler with necessary methods."""
    handler = MagicMock()
    handler.agent = mock_agent
    handler.agent_id = uuid.uuid4()

    # Create a session ID that will be used consistently
    default_session_id = uuid.uuid4()

    # Mock act method to return properly structured AgentResponse
    def act(message, session_id=None, user_id=None):
        session_id = session_id or default_session_id

        # Return a properly constructed AgentResponse instance
        return AgentResponse(
            agent_id=handler.agent_id,
            session_id=session_id,
            content="Test response",
            role="agent",
            metadata={"messages": [{"role": "assistant", "content": "Test response"}]},
            metrics={"tokens": 10},
        )

    # Explicitly attach the act method
    handler.act = act

    # Mock _ensure_agent_response method if used by the REST server
    def _ensure_agent_response(result, session_id):
        if isinstance(result, AgentResponse):
            return result
        return AgentResponse(
            agent_id=handler.agent_id,
            session_id=session_id,
            content=str(result),
            metrics={},
        )

    handler._ensure_agent_response = _ensure_agent_response

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
        "input": "Tell me about food recommendation - location is beach",
        "user_id": "user-123456",
        "session_id": "45ab8be5-d213-4373-bcf6-c79b61caa086",
    }


@pytest.fixture
def sample_jsonrpc_request():
    """Sample JSON-RPC request for testing."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "Context",
        "params": {"operation": "add", "key": "test_key", "value": "test_value"},
    }
