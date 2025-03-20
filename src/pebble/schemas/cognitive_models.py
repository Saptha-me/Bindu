"""
Cognitive schema models for the agent protocol.

This module defines the cognitive schema models used for enabling more sophisticated
agent interactions based on the TinyTroupe-inspired cognitive framework.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


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
    """Request model for cognitive agent operations."""
    
    agent_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(default_factory=uuid4)
    content: str
    stimulus_type: StimulusType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CognitiveResponse(BaseModel):
    """Response model for cognitive agent operations."""
    
    agent_id: UUID
    session_id: UUID
    content: str
    stimulus_type: StimulusType
    cognitive_state: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Add these to models.py imports for backwards compatibility
__all__ = [
    "StimulusType",
    "CognitiveState",
    "CognitiveRequest",
    "CognitiveResponse"
]
