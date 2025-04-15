"""
Core deployment functionality for the Pebble framework.

This module provides functions for deploying agents via the Pebble protocol.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from fastapi import FastAPI

from pebble.adapters import AgnoAdapter
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
    agent: Union[Any, List[Any]],
    agent_id: Optional[Union[UUID, List[UUID]]] = None,
    name: Optional[Union[str, List[str]]] = None,
    metadata: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    cors_origins: List[str] = ["*"],
    enable_docs: bool = True,
    require_auth: bool = True,
    autostart: bool = True
) -> Union[FastAPI, List[AgentProtocol]]:
    """Deploy one or more agents via the Pebble protocol.
    
    Args:
        agent: A single agent or list of agents to deploy
        agent_id: Unique identifier(s) for the agent(s)
        name: Name(s) of the agent(s)
        metadata: Additional metadata for the agent(s)
        host: Host address to bind the server to
        port: Port to run the server on
        cors_origins: Allowed CORS origins
        enable_docs: Whether to enable API documentation
        require_auth: Whether to require authentication
        autostart: Whether to automatically start the server
        
    Returns:
        Union[FastAPI, List[AgentProtocol]]: The FastAPI app if autostart=False, otherwise the list of adapters
    """
    # Create the deployment configuration
    config = DeploymentConfig(
        host=host,
        port=port,
        cors_origins=cors_origins,
        enable_docs=enable_docs,
        require_auth=require_auth
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
