"""
Common data models and schemas for the Pebble framework.

This module defines the data models used throughout the Pebble framework for
consistency and type safety.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


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


class ActionRequest(BaseModel):
    """A request for an agent to take action."""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(default_factory=uuid4, description="Session ID for conversation continuity")
    message: str = Field(description="Message content from the user")
    role: MessageRole = Field(default=MessageRole.USER, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the request")
    stream: bool = Field(default=False, description="Whether to stream the response")


class ActionResponse(BaseModel):
    """A response from an agent action."""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(description="Session ID for conversation continuity")
    message: str = Field(description="Response content from the agent")
    role: MessageRole = Field(default=MessageRole.AGENT, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata from the agent")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool calls made by the agent")


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
