"""
Core deployment functionality for the Pebble framework.

This module provides functions for deploying agents via the Pebble protocol.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from fastapi import FastAPI

from pebble.adapters import AgnoAdapter, CrewAdapter
from pebble.api.server import create_app, start_server
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import DeploymentConfig


def get_adapter_for_agent(
    agent: Any,
    agent_id: Optional[UUID] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AgentProtocol:
    """Get the appropriate adapter for an agent.
    
    Args:
        agent: The agent to adapt
        agent_id: Unique identifier for the agent
        name: Name of the agent
        metadata: Additional metadata for the agent
        
    Returns:
        AgentProtocol: The agent protocol adapter
        
    Raises:
        ValueError: If the agent type is not supported
    """
    # Import agent frameworks here to avoid dependency issues
    try:
        from agno.agent import Agent as AgnoAgent
        has_agno = True
    except ImportError:
        has_agno = False
    
    try:
        from crewai.agent import Agent as CrewAgent
        has_crew = True
    except ImportError:
        has_crew = False
    
    # Check agent type and create appropriate adapter
    if has_agno and isinstance(agent, AgnoAgent):
        return AgnoAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    if has_crew and isinstance(agent, CrewAgent):
        return CrewAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    # If no adapter found, look at the class hierarchy
    if has_agno and inspect.isclass(type(agent)) and issubclass(type(agent), AgnoAgent):
        return AgnoAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    if has_crew and inspect.isclass(type(agent)) and issubclass(type(agent), CrewAgent):
        return CrewAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    # If still no match, raise an error
    raise ValueError(
        f"Unsupported agent type: {type(agent).__name__}. "
        "Currently supported frameworks: Agno, CrewAI"
    )


def deploy(
    agent: Any,
    agent_id: Optional[UUID] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    cors_origins: List[str] = ["*"],
    enable_docs: bool = True,
    require_auth: bool = True,
    autostart: bool = True
) -> Union[FastAPI, AgentProtocol]:
    """Deploy an agent via the Pebble protocol.
    
    Args:
        agent: The agent to deploy
        agent_id: Unique identifier for the agent
        name: Name of the agent
        metadata: Additional metadata for the agent
        host: Host address to bind the server to
        port: Port to run the server on
        cors_origins: Allowed CORS origins
        enable_docs: Whether to enable API documentation
        require_auth: Whether to require authentication
        autostart: Whether to automatically start the server
        
    Returns:
        Union[FastAPI, AgentProtocol]: The FastAPI app if autostart=False, otherwise the adapter
    """
    # Create the deployment configuration
    config = DeploymentConfig(
        host=host,
        port=port,
        cors_origins=cors_origins,
        enable_docs=enable_docs,
        require_auth=require_auth
    )
    
    # Get the appropriate adapter for the agent
    adapter = get_adapter_for_agent(
        agent=agent,
        agent_id=agent_id,
        name=name,
        metadata=metadata
    )
    
    # Create the FastAPI app
    app = create_app(adapter=adapter, config=config)
    
    # Start the server if requested
    if autostart:
        start_server(app=app, config=config)
        return adapter
    else:
        return app
