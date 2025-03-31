"""
Core deployment functionality for the Pebble framework.

This module provides functions for deploying agents via the Pebble protocol.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from fastapi import FastAPI

from pebble.adapters import get_adapter_for_agent
from pebble.api.server import create_app, start_server
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import DeploymentConfig, DeploymentMode
from pebble.deployment import register_with_router, create_docker_deployment

def pebblify(
    agent: Union[Any, List[Any]],
    agent_id: Optional[Union[UUID, List[UUID]]] = None,
    name: Optional[Union[str, List[str]]] = None,
    metadata: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    config: Optional[DeploymentConfig] = None,
    # For backwards compatibility
    host: str = "0.0.0.0",
    port: int = 8000,
    cors_origins: List[str] = ["*"],
    enable_docs: bool = True,
    require_auth: bool = True,
    autostart: bool = True
) -> Union[FastAPI, List[AgentProtocol], str]:
    """Deploy one or more agents via the Pebble protocol.
    
    This function provides multiple deployment options:
    1. LOCAL: Run a local FastAPI server (default)
    2. REGISTER: Deploy and register with an external router
    3. DOCKER: Create Docker artifacts for containerized deployment
    
    Args:
        agent: A single agent or list of agents to deploy
        agent_id: Unique identifier(s) for the agent(s)
        name: Name(s) of the agent(s)
        metadata: Additional metadata for the agent(s)
        config: Comprehensive deployment configuration
        host: Host address to bind the server to (if not using config)
        port: Port to run the server on (if not using config)
        cors_origins: Allowed CORS origins (if not using config)
        enable_docs: Whether to enable API documentation (if not using config)
        require_auth: Whether to require authentication (if not using config)
        autostart: Whether to automatically start the server (LOCAL mode only)
        
    Returns:
        For LOCAL mode: The FastAPI app if autostart=False, otherwise the list of adapters
        For REGISTER mode: The registration URL
        For DOCKER mode: Path to the Docker artifacts
    """
    # Create the deployment configuration if not provided
    if config is None:
        config = DeploymentConfig(
            host=host,
            port=port,
            cors_origins=cors_origins,
            enable_docs=enable_docs,
            require_auth=require_auth,
            mode=DeploymentMode.LOCAL
        )
    
    # Convert single agent to list for consistent handling
    agents_list = [agent] if not isinstance(agent, list) else agent
    agent_ids = [agent_id] * len(agents_list) if not isinstance(agent_id, list) else agent_id
    names = [name] * len(agents_list) if not isinstance(name, list) else name
    metadatas = [metadata] * len(agents_list) if not isinstance(metadata, list) else metadata
    
    # Fill in None values with appropriate defaults
    if agent_ids is None or len(agent_ids) < len(agents_list):
        agent_ids = [None] * len(agents_list)
    if names is None or len(names) < len(agents_list):
        names = [None] * len(agents_list)
    if metadatas is None or len(metadatas) < len(agents_list):
        metadatas = [None] * len(agents_list)
    
    # Get adapters for all agents
    adapters = []
    for i, agent_instance in enumerate(agents_list):
        try:
            adapter = get_adapter_for_agent(
                agent=agent_instance,
                agent_id=agent_ids[i] if i < len(agent_ids) else None,
                name=names[i] if i < len(names) else None,
                metadata=metadatas[i] if i < len(metadatas) else None
            )
            adapters.append(adapter)
        except Exception as e:
            print(f"Error creating adapter for agent {i}: {str(e)}")
    
    if not adapters:
        raise ValueError("No valid adapters could be created from the provided agents")
    
    # Handle different deployment modes
    if config.mode == DeploymentMode.LOCAL:
        # Use the first adapter as the primary one but register routes for all adapters
        primary_adapter = adapters[0]
        additional_adapters = adapters[1:] if len(adapters) > 1 else None
        
        # Create the FastAPI app with all adapters
        app = create_app(
            adapter=primary_adapter, 
            config=config,
            additional_adapters=additional_adapters
        )
        
        # Start the server if requested
        if autostart:
            start_server(app=app, config=config)
            return adapters
        else:
            return app
            
    elif config.mode == DeploymentMode.REGISTER:
        if not config.router_config:
            raise ValueError("Router configuration is required for REGISTER mode")
            
        # Create server app
        primary_adapter = adapters[0]
        additional_adapters = adapters[1:] if len(adapters) > 1 else None
        app = create_app(
            adapter=primary_adapter, 
            config=config,
            additional_adapters=additional_adapters
        )
        
        # Register with router service and start server
        registration_url = register_with_router(
            app=app,
            adapters=adapters,
            config=config
        )
        
        # Start the server
        start_server(app=app, config=config)
        
        return registration_url
        
    elif config.mode == DeploymentMode.DOCKER:
        if not config.docker_config:
            raise ValueError("Docker configuration is required for DOCKER mode")
            
        # Create docker artifacts
        docker_path = create_docker_deployment(
            adapters=adapters,
            config=config
        )
        
        return docker_path