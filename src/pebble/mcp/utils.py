"""
Utility functions for MCP integration.

This module provides helper functions for working with MCP in Pebble,
making it easier to set up and configure MCP components.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pebble.core.protocol import AgentProtocol
from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.mcp.client import MCPClientAdapter, MCPCognitiveAdapter
from pebble.mcp.server import MCPServer, MCPResource, MCPTool, MCPPrompt
from pebble.mcp.transport import MCPTransport, StdioTransport, SSETransport, TransportType

logger = logging.getLogger(__name__)


def create_mcp_client(
    transport_type: str = "stdio",
    endpoint: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    name: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> MCPClientAdapter:
    """Create an MCP client adapter.
    
    Args:
        transport_type: The type of transport to use ("stdio" or "sse")
        endpoint: The endpoint for SSE transport (required for "sse")
        agent_id: Unique identifier for the agent (generated if not provided)
        name: Name of the agent
        capabilities: List of capabilities the agent has
        metadata: Additional metadata about the agent
        
    Returns:
        MCPClientAdapter: The MCP client adapter
        
    Raises:
        ValueError: If endpoint is missing for SSE transport
    """
    # Create the appropriate transport
    if transport_type == "stdio":
        transport = StdioTransport()
    elif transport_type == "sse":
        if not endpoint:
            raise ValueError("Endpoint is required for SSE transport")
        transport = SSETransport(endpoint)
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")
    
    # Create and return the client adapter
    return MCPClientAdapter(
        transport=transport,
        agent_id=agent_id,
        name=name,
        capabilities=capabilities,
        metadata=metadata
    )


def create_mcp_cognitive_client(
    transport_type: str = "stdio",
    endpoint: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    name: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    cognitive_capabilities: Optional[List[str]] = None
) -> MCPCognitiveAdapter:
    """Create an MCP cognitive client adapter.
    
    Args:
        transport_type: The type of transport to use ("stdio" or "sse")
        endpoint: The endpoint for SSE transport (required for "sse")
        agent_id: Unique identifier for the agent (generated if not provided)
        name: Name of the agent
        capabilities: List of capabilities the agent has
        metadata: Additional metadata about the agent
        cognitive_capabilities: List of cognitive capabilities the agent has
        
    Returns:
        MCPCognitiveAdapter: The MCP cognitive client adapter
        
    Raises:
        ValueError: If endpoint is missing for SSE transport
    """
    # Create the appropriate transport
    if transport_type == "stdio":
        transport = StdioTransport()
    elif transport_type == "sse":
        if not endpoint:
            raise ValueError("Endpoint is required for SSE transport")
        transport = SSETransport(endpoint)
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")
    
    # Create and return the cognitive client adapter
    return MCPCognitiveAdapter(
        transport=transport,
        agent_id=agent_id,
        name=name,
        capabilities=capabilities,
        metadata=metadata,
        cognitive_capabilities=cognitive_capabilities
    )


def create_mcp_server(
    agent_protocol: Union[AgentProtocol, CognitiveAgentProtocol],
    transport_type: str = "stdio",
    endpoint: Optional[str] = None
) -> MCPServer:
    """Create an MCP server.
    
    Args:
        agent_protocol: The agent protocol to expose as an MCP server
        transport_type: The type of transport to use ("stdio" or "sse")
        endpoint: The endpoint for the server (required for "sse")
        
    Returns:
        MCPServer: The MCP server
        
    Raises:
        ValueError: If endpoint is missing for SSE transport
    """
    # Convert transport type string to enum
    if transport_type == "stdio":
        transport = TransportType.STDIO
    elif transport_type == "sse":
        if not endpoint:
            raise ValueError("Endpoint is required for SSE transport")
        transport = TransportType.SSE
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")
    
    # Create and return the server
    return MCPServer(
        agent_protocol=agent_protocol,
        transport_type=transport,
        endpoint=endpoint
    )


async def connect_to_mcp_server(client: MCPClientAdapter) -> None:
    """Connect an MCP client to an MCP server.
    
    Args:
        client: The MCP client to connect
        
    Raises:
        RuntimeError: If connection fails
    """
    try:
        await client.transport.connect()
        logger.info("Connected to MCP server")
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        raise RuntimeError(f"Failed to connect to MCP server: {e}")


async def start_mcp_server(server: MCPServer) -> None:
    """Start an MCP server.
    
    Args:
        server: The MCP server to start
        
    Raises:
        RuntimeError: If server fails to start
    """
    try:
        await server.start()
        logger.info("MCP server started")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise RuntimeError(f"Failed to start MCP server: {e}")


def register_standard_tools(server: MCPServer) -> None:
    """Register standard tools with an MCP server.
    
    This function registers common tools that are useful for many applications.
    
    Args:
        server: The MCP server to register tools with
    """
    # Register a simple echo tool
    server.register_tool(MCPTool(
        name="echo",
        description="Echo the input text",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to echo"
                }
            },
            "required": ["text"]
        },
        handler=lambda session_id, params: params.get("text", "")
    ))
    
    # Register a tool to get agent information
    async def get_agent_info(session_id, params):
        agent = server.agent_protocol
        return {
            "agent_id": str(agent.agent_id),
            "name": agent.name,
            "framework": agent.framework,
            "capabilities": agent.capabilities
        }
    
    server.register_tool(MCPTool(
        name="get_agent_info",
        description="Get information about the current agent",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=get_agent_info
    ))
    
    # Register cognitive state tool if applicable
    if isinstance(server.agent_protocol, CognitiveAgentProtocol):
        async def get_cognitive_state(session_id, params):
            agent = server.agent_protocol
            return agent.cognitive_state
        
        server.register_tool(MCPTool(
            name="get_cognitive_state",
            description="Get the current cognitive state of the agent",
            parameters={
                "type": "object",
                "properties": {}
            },
            handler=get_cognitive_state
        ))


def register_standard_prompts(server: MCPServer) -> None:
    """Register standard prompts with an MCP server.
    
    This function registers common prompts that are useful for many applications.
    
    Args:
        server: The MCP server to register prompts with
    """
    # Register a basic system prompt
    server.register_prompt(MCPPrompt(
        name="system",
        description="Set the system behavior for the agent",
        template="You are {role}. {instructions}",
        parameters={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "The role the agent should take"
                },
                "instructions": {
                    "type": "string",
                    "description": "Detailed instructions for the agent"
                }
            },
            "required": ["role", "instructions"]
        }
    ))
    
    # Register a cognitive thinking prompt if applicable
    if isinstance(server.agent_protocol, CognitiveAgentProtocol):
        server.register_prompt(MCPPrompt(
            name="cognitive_thinking",
            description="Process cognitive thinking about a situation",
            template=(
                "Based on your current mental state and the provided context, "
                "think carefully about the following: {instruction}\n\n"
                "Consider your current cognitive state: {context}"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "The instruction or situation to think about"
                    },
                    "context": {
                        "type": "object",
                        "description": "The current cognitive context"
                    }
                },
                "required": ["instruction", "context"]
            }
        ))


def register_standard_resources(server: MCPServer) -> None:
    """Register standard resources with an MCP server.
    
    This function registers common resources that are useful for many applications.
    
    Args:
        server: The MCP server to register resources with
    """
    # Register agent information as a resource
    agent = server.agent_protocol
    agent_info = {
        "agent_id": str(agent.agent_id),
        "name": agent.name,
        "framework": agent.framework,
        "capabilities": agent.capabilities
    }
    
    server.register_resource(MCPResource(
        uri="mcp://agent/info",
        content_type="application/json",
        content=agent_info,
        metadata={"description": "Information about the current agent"}
    ))
    
    # Register cognitive capabilities information if applicable
    if isinstance(agent, CognitiveAgentProtocol):
        cognitive_info = {
            "cognitive_capabilities": agent.cognitive_capabilities
        }
        
        server.register_resource(MCPResource(
            uri="mcp://agent/cognitive",
            content_type="application/json",
            content=cognitive_info,
            metadata={"description": "Cognitive capabilities of the agent"}
        ))
