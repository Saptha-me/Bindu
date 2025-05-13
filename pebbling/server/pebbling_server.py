"""Pebbling server main entry point."""

import asyncio
import uuid
from typing import List, Literal, Optional

import uvicorn
from agno.agent import Agent as AgnoAgent
from fastapi import FastAPI

from pebbling.agent.agno_adapter import AgnoProtocolHandler
from pebbling.core.protocol import ProtocolMethod, pebblingProtocol
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.rest_server import create_rest_server


async def start_servers(
    jsonrpc_app: FastAPI,
    rest_app: FastAPI,
    host: str,
    pebbling_port: int,
    user_port: int,
    hosting_method: Literal["docker", "tunnel", "fly", "localhost"] = "localhost",
):
    """Start both JSON-RPC and REST API servers concurrently."""
    # Import rich components for pretty display
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    # Create a stylish ASCII art logo with penguin emoji
    logo = """
    ██████╗ ███████╗██████╗ ██████╗ ██╗     ██╗███╗   ██╗ ██████╗
    ██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     ██║████╗  ██║██╔════╝
    ██████╔╝█████╗  ██████╔╝██████╔╝██║     ██║██╔██╗ ██║██║  ███╗
    ██╔═══╝ ██╔══╝  ██╔══██╗██╔══██╗██║     ██║██║╚██╗██║██║   ██║
    ██║     ███████╗██████╔╝██████╔╝███████╗██║██║ ╚████║╚██████╔╝
    ╚═╝     ╚══════╝╚═════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝
    """

    version_info = Text("v" + "0.1.0", style="bright_white")
    hosting_text = Text(f"Hosting method: {hosting_method}", style="bright_cyan")
    jsonrpc_text = Text(f"JSON-RPC server: {host}:{pebbling_port}", style="bright_green")
    rest_text = Text(f"REST API server: {host}:{user_port}", style="bright_yellow")

    # Display the colorful logo and server information
    console.print(
        Panel.fit(
            Text(logo, style="bold magenta")
            + "\n\n"
            + version_info
            + "\n"
            + hosting_text
            + "\n"
            + jsonrpc_text
            + "\n"
            + rest_text
            + "\n\n"
            + Text(
                "🐧 Pebbling - A Protocol Framework for Agent to Agent Communication",
                style="bold cyan italic",
            ),
            title="[bold rainbow]🐧 Pebbling Protocol Framework[/bold rainbow]",
            border_style="bright_blue",
            box=box.DOUBLE,
        )
    )

    config_pebbling = uvicorn.Config(jsonrpc_app, host=host, port=pebbling_port, log_level="info")
    pebbling_jsonrpc_server = uvicorn.Server(config_pebbling)

    config_user = uvicorn.Config(rest_app, host=host, port=user_port, log_level="info")
    pebbling_rest_server = uvicorn.Server(config_user)

    # Server startup is now handled by the async gather
    await asyncio.gather(pebbling_jsonrpc_server.serve(), pebbling_rest_server.serve())


def pebblify(
    agent: AgnoAgent,
    agent_id: Optional[str] = None,
    supported_methods: Optional[List[ProtocolMethod]] = None,
    pebbling_port: int = 3773,
    user_port: int = 3774,
    host: str = "localhost",
    protocol_config_path: Optional[str] = None,
) -> None:
    """
    Start pebbling protocol servers for an agent.

    Args:
        agent: The Agno agent to be served
        agent_id: Unique identifier for the agent
        supported_methods: List of supported protocol methods
        pebbling_port: Port for JSON-RPC server
        user_port: Port for REST API server
        host: Host to bind servers to
        protocol_config_path: Path to protocol config file
        hosting_method: Method to host the servers
    """
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    supported_methods = supported_methods or []

    protocol = pebblingProtocol(protocol_config_path)
    protocol_handler = AgnoProtocolHandler(agent, agent_id)

    jsonrpc_app = create_jsonrpc_server(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=[m.value for m in supported_methods],
    )
    rest_app = create_rest_server(protocol_handler)

    # if register:
    #     _register_agent(agent, agent_id)

    print(f"Pebblifying agent with methods: {supported_methods}")
    print("Use Ctrl+C to stop the servers")

    try:
        # All hosting methods use the same function call with identical parameters
        asyncio.run(
            start_servers(
                jsonrpc_app=jsonrpc_app,
                rest_app=rest_app,
                host=host,
                pebbling_port=pebbling_port,
                user_port=user_port,
            )
        )
    except KeyboardInterrupt:
        print("Servers stopped.")
