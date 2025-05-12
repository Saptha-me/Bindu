"""
Response Models for pebbling Server

This module defines Pydantic models for standardized request and response formats
used by the pebbling REST API server.
"""
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, model_validator
from uuid import UUID, uuid4
from enum import Enum
from pathlib import Path
import httpx
import base64

class MessageRole(str, Enum):
    """Role of a message sender."""
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"

class HealthResponse(BaseModel):
    """Health check response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field(..., description="Current status of the agent")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Timestamp of the health check")

    class Config:
        schema_extra = {
            "example": {
                "status_code": 200,
                "status": "healthy",
                "message": "Service is running",
                "timestamp": "2023-04-01T12:34:56Z"
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")

    class Config:
        schema_extra = {
            "example": {
                "status_code": 500,
                "status": "error",
                "message": "Internal server error"
            }
        }

class AgentRequest(BaseModel):
    """Agent run request model"""
    input: str = Field(..., description="Input text for the agent", example="Tell me about the latest news in technology")
    user_id: str = Field(..., description="User ID", example="user-123456")
    session_id: str = Field(..., description="Session ID", example="session-789012")
    stream: bool = Field(..., description="Stream the response", example=False)
    
    class Config:
        schema_extra = {
            "example": {
                "input": "What's happening in the stock market today?",
                "user_id": "user-abc123",
                "session_id": "session-xyz456",
                "stream": False
            }
        }


class AgentResponse(BaseModel):
    """Agent run response model"""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(description="Session ID for conversation continuity")
    role: MessageRole = Field(default=MessageRole.AGENT, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata from the agent")
    status: str = Field("success", description="Success status")
    content: str = Field(..., description="Agent response content")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")

    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-123",
                "session_id": "session-xyz456",
                "role": "agent",
                "metadata": {
                    "original_prompt": "What's happening in the stock market today?",
                    "revised_prompt": "What's happening in the stock market today?"
                },
                "status": "success",
                "content": "The stock market is expected to continue its upward trend in the coming weeks.",
                "metrics": {
                    "response_time": "1.234 seconds"
                }
            }
        }


# JSON-RPC Models
class JsonRpcRequest(BaseModel):
    """JSON-RPC request model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request ID")
    method: str = Field(..., description="Method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    source_agent_id: Optional[str] = Field(None, description="Source agent ID")
    destination_agent_id: Optional[str] = Field(None, description="Destination agent ID")
    timestamp: Optional[str] = Field(None, description="Request timestamp")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "act",
                "params": {
                    "input": "What's happening in the stock market today?",
                    "user_id": "user-abc123",
                    "session_id": "session-xyz456"
                },
                "source_agent_id": "agent-123",
                "destination_agent_id": "agent-456",
                "timestamp": "2023-04-01T12:34:56Z"
            }
        }


class JsonRpcErrorDetail(BaseModel):
    """JSON-RPC error detail model"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")

    class Config:
        schema_extra = {
            "example": {
                "code": -32601,
                "message": "Method not found",
                "data": {
                    "original_error": "Method not found"
                }
            }
        }


class JsonRpcError(BaseModel):
    """JSON-RPC error response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version") 
    id: Optional[str] = Field(None, description="Request ID")
    error: JsonRpcErrorDetail = Field(..., description="Error details")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": {
                        "original_error": "Method not found"
                    }
                }
            }
        }


