"""Pebbling server main entry point."""

import asyncio
import uuid
from typing import Any, List, Optional, Union

import uvicorn
from agno.agent import Agent as AgnoAgent
from fastapi import FastAPI

from pebbling.agent.agno_adapter import AgnoProtocolHandler
from pebbling.core.protocol import CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod, pebblingProtocol
from pebbling.security.cert_manager import CertificateManager
from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls_middleware import MTLSMiddleware
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.rest_server import create_rest_server
from pebbling.server.server_security import SecurityMiddleware
#from pebbling.utils import register_with_hibiscus_registry


async def start_servers(
    jsonrpc_app: FastAPI,
    rest_app: FastAPI,
    host: str,
    hosting_method: str,
    pebbling_port: int,
    user_port: int,
    ssl_context: Optional[Any] = None,
) -> None:
    """Start the pebbling protocol and user-facing servers.

    Args:
        jsonrpc_app: FastAPI app for agent-to-agent protocol
        rest_app: FastAPI app for user-agent interactions
        host: Host to bind servers to
        hosting_method: Hosting method (local or docker)
        pebbling_port: Port for protocol server
        user_port: Port for user-facing server
        ssl_context: Optional SSL context for secure connections
    """
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
    # Configuration for servers
    pebbling_config = uvicorn.Config(
        jsonrpc_app,
        host=host,
        port=pebbling_port,
        log_level="info",
        ssl_certfile=getattr(ssl_context, "certfile", None) if ssl_context else None,
        ssl_keyfile=getattr(ssl_context, "keyfile", None) if ssl_context else None,
        ssl_ca_certs=getattr(ssl_context, "ca_certs", None) if ssl_context else None,
        ssl_cert_reqs=getattr(ssl_context, "verify_mode", None) if ssl_context else None,
        ssl_version=getattr(ssl_context, "protocol", None) if ssl_context else None,
        ssl_ciphers=":".join(getattr(ssl_context, "ciphers", [])) if ssl_context and hasattr(ssl_context, "ciphers") else None,
    )
    user_config = uvicorn.Config(
        rest_app,
        host=host,
        port=user_port,
        log_level="info",
    )

    # Create server instances
    pebbling_server = uvicorn.Server(pebbling_config)
    user_server = uvicorn.Server(user_config)

    # Override installation signal handlers
    pebbling_server.config.install_signal_handlers = False
    user_server.config.install_signal_handlers = False

    # Start both servers
    await asyncio.gather(
        pebbling_server.serve(),
        user_server.serve(),
    )


def pebblify(
    agent: Any,  # Generic type to support any agent framework
    agent_id: Optional[str] = None,
    supported_methods: Optional[List[Union[str, CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod]]] = None,
    pebbling_port: int = 3773,
    user_port: int = 3774,
    host: str = "localhost",
    protocol_config_path: Optional[str] = None,
    did_manager: Optional[DIDManager] = None,
    enable_security: bool = False,
    enable_mtls: bool = False,
    cert_path: Optional[str] = None,
    register_with_hibiscus: bool = False,
    hibiscus_url: Optional[str] = None,
) -> None:
    """
    Start pebbling protocol servers for an agent.

    Args:
        agent: The agent to be served (from any framework)
        agent_id: Unique identifier for the agent
        supported_methods: List of supported protocol methods
        pebbling_port: Port for JSON-RPC server
        user_port: Port for REST API server
        host: Host to bind servers to
        protocol_config_path: Path to protocol config file
        did_manager: Optional DID manager for secure communication
        enable_security: Whether to enable DID-based security
        enable_mtls: Whether to enable mTLS secure connections
        cert_path: Path for storing certificates (if enable_mtls is True)
        register_with_hibiscus: Whether to register agent with Hibiscus
        hibiscus_url: URL of Hibiscus agent registry
    """
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    supported_methods = supported_methods or []

    # If security is enabled, ensure DID methods are included
    if enable_security:
        security_methods = [
            SecurityProtocolMethod.EXCHANGE_DID,
            SecurityProtocolMethod.VERIFY_IDENTITY,
        ]
        for method in security_methods:
            if method not in supported_methods:
                supported_methods.append(method)
    
    # If mTLS is enabled, ensure certificate methods are included
    if enable_mtls:
        if not enable_security:
            raise ValueError("mTLS requires DID-based security to be enabled")
            
        mtls_methods = [
            SecurityProtocolMethod.EXCHANGE_CERTIFICATES,
            SecurityProtocolMethod.VERIFY_CONNECTION,
        ]
        for method in mtls_methods:
            if method not in supported_methods:
                supported_methods.append(method)

    # Initialize the protocol
    protocol = pebblingProtocol(protocol_config_path)
    
    # Detect the agent framework and use the appropriate adapter
    # Currently only Agno is supported, but this is where you'd add more adapters
    if hasattr(agent, "__module__") and "agno" in agent.__module__:
        protocol_handler = AgnoProtocolHandler(agent, agent_id)
    else:
        # Generic handler or future framework adapters can be added here
        # For now, default to Agno as it's the only one implemented
        protocol_handler = AgnoProtocolHandler(agent, agent_id)
    
    # Initialize security middleware if enabled
    security_middleware = None
    mtls_middleware = None
    ssl_context = None
    
    if enable_security:
        if did_manager is None:
            # Generate a default key path based on agent ID
            key_path = f"{agent_id.replace('-', '_')}_private_key.json"
            did_manager = DIDManager(key_path=key_path)
        
        # Create security middleware
        security_middleware = SecurityMiddleware(
            did_manager=did_manager,
            agent_id=agent_id
        )
        
        print(f"Agent DID: {did_manager.get_did()}")
        
        # Register with Hibiscus if requested
        if register_with_hibiscus and hibiscus_url:
            try:
                asyncio.run(register_with_hibiscus_registry(
                    agent_id=agent_id,
                    did=did_manager.get_did(),
                    did_document=did_manager.get_did_document(),
                    hibiscus_url=hibiscus_url
                ))
                print(f"Registered agent with Hibiscus at {hibiscus_url}")
            except Exception as e:
                print(f"Failed to register with Hibiscus: {e}")
                
    # Initialize mTLS middleware if enabled
    if enable_mtls:
        # Create certificate manager
        cert_manager = CertificateManager(
            did_manager=did_manager,
            cert_path=cert_path
        )
        
        # Create mTLS middleware
        mtls_middleware = MTLSMiddleware(
            did_manager=did_manager,
            cert_manager=cert_manager
        )
        
        # Get SSL context for the server
        ssl_context = mtls_middleware.get_server_ssl_context()
        
        print(f"mTLS security enabled with certificates in: {cert_manager.cert_path}")

    # Create the servers
    jsonrpc_app = create_jsonrpc_server(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=[m.value for m in supported_methods],
        security_middleware=security_middleware,
        mtls_middleware=mtls_middleware
    )
    rest_app = create_rest_server(
        protocol_handler=protocol_handler
    )
    
    # Determine the appropriate hosting method based on host value
    hosting_method = "local"
    if host == "0.0.0.0":
        hosting_method = "docker"
    
    # Start the servers
    asyncio.run(
        start_servers(
            jsonrpc_app=jsonrpc_app,
            rest_app=rest_app,
            host=host,
            hosting_method=hosting_method,
            pebbling_port=pebbling_port,
            user_port=user_port,
            ssl_context=ssl_context if enable_mtls else None,
        )
    )
