"""
Message schemas for agent communication.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Enumeration of supported message types."""
    TEXT = "text"
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"


class BaseMessage(BaseModel):
    """Base schema for all messages exchanged between agents."""
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None
    protocol_version: str = "1.0.0"
    
    class Config:
        arbitrary_types_allowed = True


class TextMessage(BaseMessage):
    """Schema for simple text messages between agents."""
    message_type: MessageType = MessageType.TEXT
    content: str
    metadata: Optional[Dict[str, Any]] = None


class CommandMessage(BaseMessage):
    """Schema for command messages that request agents to perform actions."""
    message_type: MessageType = MessageType.COMMAND
    command: str
    arguments: Optional[Dict[str, Any]] = {}
    timeout_seconds: Optional[float] = None
    priority: int = 0


class ResponseMessage(BaseMessage):
    """Schema for response messages sent after processing a command."""
    message_type: MessageType = MessageType.RESPONSE
    in_response_to: str  # The command message_id this is responding to
    status: str  # "success", "failure", "in_progress", etc.
    content: Any
    metadata: Optional[Dict[str, Any]] = None


class ErrorMessage(BaseMessage):
    """Schema for error messages when problems occur during communication."""
    message_type: MessageType = MessageType.ERROR
    in_response_to: Optional[str] = None  # The message_id this error relates to
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
