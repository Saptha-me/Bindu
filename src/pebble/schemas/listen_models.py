"""
Listen request schema models for the agent protocol.

This module defines request schemas for audio processing endpoints.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from pebble.schemas.models import MessageRole
from pebble.schemas.media_models import AudioArtifact


class ListenRequest(BaseModel):
    """Combined request for listen endpoint containing both action and audio data."""
    agent_id: UUID
    session_id: UUID
    message: str = ""
    role: MessageRole = MessageRole.USER
    metadata: Optional[Dict[str, Any]] = None
    stream: bool = False
    audio: AudioArtifact
