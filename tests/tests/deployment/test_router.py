"""Tests for the router deployment module."""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from pebble.deployment.router import register_with_router
from pebble.schemas.models import DeploymentConfig, RouterRegistration


class TestRouterDeployment:
    """Tests for the router deployment module."""
    
    def test_register_with_router(self):
        """Test registering with a router service."""
        with patch("pebble.deployment.router.httpx.post") as mock_post:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "agent_id": "test-agent",
                "url": "https://router.example.com/agents/test-agent"
            }
            mock_post.return_value = mock_response
            
            # Create test app and adapters
            app = FastAPI()
            adapters = [MagicMock(), MagicMock()]
            
            # Setup adapter capabilities
            adapters[0].capabilities = ["act", "see"]
            adapters[0].name = "VisionAgent"
            adapters[1].capabilities = ["act", "listen"]
            adapters[1].name = "AudioAgent"
            
            # Create deployment config
            config = DeploymentConfig(
                host="localhost",
                port=8000,
                router_config=RouterRegistration(
                    router_url="https://router.example.com",
                    api_key="test-key",
                    description="Test agent",
                    tags=["test"]
                )
            )
            
            # Register with router
            result = register_with_router(app, adapters, config)
            
            # Verify result
            assert result == "https://router.example.com/agents/test-agent"
            
            # Verify request
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://router.example.com/register"
            assert "json" in kwargs
            assert kwargs["json"]["capabilities"] == ["act", "see", "listen"]
            assert "headers" in kwargs
            assert kwargs["headers"]["Authorization"] == "Bearer test-key"