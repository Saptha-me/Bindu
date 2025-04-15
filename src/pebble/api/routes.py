"""
API Routes for the Pebble framework.

This module defines all API routes used by the Pebble framework for agent communication.
"""

from typing import Optional, List, Callable, Dict, Any
from uuid import UUID
import time
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status, Body, Query

from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, StatusResponse
from pebble.security.auth import get_auth_token
from pebble.security.keys import create_api_key

from pebble.schemas.models import ListenRequest, ViewRequest

from pydantic import BaseModel, Field

# Define models for agent communication endpoints
class AgentRelationship(BaseModel):
    """Model representing a relationship between two agents."""
    type: str = Field(..., description="Relationship type (e.g. 'Peer', 'Subordinate')")
    trust_level: float = Field(0.5, description="Trust level between agents (0.0-1.0)")
    interaction_count: int = Field(0, description="Number of interactions between these agents")

class AgentReference(BaseModel):
    """Model representing an agent reference with relationship information."""
    name: str = Field(..., description="Name of the agent")
    agent_id: str = Field(..., description="ID of the agent")
    relation: str = Field("Colleague agent", description="Relationship to this agent")
    roles: List[str] = Field(default_factory=list, description="Roles this agent can fulfill")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities this agent has")
    trust_level: float = Field(0.5, description="Trust level with this agent (0.0-1.0)")

