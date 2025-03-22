"""
Media schema models for the agent protocol.

This module defines media-related schema models used for enabling agents to process
different types of media inputs like audio, images, etc.
"""

from typing import Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


class Media(BaseModel):
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None


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
