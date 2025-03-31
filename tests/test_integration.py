"""Integration tests for the Pebble package."""

import pytest
import time
from fastapi.testclient import TestClient
import httpx
import json

from pebble import pebblify
from pebble.schemas.models import (
    DeploymentConfig, 
    DeploymentMode,
    ActionRequest,
    MessageRole
)
from pebble.registry import AgentRegistry


class TestIntegration:
    """Integration tests for the Pebble package."""
    
    def test_local_deployment(self, mock_agent):
        """Test local deployment with FastAPI."""
        # Create deployment config
        config = DeploymentConfig(
            host="localhost",
            port=8000,
            mode=DeploymentMode.LOCAL,
            require_auth=False  # Disable auth for testing
        )
        
        # Deploy agent
        app = pebblify(
            agent=mock_agent,
            name="TestAgent",
            config=config,
            autostart=False  # Don't start the server
        )
        
        # Create test client
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Test act endpoint
        act_request = {
            "content": "Hello",
            "role": "user"
        }
        
        response = client.post("/act", json=act_request)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["role"] == "assistant"
    
    def test_multi_agent_registry(self, mock_adapter):
        """Test multi-agent registry."""
        # Create registry
        registry = AgentRegistry()
        
        # Create mock adapters
        adapter1 = mock_adapter
        adapter2 = mock_adapter.__class__()
        
        # Register responses
        adapter1.register_response("Hello", "Hi from agent 1!")
        adapter2.register_response("Tell me more", "I'm agent 2, ready to help.")
        
        # Register agents
        registry.register("agent1", adapter1, roles=["greeting"])
        registry.register("agent2", adapter2, roles=["information"])
        
        # Send message from agent1 to agent2
        response = registry.send_message(
            from_agent="agent1",
            to_agent="agent2",
            message="Tell me more"
        )
        
        # Verify response
        assert response.content == "I'm agent 2, ready to help."
        
        # Verify relationship was updated
        assert registry.relationships["agent1"]["agent2"]["interaction_count"] == 1
        
        # Test handoff
        result = registry.handoff(
            from_agent="agent1",
            to_agent="agent2",
            context={"key": "value"}
        )
        
        assert result is True