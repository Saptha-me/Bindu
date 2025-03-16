"""
Core protocol implementation for agent communication in Pebble.

This module provides a simplified protocol for standardized communication
between different agent types (smolagent, agno, crew).
"""
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message types supported by the protocol."""
    TEXT = "text"
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"


class AgentType(str, Enum):
    """Agent types supported by the protocol."""
    SMOL = "smol"
    AGNO = "agno"
    CREW = "crew"
    CUSTOM = "custom"


class Message(BaseModel):
    """Base message format for agent communication."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MessageType
    sender: str
    receiver: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: Any
    metadata: Optional[Dict[str, Any]] = None


class Protocol:
    """
    A simplified protocol for agent communication.
    
    This class handles serialization, deserialization, and validation
    of messages exchanged between different agent types.
    """
    
    @staticmethod
    def create_message(
        message_type: MessageType,
        sender: str,
        content: Any,
        receiver: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create a new protocol message.
        
        Args:
            message_type: Type of message
            sender: Identifier of the sending agent
            content: Message content
            receiver: Identifier of the receiving agent (optional)
            metadata: Additional message metadata (optional)
            
        Returns:
            Message: The created message
        """
        return Message(
            type=message_type,
            sender=sender,
            receiver=receiver,
            content=content,
            metadata=metadata or {}
        )
    
    @staticmethod
    def serialize(message: Message) -> str:
        """
        Serialize a message to JSON string.
        
        Args:
            message: The message to serialize
            
        Returns:
            str: JSON string representation
        """
        message_dict = message.dict()
        # Convert datetime to ISO format string
        message_dict["timestamp"] = message_dict["timestamp"].isoformat()
        return json.dumps(message_dict)
    
    @staticmethod
    def deserialize(data: str) -> Message:
        """
        Deserialize a JSON string to a message.
        
        Args:
            data: JSON string to deserialize
            
        Returns:
            Message: The deserialized message
        """
        message_dict = json.loads(data)
        return Message.parse_obj(message_dict)
    
    @staticmethod
    def adapt_for_agent_type(message: Message, agent_type: AgentType) -> Dict[str, Any]:
        """
        Adapt a message for a specific agent type.
        
        Args:
            message: The message to adapt
            agent_type: Target agent type
            
        Returns:
            Dict[str, Any]: Adapted message for the agent type
        """
        message_dict = message.dict()
        
        # Adapt based on agent type
        if agent_type == AgentType.SMOL:
            # SmolAgent expects a simpler format
            return {
                "role": "user" if message.type == MessageType.TEXT else "system",
                "content": message.content,
                "metadata": message.metadata or {}
            }
        
        elif agent_type == AgentType.AGNO:
            # Agno expects specific message format
            return {
                "message_id": message.id,
                "type": message.type.value,
                "from": message.sender,
                "to": message.receiver,
                "content": message.content,
                "metadata": message.metadata or {}
            }
        
        elif agent_type == AgentType.CREW:
            # CrewAI expects a crew-compatible format
            return {
                "id": message.id,
                "type": message.type.value,
                "sender": message.sender,
                "content": message.content,
                "timestamp": message.timestamp.isoformat()
            }
        
        # Default: just return the dict representation
        return message_dict
