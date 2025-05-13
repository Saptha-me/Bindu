"""
Tests for model schema validation in pebbling.
"""

import uuid
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import httpx
from pydantic import ValidationError

from pebbling.server.schemas.model import (
    ImageArtifact, VideoArtifact, AudioArtifact,
    MessageRole, AgentResponse, Media
)


class TestImageArtifact:
    """Tests for the ImageArtifact model and its validation."""

    def test_url_image(self):
        """Test creating an ImageArtifact with a URL."""
        # Create an artifact with a URL
        artifact_id = uuid.uuid4()
        artifact = ImageArtifact(
            id=artifact_id,
            url="https://example.com/image.jpg",
            alt_text="Test image"
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.url == "https://example.com/image.jpg"
        assert artifact.alt_text == "Test image"
        assert artifact.base64_image is None
        
    def test_base64_image(self):
        """Test creating an ImageArtifact with base64 content."""
        # Create test base64 image
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Create an artifact with base64 content
        artifact_id = uuid.uuid4()
        artifact = ImageArtifact(
            id=artifact_id,
            base64_image=base64_data
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.base64_image == base64_data
        assert artifact.url is None
        
    def test_get_content(self):
        """Test the get_content method of ImageArtifact."""
        # Create test base64 image
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Create an artifact with base64 content
        artifact = ImageArtifact(
            id=uuid.uuid4(),
            base64_image=base64_data
        )
        
        # Get content
        content = artifact.get_content()
        
        # Verify content
        assert content is not None
        assert isinstance(content, bytes)
        
    def test_get_content_url(self):
        """Test getting content from URL."""
        # Create an artifact with URL
        artifact = ImageArtifact(
            id=uuid.uuid4(),
            url="https://example.com/image.jpg"
        )
        
        # Mock httpx.get
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.content = b"image_data"
            mock_get.return_value = mock_response
            
            # Get content
            content = artifact.get_content()
            
            # Verify content
            assert content is not None
            assert content == b"image_data"
            mock_get.assert_called_once_with("https://example.com/image.jpg")


class TestVideoArtifact:
    """Tests for the VideoArtifact model and its validation."""

    def test_url_video(self):
        """Test creating a VideoArtifact with a URL."""
        # Create an artifact with a URL
        artifact_id = uuid.uuid4()
        artifact = VideoArtifact(
            id=artifact_id,
            url="https://example.com/video.mp4",
            caption="Test video"
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.url == "https://example.com/video.mp4"
        assert artifact.caption == "Test video"
        assert artifact.base64_video is None
        
    def test_base64_video(self):
        """Test creating a VideoArtifact with base64 content."""
        # Create test base64 video
        base64_data = "dmlkZW9fZGF0YQ=="  # base64 for "video_data"
        
        # Create an artifact with base64 content
        artifact_id = uuid.uuid4()
        artifact = VideoArtifact(
            id=artifact_id,
            base64_video=base64_data
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.base64_video == base64_data
        assert artifact.url is None
        
    def test_get_content(self):
        """Test the get_content method of VideoArtifact."""
        # Create test base64 video
        base64_data = "dmlkZW9fZGF0YQ=="  # base64 for "video_data"
        
        # Create an artifact with base64 content
        artifact = VideoArtifact(
            id=uuid.uuid4(),
            base64_video=base64_data
        )
        
        # Get content
        with patch("base64.b64decode", return_value=b"decoded_video_data") as mock_decode:
            content = artifact.get_content()
            
            # Verify content
            assert content is not None
            assert content == b"decoded_video_data"
            mock_decode.assert_called_once_with(base64_data)


class TestAudioArtifact:
    """Tests for the AudioArtifact model and its validation."""

    def test_url_audio(self):
        """Test creating an AudioArtifact with a URL."""
        # Create an artifact with a URL
        artifact_id = uuid.uuid4()
        artifact = AudioArtifact(
            id=artifact_id,
            url="https://example.com/audio.mp3"
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.url == "https://example.com/audio.mp3"
        assert artifact.base64_audio is None
        
    def test_base64_audio(self):
        """Test creating an AudioArtifact with base64 content."""
        # Create test base64 audio
        base64_data = "YXVkaW9fZGF0YQ=="  # base64 for "audio_data"
        
        # Create an artifact with base64 content
        artifact_id = uuid.uuid4()
        artifact = AudioArtifact(
            id=artifact_id,
            base64_audio=base64_data
        )
        
        # Verify properties
        assert artifact.id == artifact_id
        assert artifact.base64_audio == base64_data
        assert artifact.url is None
        
    def test_validation_errors(self):
        """Test validation errors in AudioArtifact."""
        # Test with both URL and base64
        with pytest.raises(ValueError) as excinfo:
            AudioArtifact(
                id=uuid.uuid4(),
                url="https://example.com/audio.mp3",
                base64_audio="YXVkaW9fZGF0YQ=="
            )
        assert "Provide either `url` or `base64_audio`, not both" in str(excinfo.value)
        
        # Test with neither URL nor base64
        with pytest.raises(ValueError) as excinfo:
            AudioArtifact(id=uuid.uuid4())
        assert "Either `url` or `base64_audio` must be provided" in str(excinfo.value)


class TestAgentResponse:
    """Tests for the AgentResponse model."""
    
    def test_response_metrics(self):
        """Test response with custom metrics."""
        agent_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        # Create response with metrics
        response = AgentResponse(
            agent_id=agent_id,
            session_id=session_id,
            content="Test response",
            metrics={"tokens": 42, "time": 0.5}
        )
        
        # Verify metrics
        assert response.metrics["tokens"] == 42
        assert response.metrics["time"] == 0.5
        
    def test_response_metadata(self):
        """Test response with metadata."""
        agent_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        # Create response with metadata
        response = AgentResponse(
            agent_id=agent_id,
            session_id=session_id,
            content="Test response",
            metadata={"source": "test", "confidence": 0.9}
        )
        
        # Verify metadata
        assert response.metadata["source"] == "test"
        assert response.metadata["confidence"] == 0.9
        
    def test_custom_role(self):
        """Test response with custom role."""
        agent_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        # Create response with custom role
        response = AgentResponse(
            agent_id=agent_id,
            session_id=session_id,
            content="User input",
            role=MessageRole.USER
        )
        
        # Verify role
        assert response.role == MessageRole.USER
