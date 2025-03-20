"""
API Routes for the Pebble framework.

This module defines all API routes used by the Pebble framework for agent communication.
"""

from typing import Optional, List, Callable
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status

from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, StatusResponse
from pebble.security.auth import get_auth_token
from pebble.security.keys import create_api_key


def register_routes(
    app: FastAPI, 
    adapter: AgentProtocol, 
    require_auth: bool = True,
    additional_routes: Optional[List[Callable]] = None
) -> None:
    """Register all routes for the Pebble API.
    
    Args:
        app: The FastAPI application
        adapter: The agent protocol adapter
        require_auth: Whether authentication is required
        additional_routes: Additional route handlers to register
    """
    
    # Define route for agent status
    @app.get("/agent/status", response_model=StatusResponse)
    async def get_agent_status(
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Get the current status of the agent."""
        return adapter.get_status()
    
    # Define route for agent action
    @app.post("/agent/action", response_model=ActionResponse)
    async def post_agent_action(
        request: ActionRequest,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Process an action with the agent."""
        return adapter.process_action(request)
    
    # Define route to generate a new API key (admin only)
    @app.post("/admin/generate-api-key")
    async def generate_api_key(
        expire_days: int = 365,
        token: str = Depends(get_auth_token) if require_auth else None
    ):
        """Generate a new API key."""
        new_api_key = create_api_key(expire_days=expire_days)
        return {"api_key": new_api_key}
    
    # Register additional routes if provided
    if additional_routes:
        for route_func in additional_routes:
            app.add_api_route(
                f"/{route_func.__name__}",
                route_func,
                methods=["POST"]
            )