class JsonRpcResponse(BaseModel):
    """JSON-RPC success response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request ID")
    result: Dict[str, Any] = Field(..., description="Response result")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "result": {
                    "content": "The stock market is expected to continue its upward trend in the coming weeks.",
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "The stock market is expected to continue its upward trend in the coming weeks."
                        }
                    ],
                    "metrics": {
                        "response_time": "1.234 seconds"
                    }
                }
            }
        }


class Media(BaseModel):
    """Base class for media content."""
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "id": "1",
                "original_prompt": "What's happening in the stock market today?",
                "revised_prompt": "What's happening in the stock market today?"
            }
        }
    

class AudioArtifact(Media):
    """Audio data for agent processing."""
    id: UUID = Field(default_factory=uuid4)  # Unique identifier for the audio artifact
    url: Optional[str] = None  # Remote location for file
    base64_audio: Optional[str] = None  # Base64-encoded audio data
    length: Optional[str] = None
    mime_type: Optional[str] = None

    @model_validator(mode="before")
    def validate_exclusive_audio(cls, data: Any):
        """
        Ensure that either `url` or `base64_audio` is provided, but not both.
        """
        if data.get("url") and data.get("base64_audio"):
            raise ValueError("Provide either `url` or `base64_audio`, not both.")
        if not data.get("url") and not data.get("base64_audio"):
            raise ValueError("Either `url` or `base64_audio` must be provided.")
        return data

    class Config:
        schema_extra = {
            "example": {
                "agent_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "message": "whats the capital of india?",
                "role": "user",
                "metadata": {
                    "source": "mobile_app"
                },
                "stream": False,
                "audio": {
                    "url" : "https://raw.githubusercontent.com/Pebbling-ai/pebble/main/sample_data/audio/sample_audio.mp3"
                }
            }
        }


class ListenRequest(AgentRequest):
    """Combined request for listen endpoint containing both action and audio data."""
    input: str = Field(..., description="Input text for the agent", example="Tell me about the latest news in technology")
    audio: AudioArtifact


class ImageArtifact(Media):
    """Image data for agent processing."""
    id: UUID = Field(default_factory=uuid4)  # Unique identifier for the image artifact
    url: Optional[str] = None  # Remote location for image file
    base64_image: Optional[str] = None  # Base64-encoded image data
    width: Optional[int] = None  # Image width in pixels
    height: Optional[int] = None  # Image height in pixels
    mime_type: Optional[str] = None  # e.g., "image/jpeg", "image/png"
    alt_text: Optional[str] = None  # Alternative text description of the image
    detail: Optional[str] = None  # Image detail level (low, medium, high, auto) for vision APIs

    @model_validator(mode="before")
    def validate_exclusive_image(cls, data: Any):
        """
        Ensure that either `url` or `base64_image` is provided, but not both.
        """
        if data.get("url") and data.get("base64_image"):
            raise ValueError("Provide either `url` or `base64_image`, not both.")
        if not data.get("url") and not data.get("base64_image"):
            raise ValueError("Either `url` or `base64_image` must be provided.")
        return data
    
    def get_content(self) -> Optional[bytes]:
        """Retrieve the image content either from URL or base64."""
        if self.url:
            return httpx.get(self.url).content
        elif self.base64_image:
            return base64.b64decode(self.base64_image)
        return None


class VideoArtifact(Media):
    """Video data for agent processing."""
    id: UUID = Field(default_factory=uuid4)  # Unique identifier for the video artifact
    url: Optional[str] = None  # Remote location for video file
    base64_video: Optional[str] = None  # Base64-encoded video data
    duration: Optional[float] = None  # Duration in seconds
    width: Optional[int] = None  # Video width in pixels
    height: Optional[int] = None  # Video height in pixels
    frame_rate: Optional[float] = None  # Frames per second
    mime_type: Optional[str] = None  # e.g., "video/mp4"
    caption: Optional[str] = None  # Caption or description of the video
    eta: Optional[str] = None  # Estimated time for processing (from agno)

    @model_validator(mode="before")
    def validate_exclusive_video(cls, data: Any):
        """
        Ensure that either `url` or `base64_video` is provided, but not both.
        """
        if data.get("url") and data.get("base64_video"):
            raise ValueError("Provide either `url` or `base64_video`, not both.")
        if not data.get("url") and not data.get("base64_video"):
            raise ValueError("Either `url` or `base64_video` must be provided.")
        return data
    
    def get_content(self) -> Optional[bytes]:
        """Retrieve the video content either from URL or base64."""
        if self.url:
            return httpx.get(self.url).content
        elif self.base64_video:
            return base64.b64decode(self.base64_video)
        return None


# -----------------------------------------------------------------------------
# Media Models - Internal Processing
# -----------------------------------------------------------------------------

class Image(BaseModel):
    """More complete image class for internal processing."""
    url: Optional[str] = None  # Remote location for image
    filepath: Optional[Union[Path, str]] = None  # Local location for image
    content: Optional[bytes] = None  # Actual image bytes
    format: Optional[str] = None  # e.g., "png", "jpeg", "webp", "gif"
    width: Optional[int] = None
    height: Optional[int] = None
    detail: Optional[str] = None  # low, medium, high, auto
    alt_text: Optional[str] = None
    id: Optional[UUID] = Field(default_factory=uuid4)
    
    @model_validator(mode="before")
    def validate_data(cls, data: Any):
        """Ensure exactly one of url, filepath, or content is provided."""
        url = data.get("url")
        filepath = data.get("filepath")
        content = data.get("content")
        
        # Convert content to bytes if it's a base64 string
        if content and isinstance(content, str):
            try:
                data["content"] = base64.b64decode(content)
            except Exception:
                pass
        
        # Count how many source fields are provided
        count = len([field for field in [url, filepath, content] if field is not None])
        
        if count == 0:
            raise ValueError("One of `url`, `filepath`, or `content` must be provided.")
        elif count > 1:
            raise ValueError("Only one of `url`, `filepath`, or `content` should be provided.")
            
        return data
    
    def get_content(self) -> Optional[bytes]:
        """Get image content from any source."""
        if self.content:
            return self.content
        elif self.url:
            return httpx.get(self.url).content
        elif self.filepath:
            return Path(self.filepath).read_bytes()
        return None
    
    @classmethod
    def from_artifact(cls, artifact: ImageArtifact) -> "Image":
        """Create an Image instance from an ImageArtifact."""
        if artifact.url:
            return cls(
                url=artifact.url,
                width=artifact.width,
                height=artifact.height,
                format=artifact.mime_type.split("/")[1] if artifact.mime_type else None,
                detail=artifact.detail,
                alt_text=artifact.alt_text,
                id=artifact.id
            )
        elif artifact.base64_image:
            return cls(
                content=base64.b64decode(artifact.base64_image),
                width=artifact.width,
                height=artifact.height,
                format=artifact.mime_type.split("/")[1] if artifact.mime_type else None,
                detail=artifact.detail,
                alt_text=artifact.alt_text,
                id=artifact.id
            )


class Video(BaseModel):
    """More complete video class for internal processing."""
    url: Optional[str] = None  # Remote location for video
    filepath: Optional[Union[Path, str]] = None  # Local location for video
    content: Optional[bytes] = None  # Actual video bytes
    format: Optional[str] = None  # e.g., "mp4", "mov", "avi", "webm"
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[float] = None
    caption: Optional[str] = None
    id: Optional[UUID] = Field(default_factory=uuid4)
    
    @model_validator(mode="before")
    def validate_data(cls, data: Any):
        """Ensure exactly one of url, filepath, or content is provided."""
        url = data.get("url")
        filepath = data.get("filepath")
        content = data.get("content")
        
        # Convert content to bytes if it's a base64 string
        if content and isinstance(content, str):
            try:
                data["content"] = base64.b64decode(content)
            except Exception:
                pass
        
        # Count how many source fields are provided
        count = len([field for field in [url, filepath, content] if field is not None])
        
        if count == 0:
            raise ValueError("One of `url`, `filepath`, or `content` must be provided.")
        elif count > 1:
            raise ValueError("Only one of `url`, `filepath`, or `content` should be provided.")
            
        return data
    
    def get_content(self) -> Optional[bytes]:
        """Get video content from any source."""
        if self.content:
            return self.content
        elif self.url:
            return httpx.get(self.url).content
        elif self.filepath:
            return Path(self.filepath).read_bytes()
        return None
    
    @classmethod
    def from_artifact(cls, artifact: VideoArtifact) -> "Video":
        """Create a Video instance from a VideoArtifact."""
        if artifact.url:
            return cls(
                url=artifact.url,
                width=artifact.width,
                height=artifact.height,
                duration=artifact.duration,
                frame_rate=artifact.frame_rate,
                format=artifact.mime_type.split("/")[1] if artifact.mime_type else None,
                caption=artifact.caption,
                id=artifact.id
            )
        elif artifact.base64_video:
            return cls(
                content=base64.b64decode(artifact.base64_video),
                width=artifact.width,
                height=artifact.height,
                duration=artifact.duration,
                frame_rate=artifact.frame_rate,
                format=artifact.mime_type.split("/")[1] if artifact.mime_type else None,
                caption=artifact.caption,
                id=artifact.id
            )


class ViewRequest(AgentRequest):
    """Combined request for view endpoint containing both action and media data (image or video)."""
    media_type: Literal["image", "video"] = Field(..., description="Type of media being sent")
    media: Union[ImageArtifact, VideoArtifact]
    
    @model_validator(mode='after')
    def validate_media_type(self):
        """Validate that the media_type matches the media object type."""
        if self.media_type == "image" and not isinstance(self.media, ImageArtifact):
            raise ValueError("media_type is 'image' but media is not an ImageArtifact")
        if self.media_type == "video" and not isinstance(self.media, VideoArtifact):
            raise ValueError("media_type is 'video' but media is not a VideoArtifact")
        return self
