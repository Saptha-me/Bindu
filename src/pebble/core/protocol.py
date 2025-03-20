"""
Protocol definition for standardized agent communication.

This module defines the core protocol that all agents must follow to ensure
consistent communication regardless of the underlying framework.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    AgentStatus,
    MessageRole, 
    StatusResponse
)


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
