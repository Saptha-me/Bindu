"""
Base protocol definition for agent communication in Pebble.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

class BaseProtocol(ABC):
    """
    Base class for all communication protocols used between agents.
    
    This abstract class defines the interface that all protocol implementations
    must adhere to, ensuring standardized communication between different agent types.
    """
    
    @abstractmethod
    def serialize_message(self, message: Dict[str, Any]) -> bytes:
        """
        Serialize a message dictionary into bytes for transmission.
        
        Args:
            message: The message dictionary to serialize
            
        Returns:
            bytes: The serialized message
        """
        pass
    
    @abstractmethod
    def deserialize_message(self, data: bytes) -> Dict[str, Any]:
        """
        Deserialize received bytes into a message dictionary.
        
        Args:
            data: The bytes to deserialize
            
        Returns:
            Dict[str, Any]: The deserialized message
        """
        pass
    
    @abstractmethod
    def validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate if a message conforms to this protocol's schema.
        
        Args:
            message: The message to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def format_for_agent_type(self, message: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
        """
        Format a message specifically for the given agent type.
        
        Args:
            message: The message to format
            agent_type: The type of agent (e.g., "smol", "agno", "crew")
            
        Returns:
            Dict[str, Any]: The formatted message
        """
        pass
