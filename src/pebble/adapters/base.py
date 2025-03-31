"""
Base adapter with common functionality.

This module provides a base adapter that implements common functionality for all adapters,
including media handling, session management, and error handling.
"""
import base64
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import httpx

from pebble.core.protocol import AgentProtocol, CognitiveAgentProtocol
from pebble.schemas.models import (
    ActionRequest,
    ActionResponse,
    MessageRole,
    ImageArtifact,
    ListenRequest,
    VideoArtifact,
    ViewRequest
)

class BaseAdapter(AgentProtocol):
    """Base adapter with common functionality for all framework adapters."""
    
    def __init__(self, 
                 agent: Any, 
                 agent_id: Optional[UUID] = None, 
                 name: Optional[str] = None, 
                 framework: str = "unknown",
                 capabilities: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize the base adapter.
        
        Args:
            agent: The agent implementation
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            framework: Name of the framework the agent is based on
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
        """
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name,
            framework=framework,
            capabilities=capabilities,
            metadata=metadata or {}
        )
        
        # Store session history for continuity
        self.sessions = {}
    
    def _initialize_session(self, session_id, request):
        """Helper to initialize session and set agent properties."""
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "agent_state": {}
            }
    
    def _download_content_from_url(self, url: str) -> bytes:
        """Download content from a URL.
        
        Args:
            url: URL to download content from
            
        Returns:
            Downloaded content as bytes
            
        Raises:
            Exception: If download fails
        """
        with httpx.Client() as client:
            response = client.get(url)
            if response.status_code != 200:
                raise Exception(f"HTTP status {response.status_code}")
            return response.content
    
    def _decode_base64(self, base64_content: str) -> bytes:
        """Decode base64 content to bytes.
        
        Args:
            base64_content: Base64 encoded content
            
        Returns:
            Decoded content as bytes
        """
        # Remove potential data URL prefix
        if ',' in base64_content:
            base64_content = base64_content.split(',', 1)[1]
            
        return base64.b64decode(base64_content)
        
    def _create_response(self, session_id, response_content, request, tool_calls=None):
        """Create response and update session history."""
        # Store the response in session history
        self.sessions[session_id]["history"].append({
            "role": MessageRole.AGENT,
            "content": response_content
        })
        
        # Create and return the response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=session_id,
            message=response_content,
            role=MessageRole.AGENT,
            metadata=request.metadata,
            tool_calls=tool_calls if tool_calls else None
        )


class BaseCognitiveAdapter(CognitiveAgentProtocol):
    """Base adapter with common functionality for cognitive adapters."""
    
    def __init__(self, 
                 agent: Any, 
                 agent_id: Optional[UUID] = None, 
                 name: Optional[str] = None, 
                 framework: str = "unknown",
                 capabilities: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 cognitive_capabilities: Optional[List[str]] = None):
        """Initialize the base cognitive adapter.
        
        Args:
            agent: The agent implementation
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            framework: Name of the framework the agent is based on
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
            cognitive_capabilities: List of cognitive capabilities
        """
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name,
            framework=framework,
            capabilities=capabilities,
            metadata=metadata or {},
            cognitive_capabilities=cognitive_capabilities
        )
        
        # Store session history for continuity
        self.sessions = {}
    
    def _initialize_session(self, session_id, request):
        """Helper to initialize session and set agent properties."""
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "agent_state": {}
            }
    
    def _download_content_from_url(self, url: str) -> bytes:
        """Download content from a URL.
        
        Args:
            url: URL to download content from
            
        Returns:
            Downloaded content as bytes
            
        Raises:
            Exception: If download fails
        """
        with httpx.Client() as client:
            response = client.get(url)
            if response.status_code != 200:
                raise Exception(f"HTTP status {response.status_code}")
            return response.content
    
    def _decode_base64(self, base64_content: str) -> bytes:
        """Decode base64 content to bytes.
        
        Args:
            base64_content: Base64 encoded content
            
        Returns:
            Decoded content as bytes
        """
        # Remove potential data URL prefix
        if ',' in base64_content:
            base64_content = base64_content.split(',', 1)[1]
            
        return base64.b64decode(base64_content)
        
    def _create_response(self, session_id, response_content, request, tool_calls=None):
        """Create response and update session history."""
        # Store the response in session history
        self.sessions[session_id]["history"].append({
            "role": MessageRole.AGENT,
            "content": response_content
        })
        
        # Create and return the response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=session_id,
            message=response_content,
            role=MessageRole.AGENT,
            metadata=request.metadata,
            tool_calls=tool_calls if tool_calls else None
        )