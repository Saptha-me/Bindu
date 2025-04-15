"""
API Routes for the Pebble framework.

This module defines all API routes used by the Pebble framework for agent communication.
"""

from typing import Optional, List, Callable, Dict, Any
from uuid import UUID
import time
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status, Body, Query

from pebble.core.protocol import AgentProtocol
from pebble.security.auth import get_auth_token
from pebble.security.keys import create_api_key
from pebble.schemas.models import ActionRequest, ActionResponse, StatusResponse, ListenRequest, ViewRequest

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
    
    