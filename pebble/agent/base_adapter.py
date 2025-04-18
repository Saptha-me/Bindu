"""
Base Adapter for Pebble Protocol

This module defines the base adapter interface that all agent-specific adapters must implement.
It provides protocol handlers for the Pebble protocol methods.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Callable
import uuid

from pebble.core.protocol import ProtocolMethod, TaskStatus


class BaseAdapter(ABC):
    """
    Base adapter class that provides the framework for integrating any agent with the Pebble protocol.
    Subclasses must implement the create_agent_runner and create_protocol_handler methods.
    """
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize with an optional agent ID"""
        self.agent_id = agent_id or str(uuid.uuid4())


class BaseAgentRunner(BaseAdapter, ABC):
    """
    Base class for agent runners that all framework-specific implementations must implement.
    This class defines the interface for the REST API server endpoints.
    """
    
    @abstractmethod
    def run(self,
            input_text: str,
            stream: bool = False,
            show_full_reasoning: bool = False,
            stream_intermediate_steps: bool = False,
            **kwargs) -> Any:
        """Run the agent with the given input text"""
        pass
    
    def get_status(self) -> str:
        """Get the current status of the agent"""
        return "healthy"


class BaseProtocolHandler(BaseAdapter, ABC):
    """
    Base class for protocol handlers that all framework-specific implementations must implement.
    This class defines handlers for the Pebble protocol methods.
    """

    @abstractmethod
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the Context method.
        
        Required params:
            - operation: The operation to perform (add, update, delete)
            - key: The key of the context
            
        Optional params:
            - value: The value of the context
            - metadata: Metadata for the context
        """
        pass