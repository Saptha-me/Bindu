"""
Pebblify - Easy deployment for Agents

This module provides simple deployment functionality for various agent types,
including Agno, Smol, and Crew agents.
"""

import asyncio
import logging
import uvicorn
import uuid
from typing import Optional, Union, Dict, Any, Type
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .constants import AgentType
from .api.handlers.agno_handler import AgnoAgentHandler
from .api.api_server import PebbleServer
from .api.routers.agent_router import create_agent_router, get_agent_wrapper

# Import protocol system components
from .protocol.coordinator import ProtocolCoordinator
from .protocol.protocol import Protocol
from .protocol.adapters.agno_adapter import AgnoAdapter
from .protocol.adapters.smol_adapter import SmolAdapter
from .protocol.adapters.crew_adapter import CrewAdapter

# Set up logging
logger = logging.getLogger(__name__)

class AgentDeployer:
    """Class for deploying agents as API endpoints."""
    
    def __init__(self, agent: Any, agent_type: str = AgentType.AGNO, host: str = "0.0.0.0", port: int = 8000):
        """Initialize the deployer with an agent.
        
        Args:
            agent: The agent to deploy
            agent_type: The type of agent (default: AgentType.AGNO)
            host: Host to bind the server to (default: "0.0.0.0")
            port: Port to bind the server to (default: 8000)
        """
        self.agent = agent
        self.agent_type = agent_type
        self.host = host
        self.port = port
        
        # Initialize the protocol coordinator for agent communication
        self.coordinator = ProtocolCoordinator()
        
        # Register the agent with the coordinator to get its adapter
        self.agent_id = self.coordinator.register_agent(agent)
        self.adapter = self.coordinator.agents.get(self.agent_id)
        self.app = FastAPI(
            title="Pebble Agent API",
            description="API for interacting with deployed agents",
            docs_url="/docs"
        )
        
        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up exception handlers
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": str(exc.detail)},
            )
        
        # Set up routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up the API routes for the agent."""
        # Verify the agent was properly registered with the protocol system
        if not self.agent_id:
            raise ValueError("Agent could not be registered with the protocol system")
            
        if not self.adapter:
            raise ValueError("No adapter found for the agent")
        
        # Use agent's adapter to ensure consistent properties
        agent_properties = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": getattr(self.agent, "name", "Unnamed Agent"),
            "description": getattr(self.agent, "description", ""),
        }
        
        logger.info(f"Deploying agent: {agent_properties}")
            
        # Create a handler for the agent based on its type that uses the protocol adapter
        if self.agent_type == AgentType.AGNO:
            handler = AgnoAgentHandler(self.agent, self.adapter)
        else:
            raise ValueError(f"Unsupported agent type: {self.agent_type}")
        
        # Create a router for the agent
        router = create_agent_router()
        
        # Register the agent handler as a dependency
        self.app.dependency_overrides[get_agent_wrapper] = lambda: handler
        
        # Include the router in the app
        self.app.include_router(router)
    
    def run(self):
        """Run the API server."""
        logger.info(f"Starting agent API server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)


def _ensure_agent_has_basic_attributes(agent: Any):
    """Ensure agent has basic attributes for deployment.
    
    This performs minimal validation since the protocol system will handle
    agent_id and other properties.
    
    Args:
        agent: The agent to validate
        
    Returns:
        The validated agent with basic attributes set
    
    Raises:
        ValueError: If the agent is invalid or missing core attributes
    """
    # Check if agent is None
    if agent is None:
        raise ValueError("Cannot deploy None as an agent")
    
    # Check if agent has a name
    if not hasattr(agent, "name") or agent.name is None or agent.name.strip() == "":
        raise ValueError("Agent must have a valid name attribute")

    # Check if agent has a description
    if not hasattr(agent, "description") or agent.description is None or agent.description.strip() == "":
        raise ValueError("Agent must have a valid description attribute")
    
    # Name is the minimum required attribute, as the protocol system 
    # will handle agent_id and other required properties
    logger.info(f"Basic agent validation complete for agent: {agent.name}")
    return agent


def deploy(agent: Any, agent_type: str = AgentType.AGNO, host: str = "0.0.0.0", port: int = 8000):
    """Deploy an agent as an API endpoint.
    
    Args:
        agent: The agent to deploy
        agent_type: The type of agent (default: AgentType.AGNO)
        host: Host to bind the server to (default: "0.0.0.0")
        port: Port to bind the server to (default: 8000)
        
    Raises:
        ValueError: If the agent is invalid or missing required attributes
    """
    # Basic validation of agent attributes
    validated_agent = _ensure_agent_has_basic_attributes(agent)
    
    # Create and run the deployer - this will register the agent with the protocol system
    deployer = AgentDeployer(validated_agent, agent_type, host, port)
    deployer.run()
