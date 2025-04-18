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
    user_port: int
):
    """Start both JSON-RPC and REST API servers concurrently."""
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
    agent_id: Optional[str] = None,
    supported_methods: List[ProtocolMethod] = None,
    pebble_port: int = 3773,
    user_port: int = 3774,
    host: str = "0.0.0.0",
    protocol_config_path: Optional[str] = None
) -> None:
    """
    Start Pebble protocol servers for an agent.
    
    Args:
        agent: The Agno agent to be served
        agent_id: Unique identifier for the agent
        supported_methods: List of supported protocol methods
        pebble_port: Port for JSON-RPC server
        user_port: Port for REST API server
        host: Host to bind servers to
        protocol_config_path: Path to protocol config file
    """
    supported_methods = supported_methods or []
        
    protocol = PebbleProtocol(protocol_config_path)
    protocol_handler = AgnoProtocolHandler(agent, agent_id)
    
    jsonrpc_app = create_jsonrpc_server(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=supported_methods
    )
    rest_app = create_rest_server(protocol_handler)
    
    print(f"Pebblifying agent with methods: {supported_methods}")
    print(f"Use Ctrl+C to stop the servers")
    
    try:
        asyncio.run(start_servers(jsonrpc_app, rest_app, host, pebble_port, user_port))
    except KeyboardInterrupt:
        print("Servers stopped.")