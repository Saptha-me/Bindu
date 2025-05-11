"""
Tests for the Agno adapter.
"""
import pytest
from unittest.mock import MagicMock, patch

from agno.agent import Agent as AgnoAgent
from pebbling.agent.agno_adapter import AgnoProtocolHandler


class TestAgnoAdapter:
    """Tests for the AgnoProtocolHandler."""
    
    @pytest.fixture
    def agno_agent(self):
        """Create a mock Agno agent."""
        agent = MagicMock(spec=AgnoAgent)
        agent.context = {}
        return agent
    
    @pytest.fixture
    def protocol_handler(self, agno_agent):
        """Create an AgnoProtocolHandler with a mock agent."""
        return AgnoProtocolHandler(agent=agno_agent, agent_id="test-agent")
    
    @pytest.mark.asyncio
    async def test_handle_context_add(self, protocol_handler):
        """Test adding context."""
        params = {
            "operation": "add",
            "key": "test_key",
            "value": "test_value",
            "id": "test-id"
        }
        
        result = await protocol_handler.handle_Context(params)
        
        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context added successfully"
        assert protocol_handler.agent.context["test_key"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_handle_context_missing_key(self, protocol_handler):
        """Test adding context with missing key."""
        params = {
            "operation": "add",
            "value": "test_value",
            "id": "test-id"
        }
        
        result = await protocol_handler.handle_Context(params)
        
        assert "error" in result
        assert result["error"]["code"] == 400
    
    @pytest.mark.asyncio
    async def test_handle_context_update(self, protocol_handler):
        """Test updating context."""
        # First add the context with the correct structure (dict with value and metadata)
        protocol_handler.agent.context["test_key"] = {
            "value": "old_value",
            "metadata": {}
        }
        
        params = {
            "operation": "update",
            "key": "test_key",
            "value": "new_value",
            "id": "test-id"
        }
        
        result = await protocol_handler.handle_Context(params)
        
        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context updated successfully"
        
        # After update, the context value is a simple string, not a dictionary
        assert protocol_handler.agent.context["test_key"] == "new_value"
    
    @pytest.mark.asyncio
    async def test_handle_context_delete(self, protocol_handler):
        """Test deleting context."""
        # First add the context with the correct structure
        protocol_handler.agent.context["test_key"] = {
            "value": "test_value",
            "metadata": {}
        }
        
        params = {
            "operation": "delete",
            "key": "test_key",
            "id": "test-id"
        }
        
        result = await protocol_handler.handle_Context(params)
        
        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context deleted successfully"
        assert "test_key" not in protocol_handler.agent.context