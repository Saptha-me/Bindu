"""Tests for schema models."""

import pytest
from pydantic import ValidationError

from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    MessageRole, 
    DeploymentConfig,
    DeploymentMode,
    RouterRegistration,
    DockerConfig,
    Image,
    Video,
    Audio
)


class TestSchemaModels:
    """Tests for Pebble schema models."""
    
    def test_action_request(self):
        """Test ActionRequest model."""
        # Test basic request
        request = ActionRequest(
            content="Test content",
            role=MessageRole.USER
        )
        
        assert request.content == "Test content"
        assert request.role == MessageRole.USER
        assert request.session_id is not None  # Auto-generated
        assert request.metadata == {}
        assert request.media == []
        
        # Test with all fields
        request = ActionRequest(
            content="Full request",
            role=MessageRole.SYSTEM,
            session_id="test-session",
            metadata={"key": "value"},
            media=[Image(url="https://example.com/image.jpg")]
        )
        
        assert request.content == "Full request"
        assert request.role == MessageRole.SYSTEM
        assert request.session_id == "test-session"
        assert request.metadata == {"key": "value"}
        assert len(request.media) == 1
        assert isinstance(request.media[0], Image)
    
    def test_action_response(self):
        """Test ActionResponse model."""
        # Test basic response
        response = ActionResponse(
            content="Test response",
            role=MessageRole.ASSISTANT
        )
        
        assert response.content == "Test response"
        assert response.role == MessageRole.ASSISTANT
        assert response.session_id is not None  # Auto-generated
        assert response.metadata == {}
        assert response.media == []
        assert response.finished is True  # Default
        
        # Test with all fields
        response = ActionResponse(
            content="Full response",
            role=MessageRole.TOOL,
            session_id="test-session",
            metadata={"key": "value"},
            media=[Image(url="https://example.com/result.jpg")],
            finished=False
        )
        
        assert response.content == "Full response"
        assert response.role == MessageRole.TOOL
        assert response.session_id == "test-session"
        assert response.metadata == {"key": "value"}
        assert len(response.media) == 1
        assert response.finished is False
    
    def test_deployment_config(self):
        """Test DeploymentConfig model."""
        # Test default config
        config = DeploymentConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cors_origins == ["*"]
        assert config.enable_docs is True
        assert config.require_auth is True
        assert config.mode == DeploymentMode.LOCAL
        assert config.log_level == "INFO"
        assert config.router_config is None
        assert config.docker_config is None
        
        # Test router configuration
        router_config = RouterRegistration(
            router_url="https://router.example.com",
            api_key="test-key"
        )
        
        config = DeploymentConfig(
            mode=DeploymentMode.REGISTER,
            router_config=router_config
        )
        
        assert config.mode == DeploymentMode.REGISTER
        assert config.router_config == router_config
        
        # Test docker configuration
        docker_config = DockerConfig(
            base_image="python:3.10-slim",
            output_dir="./docker"
        )
        
        config = DeploymentConfig(
            mode=DeploymentMode.DOCKER,
            docker_config=docker_config
        )
        
        assert config.mode == DeploymentMode.DOCKER
        assert config.docker_config == docker_config
        
        # Test validation - router config required for REGISTER mode
        with pytest.raises(ValidationError):
            DeploymentConfig(mode=DeploymentMode.REGISTER)
        
        # Test validation - docker config required for DOCKER mode
        with pytest.raises(ValidationError):
            DeploymentConfig(mode=DeploymentMode.DOCKER)
    
    def test_media_models(self):
        """Test media models (Image, Video, Audio)."""
        # Test Image with URL
        image = Image(url="https://example.com/image.jpg")
        assert image.url == "https://example.com/image.jpg"
        assert image.content is None
        
        # Test Image with content
        image = Image(content=b"image_data")
        assert image.content == b"image_data"
        assert image.url is None
        
        # Test Image with both URL and content
        image = Image(url="https://example.com/image.jpg", content=b"image_data")
        assert image.url == "https://example.com/image.jpg"
        assert image.content == b"image_data"
        
        # Test Video
        video = Video(url="https://example.com/video.mp4")
        assert video.url == "https://example.com/video.mp4"
        
        # Test Audio
        audio = Audio(url="https://example.com/audio.mp3")
        assert audio.url == "https://example.com/audio.mp3"
        
        # Test validation - either URL or content is required
        with pytest.raises(ValidationError):
            Image()