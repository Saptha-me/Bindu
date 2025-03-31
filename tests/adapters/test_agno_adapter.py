"""Tests for the Agno adapter."""

import pytest
from unittest.mock import MagicMock, patch

from pebble.adapters.agno_adapter import AgnoAdapter
from pebble.schemas.models import ActionRequest, MessageRole, Image, Video


class TestAgnoAdapter:
    """Tests for the AgnoAdapter class."""
    
    def test_init(self, mock_agent):
        """Test adapter initialization."""
        adapter = AgnoAdapter(agent=mock_agent)
        assert adapter.agent == mock_agent
        assert adapter.name == "AgnoAdapter"
        
        # Test with custom values
        adapter = AgnoAdapter(
            agent=mock_agent,
            name="CustomAgnoAdapter",
            metadata={"key": "value"}
        )
        assert adapter.name == "CustomAgnoAdapter"
        assert adapter.metadata == {"key": "value"}
    
    def test_act_simple(self, mock_agent):
        """Test simple act method with text only."""
        adapter = AgnoAdapter(agent=mock_agent)
        request = ActionRequest(content="Hello", role=MessageRole.USER)
        
        # Register a response
        mock_agent.responses = {"Hello": "Hi there!"}
        
        response = adapter.act(request)
        assert response.content == "Hi there!"
        assert response.role == MessageRole.ASSISTANT
        assert response.finished is True
    
    def test_act_with_image(self, mock_vision_agent, mock_httpx_client):
        """Test act method with image processing."""
        adapter = AgnoAdapter(agent=mock_vision_agent)
        
        # Register a response for image processing
        mock_vision_agent.responses = {"Describe this image": "This is a beautiful landscape."}
        
        # Create test request with image URL
        url = "https://example.com/test_image.jpg"
        test_content = b"TEST_IMAGE_DATA"
        mock_httpx_client.register_response(url, test_content)
        
        request = ActionRequest(
            content="Describe this image",
            role=MessageRole.USER,
            media=[Image(url=url)]
        )
        
        response = adapter.act(request)
        assert response.content == "This is a beautiful landscape."
        
        # Verify the agent was called with the downloaded image
        assert len(mock_vision_agent.last_inputs) > 0
        assert mock_vision_agent.last_inputs[-1]["prompt"] == "Describe this image"
        assert mock_vision_agent.last_inputs[-1]["images"] is not None
    
    def test_act_with_direct_image_content(self, mock_vision_agent):
        """Test act method with direct image content."""
        adapter = AgnoAdapter(agent=mock_vision_agent)
        
        # Register a response
        mock_vision_agent.responses = {"Analyze this image": "It's a test pattern."}
        
        # Create test request with direct image content
        direct_content = b"DIRECT_IMAGE_CONTENT"
        request = ActionRequest(
            content="Analyze this image",
            role=MessageRole.USER,
            media=[Image(content=direct_content)]
        )
        
        response = adapter.act(request)
        assert response.content == "It's a test pattern."
        
        # Verify the agent was called with the image content
        assert len(mock_vision_agent.last_inputs) > 0
        assert mock_vision_agent.last_inputs[-1]["images"] is not None