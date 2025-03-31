"""
Common data models and schemas for the Pebble framework.

This module defines the data models used throughout the Pebble framework for
consistency and type safety.
"""
import base64
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID, uuid4
import httpx
from pydantic import BaseModel, Field, model_validator


class AgentStatus(str, Enum):
    """Status of an agent."""
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    INITIALIZING = "initializing"


class MessageRole(str, Enum):
    """Role of a message sender."""
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


class Message(BaseModel):
    """A message in the agent protocol."""
    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class StimulusType(str, Enum):
    """Types of stimuli an agent can process."""
    
    ACTION = "action"
    VERBAL = "verbal"
    VISUAL = "visual"
    THOUGHT = "thought"
    RESPONSE = "response"


class CognitiveState(BaseModel):
    """Representation of an agent's cognitive state."""
    
    mental_state: Dict[str, Any] = Field(default_factory=dict)
    episodic_memory: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_memory: Dict[str, Any] = Field(default_factory=dict)
    attention: Optional[StimulusType] = None
    context: List[str] = Field(default_factory=list)


class CognitiveRequest(BaseModel):
    """Request model for cognitive agent operations that is superseded by ActionRequest."""
    
    # This class is kept for backward compatibility but will be removed in a future version
    # Use ActionRequest with stimulus_type field instead
    agent_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(default_factory=uuid4)
    content: str
    stimulus_type: StimulusType
    stream: bool = Field(default=False, description="Whether to stream the response")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CognitiveResponse(BaseModel):
    """Response model for cognitive agent operations that is superseded by ActionResponse."""
    
    # This class is kept for backward compatibility but will be removed in a future version
    # Use ActionResponse with stimulus_type and cognitive_state fields instead
    agent_id: UUID
    session_id: UUID
    content: str
    stimulus_type: StimulusType
    cognitive_state: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    
class ActionRequest(BaseModel):
    """A request for an agent to take action, with support for cognitive capabilities."""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(default_factory=uuid4, description="Session ID for conversation continuity")
    message: str = Field(description="Message content from the user")
    role: MessageRole = Field(default=MessageRole.USER, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the request")
    stream: bool = Field(default=False, description="Whether to stream the response")
    stimulus_type: Optional[StimulusType] = Field(default=None, description="Type of stimulus for cognitive agents")
    cognitive_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Cognitive-specific metadata")

    @property
    def content(self) -> str:
        """Alias for message to maintain compatibility with CognitiveRequest."""
        return self.message


class ActionResponse(BaseModel):
    """A response from an agent action, with support for cognitive capabilities."""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(description="Session ID for conversation continuity")
    message: str = Field(description="Response content from the agent")
    role: MessageRole = Field(default=MessageRole.AGENT, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata from the agent")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool calls made by the agent")
    stimulus_type: Optional[StimulusType] = Field(default=None, description="Type of stimulus for cognitive agents")
    cognitive_state: Optional[Dict[str, Any]] = Field(default=None, description="Cognitive state of the agent")

    @property
    def content(self) -> str:
        """Alias for message to maintain compatibility with CognitiveResponse."""
        return self.message


class StatusResponse(BaseModel):
    """A response containing the status of an agent."""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    name: str = Field(description="Name of the agent")
    framework: str = Field(description="Framework the agent is based on")
    status: AgentStatus = Field(description="Current status of the agent")
    capabilities: List[str] = Field(description="List of capabilities the agent has")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata about the agent")


class DeploymentConfig(BaseModel):
    """Configuration for agent deployment."""
    host: str = Field(default="0.0.0.0", description="Host address to bind the server to")
    port: int = Field(default=8000, description="Port to run the server on")
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    enable_docs: bool = Field(default=True, description="Whether to enable API documentation")
    require_auth: bool = Field(default=True, description="Whether to require authentication")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    api_key_expire_days: int = Field(default=365, description="API key expiration in days")


# -----------------------------------------------------------------------------
# Media Models - Base
# -----------------------------------------------------------------------------

class Media(BaseModel):
    """Base class for media content."""
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None


# -----------------------------------------------------------------------------
# Media Models - Artifacts
# -----------------------------------------------------------------------------

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


class ListenRequest(ActionRequest):
    """Combined request for listen endpoint containing both action and audio data."""
    audio: AudioArtifact


class ViewRequest(ActionRequest):
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
