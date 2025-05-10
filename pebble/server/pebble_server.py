"""
Pebble Server Implementation

This module provides the server implementation for the Pebble protocol.
"""
import asyncio
from typing import List, Optional

import uvicorn
from fastapi import FastAPI

from pebble.core.protocol import PebbleProtocol, ProtocolMethod
from agno.agent import Agent as AgnoAgent

from pebble.server.jsonrpc_server import create_jsonrpc_server
from pebble.server.rest_server import create_rest_server
from pebble.agent.agno_adapter import AgnoProtocolHandler


async def start_servers(
    jsonrpc_app: FastAPI, 
    rest_app: FastAPI, 
    host: str, 
    pebble_port: int, 
    user_port: int,
    hosting_method: Literal["tunnel", "fly", "localhost"] = "localhost"
):
    """Start both JSON-RPC and REST API servers concurrently."""
    # 
    
    if hosting_method == "fly":
        # For Fly.io/Docker deployment, configure the server to listen on 0.0.0.0
        # Configuration matches the Docker container environment variables
        config_pebble = uvicorn.Config(jsonrpc_app, host=host, port=pebble_port, log_level="info")
        pebble_jsonrpc_server = uvicorn.Server(config_pebble)
        
        config_user = uvicorn.Config(rest_app, host=host, port=user_port, log_level="info")
        pebble_rest_server = uvicorn.Server(config_user)
    
        print(f"Starting JSON-RPC server on port {pebble_port} (Docker/Fly hosting)")
        print(f"Starting REST API server on port {user_port} (Docker/Fly hosting)")
        
        await asyncio.gather(
            pebble_jsonrpc_server.serve(),
            pebble_rest_server.serve()
        )
    elif hosting_method == "tunnel":
        print()
    elif hosting_method == "localhost":
        config_pebble = uvicorn.Config(jsonrpc_app, host=host, port=pebble_port, log_level="info")
        pebble_jsonrpc_server = uvicorn.Server(config_pebble)
        
        config_user = uvicorn.Config(rest_app, host=host, port=user_port, log_level="info")
        pebble_rest_server = uvicorn.Server(config_user)
    
        print(f"Starting JSON-RPC server on port {pebble_port}")
        print(f"Starting REST API server on port {user_port}")
        
        await asyncio.gather(
            pebble_jsonrpc_server.serve(),
            pebble_rest_server.serve()
        )


def pebblify(
    agent: AgnoAgent,
    register: bool = False,
    agent_id: Optional[str] = None,
    supported_methods: List[ProtocolMethod] = None,
    #pebble_port: int = 3773,
    user_port: int = 3774,
    host: str = "0.0.0.0",
    protocol_config_path: Optional[str] = None,
    hosting_method: Literal["tunnel", "fly", "localhost"] = "localhost"
) -> None:
    """
    Start Pebble protocol servers for an agent.
    
    Args:
        agent: The Agno agent to be served
        register: Whether to register the agent in the registry
        agent_id: Unique identifier for the agent
        supported_methods: List of supported protocol methods
        pebble_port: Port for JSON-RPC server
        user_port: Port for REST API server
        host: Host to bind servers to
        protocol_config_path: Path to protocol config file
        hosting_method: Method to host the servers
    """
    supported_methods = supported_methods or []
        
    protocol = PebbleProtocol(protocol_config_path)
    protocol_handler = AgnoProtocolHandler(agent, agent_id)
    
    # jsonrpc_app = create_jsonrpc_server(
    #     protocol=protocol,
    #     protocol_handler=protocol_handler,
    #     supported_methods=supported_methods
    # )
    rest_app = create_rest_server(protocol_handler)

    # if register:
    #     _register_agent(agent, agent_id)
    
    print(f"Pebblifying agent with methods: {supported_methods}")
    print(f"Use Ctrl+C to stop the servers")
    
    try:
        # All hosting methods use the same function call with identical parameters
        asyncio.run(start_servers(
            jsonrpc_app=jsonrpc_app,
            rest_app=rest_app,
            host=host,
            pebble_port=pebble_port,
            user_port=user_port,
            hosting_method=hosting_method
        ))
    except KeyboardInterrupt:
        print("Servers stopped.")