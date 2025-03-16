"""
Base adapter for integrating different agent types with the protocol.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..protocol import Protocol
from ..protocol import Message, MessageType


class BaseAdapter(ABC):
    """
    Base adapter for agent communication.
    
    This abstract class defines the interface that all agent type adapters
    must implement to ensure standardized communication through the protocol.
    """
    
    def __init__(self, agent: Any):
        """
        Initialize the adapter with an agent instance.
        
        Args:
            agent: The agent instance to adapt
        """
        self.agent = agent
        self.protocol = Protocol()
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Get the agent's unique identifier."""
        pass
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Get the agent's type (smol, agno, crew)."""
        pass
    
    @abstractmethod
    async def send_message(self, message: Message) -> Optional[Message]:
        """
        Send a message to the agent and get its response.
        
        Args:
            message: Protocol message to send
            
        Returns:
            Optional[Message]: Response message if any
        """
        pass
    
    @abstractmethod
    async def receive_message(self, message: Message) -> None:
        """
        Process a message received from another agent.
        
        Args:
            message: Protocol message received
        """
        pass
    
    def create_response(self, 
                        to_message: Message, 
                        content: Any, 
                        metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Create a response message to another message.
        
        Args:
            to_message: The message being responded to
            content: Response content
            metadata: Additional metadata (optional)
            
        Returns:
            Message: The response message
        """
        return Protocol.create_message(
            message_type=MessageType.RESPONSE,
            sender=self.agent_id,
            receiver=to_message.sender,
            content=content,
            metadata=metadata or {"in_response_to": to_message.id}
        )
