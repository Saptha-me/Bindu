"""Tests for the base adapter."""

import uuid
import pytest
from unittest.mock import MagicMock, patch

from pebble.adapters.base import BaseAdapter
from pebble.schemas.models import ActionRequest, MessageRole, Image, Video, Audio


class TestBaseAdapter:
    """Tests for the BaseAdapter class."""
    
    def test_init(self):
        """Test adapter initialization."""
        # Test with default values
        adapter = BaseAdapter()
        assert adapter.agent_id is not None
        assert adapter.name == "BaseAdapter"
        assert adapter.metadata == {}
        
        # Test with custom values
        custom_id = uuid.uuid4()
        adapter = BaseAdapter(
            agent_id=custom_id,
            name="CustomAdapter",
            metadata={"key": "value"}
        )
        assert adapter.agent_id == custom_id
        assert adapter.name == "CustomAdapter"
        assert adapter.metadata == {"key": "value"}
    
    def test_act_not_implemented(self):
        """Test that act raises NotImplementedError."""
        adapter = BaseAdapter()
        request = ActionRequest(content="test", role=MessageRole.USER)
        
        with pytest.raises(NotImplementedError):
            adapter.act(request)
    
    def test_download_media_from_url(self, mock_httpx_client, temp_dir):
        """Test downloading media from URL."""
        adapter = BaseAdapter()
        url = "https://example.com/image.jpg"
        test_content = b"TEST_IMAGE_DATA"
        
        # Register a mock response
        mock_httpx_client.register_response(url, test_content)
        
        # Download media
        content = adapter._download_media_from_url(url)
        assert content == test_content
    
    def test_download_media_from_url_error(self, mock_httpx_client):
        """Test error handling when downloading media."""
        adapter = BaseAdapter()
        url = "https://example.com/not_found.jpg"
        
        # Register a mock error response
        mock_httpx_client.register_response(url, b"Not Found", 404)
        
        # Download should return None for failed requests
        content = adapter._download_media_from_url(url)
        assert content is None
    
    def test_process_media_with_url(self, mock_httpx_client):
        """Test processing media with URL."""
        adapter = BaseAdapter()
        
        # Create a test image with URL
        url = "https://example.com/test_image.jpg"
        test_content = b"TEST_IMAGE_DATA"
        mock_httpx_client.register_response(url, test_content)
        
        image = Image(url=url)
        
        # Process the image
        processed = adapter._process_media(image)
        assert processed == test_content
    
    def test_process_media_with_content(self):
        """Test processing media with direct content."""
        adapter = BaseAdapter()
        
        # Create a test image with direct content
        content = b"DIRECT_CONTENT"
        image = Image(content=content)
        
        # Process the image
        processed = adapter._process_media(image)
        assert processed == content
    
    def test_process_media_both_url_and_content(self, mock_httpx_client):
        """Test processing media with both URL and content (content should take precedence)."""
        adapter = BaseAdapter()
        
        # Create test image with both URL and content
        url = "https://example.com/test_image.jpg"
        url_content = b"URL_CONTENT"
        direct_content = b"DIRECT_CONTENT"
        
        mock_httpx_client.register_response(url, url_content)
        
        image = Image(url=url, content=direct_content)
        
        # Content should take precedence over URL
        processed = adapter._process_media(image)
        assert processed == direct_content