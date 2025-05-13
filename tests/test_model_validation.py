"""Tests for model validation in pebbling."""

import uuid
import base64
from unittest.mock import patch, MagicMock

import pytest
from pydantic import ValidationError

from pebbling.server.schemas.model import (
    ImageArtifact, VideoArtifact, AudioArtifact,
    ViewRequest, Media, MessageRole, AgentResponse,
    Image, Video, HealthResponse, ErrorResponse
)


class TestViewRequest:
    """Tests for the ViewRequest model."""

    def test_view_request_validation_image(self):
        """Test ViewRequest validation with image media."""
        # Create valid image artifact
        image = ImageArtifact(
            id=uuid.uuid4(),
            url="https://example.com/image.jpg",
            width=800,
            height=600,
            mime_type="image/jpeg"
        )
        
        # Create valid view request
        request = ViewRequest(
            input="Analyze this image",
            media_type="image",
            media=image,
            user_id="test-user",
            session_id=str(uuid.uuid4())
        )
        
        # Verify the validation worked
        assert request.media_type == "image"
        assert isinstance(request.media, ImageArtifact)
        
    def test_direct_model_validator(self):
        """Test model validator directly for ImageArtifact."""
        # Create an artifact with both url and base64
        with pytest.raises(ValueError) as excinfo:
            ImageArtifact(
                id=uuid.uuid4(),
                url="https://example.com/image.jpg",
                base64_image="base64data",
                width=800,
                height=600,
            )
        assert "Provide either `url` or `base64_image`, not both" in str(excinfo.value)
        
        # Create an artifact with neither url nor base64
        with pytest.raises(ValueError) as excinfo:
            ImageArtifact(
                id=uuid.uuid4(),
                width=800,
                height=600,
            )
        assert "Either `url` or `base64_image` must be provided" in str(excinfo.value)
        
    def test_view_request_validation_mismatch(self):
        """Test ViewRequest validation with mismatched media type."""
        # Create valid image artifact
        image = ImageArtifact(
            id=uuid.uuid4(),
            url="https://example.com/image.jpg"
        )
        
        # Create request with mismatched media type
        with pytest.raises(ValueError) as excinfo:
            ViewRequest(
                input="Analyze this",
                media_type="video",  # Mismatched with image
                media=image,
                user_id="test-user",
                session_id=str(uuid.uuid4())
            )
        
        assert "media_type is 'video' but media is not a VideoArtifact" in str(excinfo.value)


class TestMediaModels:
    """Tests for the media models."""
    
    def test_image_from_artifact_content(self):
        """Test creating an Image from an ImageArtifact with content."""
        # Create an artifact with base64 content
        artifact = ImageArtifact(
            id=uuid.uuid4(),
            base64_image="aW1hZ2UgZGF0YQ==",  # "image data"
            width=800,
            height=600,
            mime_type="image/jpeg"
        )
        
        # Create Image from artifact
        image = Image.from_artifact(artifact)
        
        # Verify properties
        assert image.id == artifact.id
        assert image.width == 800
        assert image.height == 600
        assert image.format == "jpeg"
        
    def test_video_from_artifact_content(self):
        """Test creating a Video from a VideoArtifact with content."""
        # Create an artifact with base64 content
        artifact = VideoArtifact(
            id=uuid.uuid4(),
            base64_video="dmlkZW8gZGF0YQ==",  # "video data"
            width=1280,
            height=720,
            duration=30.0,
            frame_rate=30.0,
            mime_type="video/mp4"
        )
        
        # Create Video from artifact
        video = Video.from_artifact(artifact)
        
        # Verify properties
        assert video.id == artifact.id
        assert video.width == 1280
        assert video.height == 720
        assert video.duration == 30.0
        assert video.frame_rate == 30.0
        assert video.format == "mp4"
        
    def test_image_get_content(self):
        """Test Image.get_content method with various sources."""
        # Test with content - Image requires one of the sources
        image1 = Image(content=b"direct content")
        assert image1.get_content() == b"direct content"
        
        # Test with URL
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.content = b"url content"
            mock_get.return_value = mock_response
            
            image2 = Image(url="https://example.com/image.jpg")
            assert image2.get_content() == b"url content"
        
        # Test with filepath
        with patch("pathlib.Path.read_bytes", return_value=b"file content"):
            image3 = Image(filepath="/path/to/image.jpg")
            assert image3.get_content() == b"file content"


class TestResponseModels:
    """Tests for the response models."""
    
    def test_health_response(self):
        """Test HealthResponse model."""
        response = HealthResponse(
            status_code=200,
            status="healthy",
            message="Service is running",
            timestamp="2023-01-01T12:00:00Z"
        )
        
        assert response.status_code == 200
        assert response.status == "healthy"
        assert response.message == "Service is running"
        assert response.timestamp == "2023-01-01T12:00:00Z"
        
    def test_error_response(self):
        """Test ErrorResponse model."""
        response = ErrorResponse(
            status_code=500,
            status="error",
            message="Something went wrong"
        )
        
        assert response.status_code == 500
        assert response.status == "error"
        assert response.message == "Something went wrong"
        
    def test_agent_response_with_metrics(self):
        """Test AgentResponse with metrics."""
        response = AgentResponse(
            agent_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            content="Response content",
            status="success",
            role=MessageRole.AGENT,
            metrics={"tokens": 150, "time": 0.5}
        )
        
        assert response.status == "success"
        assert response.content == "Response content"
        assert response.metrics["tokens"] == 150
        assert response.metrics["time"] == 0.5
        
    def test_agent_response_model_dict(self):
        """Test AgentResponse model_dump method."""
        agent_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        response = AgentResponse(
            agent_id=agent_id,
            session_id=session_id,
            content="Response content",
            status="success",
            role=MessageRole.AGENT,
            metrics={"tokens": 150}
        )
        
        # Convert to dict using model_dump (pydantic v2 method)
        response_dict = response.model_dump()
        
        # Verify dict content
        assert str(response_dict["agent_id"]) == agent_id
        assert str(response_dict["session_id"]) == session_id
        assert response_dict["content"] == "Response content"
        assert response_dict["status"] == "success"
        assert response_dict["role"] == MessageRole.AGENT
        assert response_dict["metrics"]["tokens"] == 150
