"""Tests for the agent registry."""

import pytest
from unittest.mock import MagicMock, patch
import time

from pebble.registry.agent_registry import AgentRegistry
from pebble.schemas.models import ActionResponse, MessageRole


class TestAgentRegistry:
    """Tests for the AgentRegistry class."""
    
    def test_registry_init(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        
        assert registry.agents == {}
        assert registry.relationships == {}
        assert registry.handoff_history == {}
        assert registry.conversation_context == {}
    
    def test_register_agent(self, mock_adapter):
        """Test registering an agent."""
        registry = AgentRegistry()
        
        # Register an agent
        registry.register("test_agent", mock_adapter, roles=["test"])
        
        # Verify registration
        assert "test_agent" in registry.agents
        assert registry.agents["test_agent"]["adapter"] == mock_adapter
        assert registry.agents["test_agent"]["roles"] == ["test"]
        
        # Verify relationships were initialized
        assert "test_agent" in registry.relationships
        assert registry.relationships["test_agent"] == {}
        
        # Verify handoff history was initialized
        assert "test_agent" in registry.handoff_history
        assert registry.handoff_history["test_agent"] == []
    
    def test_register_multiple_agents(self, mock_adapter):
        """Test registering multiple agents and check relationship updates."""
        registry = AgentRegistry()
        
        # Create a second mock adapter
        mock_adapter2 = MagicMock()
        mock_adapter2.agent_id = "agent-2"
        
        # Register agents with different roles
        registry.register("agent1", mock_adapter, roles=["vision"])
        registry.register("agent2", mock_adapter2, roles=["audio"])
        
        # Verify both agents are registered
        assert "agent1" in registry.agents
        assert "agent2" in registry.agents
        
        # Verify relationships were initialized
        assert "agent1" in registry.relationships
        assert "agent2" in registry.relationships
        
        # Verify relationship between agents
        assert "agent2" in registry.relationships["agent1"]
        assert "agent1" in registry.relationships["agent2"]
        
        # Check relationship properties
        assert registry.relationships["agent1"]["agent2"]["trust_level"] == 0.5
        assert registry.relationships["agent1"]["agent2"]["interaction_count"] == 0
    
    def test_get_agent(self, mock_adapter):
        """Test getting an agent from the registry."""
        registry = AgentRegistry()
        
        # Register an agent
        registry.register("test_agent", mock_adapter)
        
        # Get the agent
        agent = registry.get_agent("test_agent")
        
        # Verify
        assert agent == mock_adapter
        
        # Test getting non-existent agent
        assert registry.get_agent("non_existent") is None
    
    def test_send_message(self, mock_adapter):
        """Test sending a message between agents."""
        registry = AgentRegistry()
        
        # Register sender and receiver
        registry.register("sender", MagicMock())
        registry.register("receiver", mock_adapter)
        
        # Setup mock response
        mock_response = ActionResponse(
            content="Response from receiver",
            role=MessageRole.ASSISTANT,
            finished=True
        )
        mock_adapter.act.return_value = mock_response
        
        # Send message
        response = registry.send_message(
            from_agent="sender",
            to_agent="receiver",
            message="Hello from sender"
        )
        
        # Verify response
        assert response == mock_response
        
        # Verify act was called on receiver
        mock_adapter.act.assert_called_once()
        
        # Verify relationship was updated
        assert registry.relationships["sender"]["receiver"]["interaction_count"] == 1
    
    def test_find_agent_by_capability(self, mock_cognitive_adapter):
        """Test finding an agent by capability."""
        registry = AgentRegistry()
        
        # Register agents with different capabilities
        registry.register("vision_agent", mock_cognitive_adapter, capabilities=["see"])
        registry.register("audio_agent", MagicMock(), capabilities=["listen"])
        
        # Find by capability
        found = registry.find_agent_by_capability("see")
        
        # Verify
        assert found == "vision_agent"
        
        # Test finding non-existent capability
        assert registry.find_agent_by_capability("non_existent") is None
    
    def test_handoff(self, mock_adapter):
        """Test handoff between agents."""
        registry = AgentRegistry()
        
        # Register agents
        registry.register("agent1", MagicMock())
        registry.register("agent2", mock_adapter)
        
        # Perform handoff
        context = {"key": "value", "session": "123"}
        result = registry.handoff(
            from_agent="agent1",
            to_agent="agent2",
            context=context,
            session_id="test-session"
        )
        
        # Verify result
        assert result is True
        
        # Verify handoff was recorded
        assert len(registry.handoff_history["agent1"]) == 1
        assert registry.handoff_history["agent1"][0]["to_agent"] == "agent2"
        assert registry.handoff_history["agent1"][0]["context"] == context
        
        # Verify conversation context was updated
        assert "test-session" in registry.conversation_context
        assert registry.conversation_context["test-session"]["current_agent"] == "agent2"
        assert registry.conversation_context["test-session"]["previous_agent"] == "agent1"
    
    def test_update_relationship(self, mock_adapter):
        """Test updating relationship between agents."""
        registry = AgentRegistry()
        
        # Register agents
        registry.register("agent1", MagicMock())
        registry.register("agent2", mock_adapter)
        
        # Initial trust level should be 0.5
        assert registry.relationships["agent1"]["agent2"]["trust_level"] == 0.5
        
        # Update relationship
        registry.update_relationship(
            from_agent="agent1",
            to_agent="agent2",
            trust_delta=0.1,
            interaction_type="collaboration"
        )
        
        # Verify trust level increased
        assert registry.relationships["agent1"]["agent2"]["trust_level"] == 0.6
        
        # Verify interaction count increased
        assert registry.relationships["agent1"]["agent2"]["interaction_count"] == 1
        
        # Update again with negative trust
        registry.update_relationship(
            from_agent="agent1",
            to_agent="agent2",
            trust_delta=-0.2
        )
        
        # Verify trust level decreased but is clamped to 0.0
        assert registry.relationships["agent1"]["agent2"]["trust_level"] == 0.4