class AgentMessageRequest(BaseModel):
    """Model for agent-to-agent message requests."""
    from_agent: str = Field(..., description="Name of the sending agent")
    to_agent: str = Field(..., description="Name of the receiving agent")
    message: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class HandoffRequest(BaseModel):
    """Model for agent handoff requests."""
    from_agent: str = Field(..., description="Name of the agent handing off")
    to_agent: str = Field(..., description="Name of the agent receiving the handoff")
    message: str = Field(..., description="Handoff message describing the task")
    context: Dict[str, Any] = Field(..., description="Current conversation/task context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class HandoffResponse(BaseModel):
    """Model for agent handoff responses."""
    content: str = Field(..., description="Response content from the receiving agent")
    context: Dict[str, Any] = Field(..., description="Updated context after handoff")
    session_id: str = Field(..., description="Session ID for this handoff")


def register_routes(
    app: FastAPI, 
    adapter: AgentProtocol, 
    require_auth: bool = True,
    additional_routes: Optional[List[Callable]] = None,
    additional_adapters: Optional[List[AgentProtocol]] = None
) -> None:
    """Register all routes for the Pebble API.
    
    Args:
        app: The FastAPI application
        adapter: The primary agent protocol adapter
        require_auth: Whether authentication is required
        additional_routes: Additional route handlers to register
        additional_adapters: Additional agent protocol adapters to include in status reports
    """
    
    # Initialize the list of all adapters
    all_adapters = [adapter]
    if additional_adapters:
        all_adapters.extend(additional_adapters)
    
    # Define route for agent status
    @app.get("/agents/status")
    async def get_all_agents_status(
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Get the current status of all deployed agents."""
        return {
            "agents": [
                {
                    "agent_id": str(a.agent_id),
                    "name": a.name,
                    "status": a.get_status().dict(),
                }
                for a in all_adapters
            ]
        }
    
    # Define route for agent action
    @app.post("/agent/act", response_model=ActionResponse)
    async def post_agent_act(
        request: ActionRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Process an action with the agent."""
        return adapter.act(request)

    # Define route for agent listen
    @app.post("/agent/listen", response_model=ActionResponse)
    async def post_agent_listen(
        listen_request: ListenRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Process an audio input with the agent.
        
        Send a JSON object with agent_id, session_id, message, role, metadata, stream,
        and audio fields all at the top level.
        """
        # Pass the ListenRequest directly to the adapter
        return adapter.listen(listen_request)

    # Define route for agent view
    @app.post("/agent/view", response_model=ActionResponse)
    async def post_agent_view(
        view_request: ViewRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Process an image or video input with the agent.
        
        Send a JSON object with agent_id, session_id, message, role, metadata, stream,
        and media (image or video) fields at the top level.
        """
        # Pass the ViewRequest directly to the adapter
        return adapter.view(view_request)
    
    # Define route to generate a new API key (admin only)
    @app.post("/admin/generate-api-key")
    async def generate_api_key(
        expire_days: int = 365,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Generate a new API key for authentication."""
        try:
            api_key = create_api_key(expire_days=expire_days)
            return {"api_key": api_key}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate API key: {str(e)}"
            )
    
    # Define route for agent-to-agent communication
    @app.post("/agent/multi", response_model=ActionResponse)
    async def post_agent_multi(
        request: AgentMessageRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Send a message from one agent to another.
        
        This enables agent-to-agent communication as defined in the registry.
        The "from_agent" and "to_agent" must be names of agents registered in the registry.
        """
        # Look for the registry in any adapter's metadata
        registry = None
        for a in all_adapters:
            if hasattr(a, 'metadata') and a.metadata and 'agent_registry' in a.metadata:
                registry = a.metadata['agent_registry']
                break
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent registry not found"
            )
        
        # Get the sending and receiving agents
        sender = registry.get_agent(request.from_agent)
        receiver = registry.get_agent(request.to_agent)
        
        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sending agent '{request.from_agent}' not found"
            )
        
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receiving agent '{request.to_agent}' not found"
            )
        
        # Send the message and get the response
        try:
            result = registry.send_message(
                request.from_agent, 
                request.to_agent, 
                request.message, 
                request.metadata
            )
            
            # Format as an ActionResponse
            return ActionResponse(
                agent_id=receiver.agent_id,
                session_id=request.metadata.get("session_id", str(UUID())) if request.metadata else str(UUID()),
                message=result,
                role="agent",
                metadata={
                    "from_agent": request.from_agent,
                    "to_agent": request.to_agent,
                    "timestamp": time.time()
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send message: {str(e)}"
            )
    
    # Define route for agent handoffs
    @app.post("/agent/handoff", response_model=HandoffResponse)
    async def post_agent_handoff(
        request: HandoffRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Implement a handoff from one agent to another.
        
        This enables task handoffs between agents, allowing one agent to pass 
        a task to another agent that is better suited to handle it.
        """
        # Look for the registry in any adapter's metadata
        registry = None
        for a in all_adapters:
            if hasattr(a, 'metadata') and a.metadata and 'agent_registry' in a.metadata:
                registry = a.metadata['agent_registry']
                break
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent registry not found"
            )
        
        # Get the sending and receiving agents
        sender = registry.get_agent(request.from_agent)
        receiver = registry.get_agent(request.to_agent)
        
        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sending agent '{request.from_agent}' not found"
            )
        
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receiving agent '{request.to_agent}' not found"
            )
        
        # Perform the handoff and get the result
        try:
            result = registry.handoff(
                request.from_agent,
                request.to_agent,
                request.message,
                request.context,
                request.metadata
            )
            
            return HandoffResponse(
                content=result["content"],
                context=result["context"],
                session_id=result["session_id"]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to perform handoff: {str(e)}"
            )
    
    # Define route to get agent relationships
    @app.get("/agent/relationships/{agent_name}")
    async def get_agent_relationships(
        agent_name: str,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Get the relationships for a specific agent."""
        # Look for the registry in any adapter's metadata
        registry = None
        for a in all_adapters:
            if hasattr(a, 'metadata') and a.metadata and 'agent_registry' in a.metadata:
                registry = a.metadata['agent_registry']
                break
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent registry not found"
            )
        
        # Check if agent exists
        if agent_name not in registry.relationships:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{agent_name}' not found"
            )
        
        # Get relationships for this agent
        relationships = registry.relationships[agent_name]
        
        # Format the response
        formatted_relationships = {}
        for other_agent, relationship in relationships.items():
            formatted_relationships[other_agent] = AgentRelationship(
                type=relationship["type"],
                trust_level=relationship["trust_level"],
                interaction_count=relationship["interaction_count"]
            )
        
        return {
            "agent": agent_name,
            "relationships": formatted_relationships
        }
    
    # Define route to find an agent by role or capability
    @app.get("/agent/find")
    async def find_agent(
        role: Optional[str] = Query(None, description="Role to search for"),
        capability: Optional[str] = Query(None, description="Capability to search for"),
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Find an agent by role or capability."""
        if not role and not capability:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either role or capability parameter"
            )
        
        # Look for the registry in any adapter's metadata
        registry = None
        for a in all_adapters:
            if hasattr(a, 'metadata') and a.metadata and 'agent_registry' in a.metadata:
                registry = a.metadata['agent_registry']
                break
        
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent registry not found"
            )
        
        # Find agents matching the criteria
        results = []
        
        if role:
            agent_name = registry.get_agent_by_role(role)
            if agent_name:
                agent_data = registry.agents[agent_name]
                results.append({
                    "name": agent_name,
                    "agent_id": str(agent_data["adapter"].agent_id),
                    "roles": agent_data["roles"],
                    "capabilities": agent_data["capabilities"]
                })
        
        if capability:
            agent_name = registry.get_agent_by_capability(capability)
            if agent_name and not any(r["name"] == agent_name for r in results):
                agent_data = registry.agents[agent_name]
                results.append({
                    "name": agent_name,
                    "agent_id": str(agent_data["adapter"].agent_id),
                    "roles": agent_data["roles"],
                    "capabilities": agent_data["capabilities"]
                })
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agents found with the specified {'role' if role else 'capability'}"
            )
        
        return {"agents": results}
    
    # Register any additional routes
    if additional_routes:
        for route in additional_routes:
            route(app, require_auth)
