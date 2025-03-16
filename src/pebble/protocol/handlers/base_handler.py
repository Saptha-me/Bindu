"""
Base handler for processing agent communication messages.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

from ..schemas.message import BaseMessage


class BaseProtocolHandler(ABC):
    """
    Base class for all protocol message handlers.
    
    This abstract class defines the interface that all protocol handlers must implement,
    providing a standardized way to process messages between different agent types.
    """
    
    def __init__(self):
        self.handlers = {}
        
    def register_handler(self, message_type: str, handler_func: Callable[[BaseMessage], Optional[BaseMessage]]):
        """
        Register a handler function for a specific message type.
        
        Args:
            message_type: The type of message this handler processes
            handler_func: Function that will process messages of this type
        """
        self.handlers[message_type] = handler_func
    
    def get_handler(self, message_type: str) -> Optional[Callable]:
        """
        Get the handler function for a specific message type.
        
        Args:
            message_type: The type of message to get a handler for
            
        Returns:
            Optional[Callable]: The handler function if found, None otherwise
        """
        return self.handlers.get(message_type)
    
    @abstractmethod
    async def process_message(self, message: BaseMessage) -> Optional[BaseMessage]:
        """
        Process an incoming message and return a response if needed.
        
        Args:
            message: The message to process
            
        Returns:
            Optional[BaseMessage]: A response message if appropriate, None otherwise
        """
        pass
    
    @abstractmethod
    async def route_message(self, message: BaseMessage, target_agent_id: str) -> bool:
        """
        Route a message to a specific agent.
        
        Args:
            message: The message to route
            target_agent_id: The ID of the agent to route the message to
            
        Returns:
            bool: True if the message was successfully routed, False otherwise
        """
        pass
