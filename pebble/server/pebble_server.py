"""
Pebble Server Implementation

This module provides a framework-agnostic server implementation for the Pebble protocol.
It includes both a JSON-RPC server for agent-to-agent communication and a REST API server
for user interaction.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Type, Union
import uuid

from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
    """
    Start both JSON-RPC and REST API servers.
    
    Args:
        jsonrpc_app: The JSON-RPC app
        rest_app: The REST API app
        host: The host to bind to
        pebble_port: Port for the JSON-RPC server
        user_port: Port for the REST API server
    """
    # Configure servers
    config_pebble = uvicorn.Config(jsonrpc_app, host=host, port=pebble_port, log_level="info")
    pebble_jsonrpc_server = uvicorn.Server(config_pebble)
    
    config_user = uvicorn.Config(rest_app, host=host, port=user_port, log_level="info")
    pebble_rest_server = uvicorn.Server(config_user)
    
    print(f"Starting JSON-RPC server on port {pebble_port}")
    print(f"Starting REST API server on port {user_port}")
    
    # Use asyncio.gather to run both servers concurrently
    await asyncio.gather(
        pebble_jsonrpc_server.serve(),
        pebble_rest_server.serve()
    )

def pebblify(
    agent: AgnoAgent,
    agent_id: Optional[str],
    supported_methods: List[ProtocolMethod],
    pebble_port: int = 3773,
    user_port: int = 3774,
    host: str = "0.0.0.0",
    protocol_config_path: Optional[str] = None
) -> None:
    """
    Start Pebble protocol servers for an agent.
    
    Args:
        agent: The Agno agent to be served via Pebble protocol
        agent_id: Unique identifier for the agent (must be unique across the network)
        supported_methods: List of supported protocol methods
        pebble_port: Port for the JSON-RPC server
        user_port: Port for the REST API server
        host: Host to bind the servers to
        protocol_config_path: Path to the protocol config file
    """
    # Create protocol instance
    protocol = PebbleProtocol(protocol_config_path)
    
    # Create shared protocol handler
    protocol_handler = AgnoProtocolHandler(agent, agent_id)
    
    # Create servers
    jsonrpc_app = create_jsonrpc_server(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=supported_methods
    )
    rest_app = create_rest_server(protocol_handler)
    
    # Print info
    print(f"Pebblifying agent with methods: {supported_methods}")
    print(f"Use Ctrl+C to stop the servers")
    
    try:
        # Run the servers
        asyncio.run(start_servers(jsonrpc_app, rest_app, host, pebble_port, user_port))
    except KeyboardInterrupt:
        print("Servers stopped.")