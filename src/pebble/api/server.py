"""
Server configuration and startup for the Pebble framework.

This module provides utilities for configuring and starting the FastAPI server
for agent deployment.
"""

from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pebble.core.protocol import AgentProtocol
from pebble.api.routes import register_routes
from pebble.schemas.models import DeploymentConfig


def create_app(
    adapter: AgentProtocol,
    config: Optional[DeploymentConfig] = None
) -> FastAPI:
    """Create and configure a FastAPI application for agent deployment.
    
    Args:
        adapter: The agent protocol adapter
        config: Configuration for deployment
        
    Returns:
        FastAPI: The configured FastAPI application
    """
    # Use default config if none provided
    if config is None:
        config = DeploymentConfig()
    
    # Create the FastAPI app
    app = FastAPI(
        title=f"Pebble Agent: {adapter.name}",
        description=f"Pebble API for interacting with the '{adapter.name}' agent",
        version="0.1.0",
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register the API routes
    register_routes(
        app=app,
        adapter=adapter,
        require_auth=config.require_auth
    )
    
    return app


def start_server(
    app: FastAPI,
    config: Optional[DeploymentConfig] = None
) -> None:
    """Start the FastAPI server.
    
    Args:
        app: The FastAPI application
        config: Configuration for deployment
    """
    import uvicorn
    
    # Use default config if none provided
    if config is None:
        config = DeploymentConfig()
    
    # Start the server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port
    )
