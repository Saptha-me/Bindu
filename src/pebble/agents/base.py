"""
Base adapter for agent integration with Pebble protocol.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from ..protocol.schemas.message import BaseMessage


class BaseAgentAdapter(ABC):
    """
    Base adapter class for integrating different agent types with the Pebble protocol.
    
    This abstract class defines the interface that all agent adapters must implement,
    ensuring consistent communication between different agent implementations.
    """
    
    def __init__(self, agent: Any):
        """
        Initialize the adapter with an agent instance.
        
        Args:
            agent: The agent instance to adapt
        """
        self.agent = agent
        
    @abstractmethod
    async def send_message(self, message: BaseMessage) -> Optional[BaseMessage]:
        """
        Send a message to the agent and return any response.
        
        Args:
            message: The message to send to the agent
            
        Returns:
            Optional[BaseMessage]: The agent's response if any
        """
        pass
    
    @abstractmethod
    async def receive_message(self, message: BaseMessage) -> None:
        """
        Process a received message from another agent.
        
        Args:
            message: The message received from another agent
        """
        pass
    
    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the adapted agent.
        
        Returns:
            Dict[str, Any]: Information about the agent
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities of the adapted agent.
        
        Returns:
            List[str]: List of capability identifiers
        """
        pass
    
    @abstractmethod
    def supports_protocol(self, protocol_name: str) -> bool:
        """
        Check if the agent supports a specific protocol.
        
        Args:
            protocol_name: The name of the protocol to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        pass
