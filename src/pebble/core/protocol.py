"""
Protocol definition for standardized agent communication.

This module defines the core protocol that all agents must follow to ensure
consistent communication regardless of the underlying framework. It also provides
an extended CognitiveAgentProtocol with enhanced capabilities for more sophisticated agent interactions.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pebble.db.storage import PostgresStateProvider
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    AgentStatus,
    MessageRole, 
    StatusResponse,
    StimulusType,
    ListenRequest,
    ViewRequest
)

import logging
import time

logger = logging.getLogger(__name__)

# Maximum number of retry attempts for LLM operations
MAX_RETRIES = 2


class AgentProtocol:
    """Base class for the agent protocol."""
    
    def __init__(
        self,
        agent: Any,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        framework: str = "unknown",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize the agent protocol.
        
        Args:
            agent: The underlying agent implementation
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            framework: Name of the framework the agent is based on
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
        """
        self.agent = agent
        self.agent_id = agent_id or uuid4()
        self.name = name or getattr(agent, "name", "Unnamed Agent")
        self.framework = framework
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.status = AgentStatus.READY
        self.sessions = {}
    
    def get_status(self) -> StatusResponse:
        """Get the current status of the agent.
        
        Returns:
            StatusResponse: The current status of the agent
        """
        return StatusResponse(
            agent_id=self.agent_id,
            name=self.name,
            framework=self.framework,
            status=self.status,
            capabilities=self.capabilities,
            metadata=self.metadata
        )
    
    def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request and return a response.
        
        This method should be implemented by adapter classes.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("This method must be implemented by adapter classes")
    
    def act(self, request: ActionRequest) -> ActionResponse:
        """Process a standard text-based action and return a response.
        
        This is a convenience wrapper around process_action.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        return self.process_action(request)
    
    def listen(self, request: ListenRequest) -> ActionResponse:
        """Process an audio input and return a response.
        
        This method should be implemented by adapter classes that support audio processing.
        
        Args:
            request: The listen request containing audio data to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("Audio processing not supported by this adapter")
    
    def view(self, request: ViewRequest) -> ActionResponse:
        """Process an image or video input and return a response.
        
        This method should be implemented by adapter classes that support image/video processing.
        
        Args:
            request: The view request containing image/video data to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("Image/video processing not supported by this adapter")