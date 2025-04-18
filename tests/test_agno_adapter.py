"""
Tests for the Agno adapter.
"""
import pytest
from unittest.mock import MagicMock, patch

from agno.agent import Agent as AgnoAgent
from pebble.agent.agno_adapter import AgnoProtocolHandler


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
    
    async def test_handle_context_add(self, protocol_handler):
        """Test adding context."""
        params = {
            "operation": "add",
            "key": "test_key",
            "value": "test_value",
            "id": "test-id"
        }
        
        result = await protocol_handler.handle_Context(params)
        
        assert result["status"] == "success"
        assert result["key"] == "test_key"
        assert result["message"] == "Context added successfully"
        assert protocol_handler.agent.context["test_key"] == "test_value"
    
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
    
    async def test_handle_context_update(self, protocol_handler):
        """Test updating context."""
        # First add the context
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
        
        assert result["status"] == "success"
        assert result["key"] == "test_key"
        assert result["message"] == "Context updated successfully"
        assert protocol_handler.agent.context["test_key"]["value"] == "new_value"
    
    async def test_handle_context_delete(self, protocol_handler):
        """Test deleting context."""
        # First add the context
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
        
        assert result["status"] == "success"
        assert result["key"] == "test_key"
        assert result["message"] == "Context deleted successfully"
        assert "test_key" not in protocol_handler.agent.context