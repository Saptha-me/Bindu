"""Pebbling server main entry point."""

import asyncio
import uuid
import os
from typing import Any, List, Optional, Union, Dict, Tuple

import uvicorn
from fastapi import FastAPI
from loguru import logger

from pebbling.agent.agno_adapter import AgnoProtocolHandler
from pebbling.core.protocol import CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod, pebblingProtocol
from pebbling.security.cert_manager import CertificateManager
from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls_middleware import MTLSMiddleware
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.rest_server import create_rest_server
from pebbling.server.server_security import SecurityMiddleware


def _configure_logger() -> None:
    """Configure loguru logger for the pebbling server."""
    # Remove default logger
    logger.remove()
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Add file logger with rotation
    logger.add(
        "logs/pebbling_server.log",
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | {extra}"
    )
    
    # Add console logger for development
    logger.add(
        lambda msg: print(msg),
        level="DEBUG",
        colorize=True
    )


def _prepare_server_display() -> str:
    """Prepare the colorful ASCII display for the server."""
    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        
        console = Console(record=True)

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
        
        display_panel = Panel.fit(
            Text(logo, style="bold magenta")
            + "\n\n"
            + version_info
            + "\n\n"
            + Text(
                "🐧 Pebbling - A Protocol Framework for Agent to Agent Communication",
                style="bold cyan italic",
            ),
            title="[bold rainbow]🐧 Pebbling Protocol Framework[/bold rainbow]",
            border_style="bright_blue",
            box=box.DOUBLE,
        )
        
        return console.export_text(display_panel)
    except ImportError:
        return "🐧 Pebbling Protocol Framework v0.1.0"


def _create_uvicorn_config(
    app: FastAPI,
    host: str,
    port: int, 
    ssl_context: Optional[Any] = None
) -> uvicorn.Config:
    """Create a uvicorn server configuration.
    
    Args:
        app: FastAPI application
        host: Host to bind server to
        port: Port to bind server to
        ssl_context: Optional SSL context for secure connections
        
    Returns:
        Uvicorn server configuration
    """
    return uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        ssl_certfile=getattr(ssl_context, "certfile", None) if ssl_context else None,
        ssl_keyfile=getattr(ssl_context, "keyfile", None) if ssl_context else None,
        ssl_ca_certs=getattr(ssl_context, "ca_certs", None) if ssl_context else None,
        ssl_cert_reqs=getattr(ssl_context, "verify_mode", None) if ssl_context else None,
        ssl_version=getattr(ssl_context, "protocol", None) if ssl_context else None,
        ssl_ciphers=":".join(getattr(ssl_context, "ciphers", [])) if ssl_context and hasattr(ssl_context, "ciphers") else None,
    )


async def start_servers(
    jsonrpc_app: FastAPI,
    rest_app: FastAPI,
    host: str,
    hosting_method: str,
    port: int,
    ssl_context: Optional[Any] = None,
) -> None:
    """Start the pebbling protocol and user-facing servers.

    Args:
        jsonrpc_app: FastAPI app for agent-to-agent protocol
        rest_app: FastAPI app for user-agent interactions
        host: Host to bind servers to
        hosting_method: Hosting method (local or docker)
        port: Port for protocol server
        ssl_context: Optional SSL context for secure connections
    """
    logger.info(f"Starting servers with hosting method: {hosting_method}")
    
    # Display server information
    server_display = _prepare_server_display()
    print(server_display)
    
    # Create a single combined FastAPI app
    combined_app = FastAPI()
    
    # Mount both apps as sub-applications with different path prefixes
    combined_app.mount("/pebble", jsonrpc_app)
    combined_app.mount("/human", rest_app)
    
    # Additional server information
    hosting_info = f"Hosting method: {hosting_method}"
    server_info = f"Server running on: {host}:{port}"
    jsonrpc_info = f"JSON-RPC endpoint: /pebble"
    rest_info = f"REST API endpoint: /human"
    
    logger.info(hosting_info)
    logger.info(server_info)
    logger.info(jsonrpc_info)
    logger.info(rest_info)

    # Create server configurations
    config = _create_uvicorn_config(
        app=combined_app,
        host=host,
        port=port,
        ssl_context=ssl_context
    )

    # Create server instances
    server = uvicorn.Server(config)

    # Override installation signal handlers
    server.config.install_signal_handlers = False

    # Start both servers
    try:
        logger.debug("Starting server tasks")
        asyncio.run(server.serve())
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
        raise


def _setup_security_methods(
    supported_methods: List[Union[str, CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod]],
    enable_security: bool,
    enable_mtls: bool
) -> List[Union[str, CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod]]:
    """Add security methods to the list of supported methods if security is enabled.
    
    Args:
        supported_methods: List of supported protocol methods
        enable_security: Whether to enable DID-based security
        enable_mtls: Whether to enable mTLS secure connections
        
    Returns:
        Updated list of supported methods
    """
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
                
    return supported_methods


def _setup_protocol_handler(
    agent: Any,
    agent_id: str
) -> Any:
    """Set up the appropriate protocol handler based on the agent framework.
    
    Args:
        agent: The agent to be served
        agent_id: Unique identifier for the agent
        
    Returns:
        Protocol handler for the agent
    """
    # Detect the agent framework and use the appropriate adapter
    if hasattr(agent, "__module__") and "agno" in agent.__module__:
        logger.debug(f"Setting up AgnoProtocolHandler for agent {agent_id}")
        return AgnoProtocolHandler(agent, agent_id)
    else:
        # Generic handler or future framework adapters can be added here
        # For now, default to Agno as it's the only one implemented
        logger.debug(f"Using default AgnoProtocolHandler for agent {agent_id}")
        return AgnoProtocolHandler(agent, agent_id)


def _setup_security_middleware(
    enable_security: bool,
    agent_id: str,
    did_manager: Optional[DIDManager]
) -> Tuple[Optional[SecurityMiddleware], Optional[DIDManager]]:
    """Set up security middleware if security is enabled.
    
    Args:
        enable_security: Whether to enable DID-based security
        agent_id: Unique identifier for the agent
        did_manager: Optional DID manager for secure communication
        
    Returns:
        Tuple of (security_middleware, did_manager)
    """
    if not enable_security:
        return None, did_manager
    
    if did_manager is None:
        # Generate a default key path based on agent ID
        key_path = f"{agent_id.replace('-', '_')}_private_key.json"
        did_manager = DIDManager(key_path=key_path)
    
    # Create security middleware
    security_middleware = SecurityMiddleware(
        did_manager=did_manager,
        agent_id=agent_id
    )
    
    logger.info(f"Agent DID: {did_manager.get_did()}")
    
    return security_middleware, did_manager


def _setup_mtls_middleware(
    enable_mtls: bool,
    did_manager: Optional[DIDManager],
    cert_path: Optional[str]
) -> Tuple[Optional[MTLSMiddleware], Optional[Any]]:
    """Set up mTLS middleware if mTLS is enabled.
    
    Args:
        enable_mtls: Whether to enable mTLS secure connections
        did_manager: DID manager for secure communication
        cert_path: Path for storing certificates
        
    Returns:
        Tuple of (mtls_middleware, ssl_context)
    """
    if not enable_mtls:
        return None, None
    
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
    
    logger.info(f"mTLS security enabled with certificates in: {cert_manager.cert_path}")
    
    return mtls_middleware, ssl_context


def pebblify(
    agent: Any,  # Generic type to support any agent framework
    agent_id: Optional[str] = None,
    supported_methods: Optional[List[Union[str, CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod]]] = None,
    port: int = 3773,
    host: str = "localhost",
    protocol_config_path: Optional[str] = None,
    did_manager: Optional[DIDManager] = None,
    enable_security: bool = False,
    enable_mtls: bool = False,
    cert_path: Optional[str] = None
) -> None:
    """
    Start pebbling protocol servers for an agent.

    Args:
        agent: The agent to be served (from any framework)
        agent_id: Unique identifier for the agent
        supported_methods: List of supported protocol methods
        port: Port for pebbling server
        host: Host to bind servers to
        protocol_config_path: Path to protocol config file
        did_manager: Optional DID manager for secure communication
        enable_security: Whether to enable DID-based security
        enable_mtls: Whether to enable mTLS secure connections
        cert_path: Path for storing certificates (if enable_mtls is True)
    """
    # Configure logging
    _configure_logger()
    logger.info(f"Starting pebbling server for agent {agent_id}")
    
    # Generate agent ID if not provided
    if agent_id is None:
        agent_id = str(uuid.uuid4())
        logger.debug(f"Agent ID not provided, generated: {agent_id}")

    # Set up supported methods
    supported_methods = supported_methods or []
    supported_methods = _setup_security_methods(supported_methods, enable_security, enable_mtls)
    logger.debug(f"Set up {len(supported_methods)} supported methods")

    # Initialize the protocol
    protocol = pebblingProtocol(protocol_config_path)
    
    # Set up protocol handler
    protocol_handler = _setup_protocol_handler(agent, agent_id)
    
    # Set up security middleware if enabled
    security_middleware, did_manager = _setup_security_middleware(
        enable_security, 
        agent_id, 
        did_manager
    )
    
    # Set up mTLS middleware if enabled
    mtls_middleware, ssl_context = _setup_mtls_middleware(
        enable_mtls,
        did_manager,
        cert_path
    )

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
    
    logger.info(f"Server initialization complete, starting servers")
    
    # Start the servers
    asyncio.run(
        start_servers(
            jsonrpc_app=jsonrpc_app,
            rest_app=rest_app,
            host=host,
            hosting_method=hosting_method,
            port=port,
            ssl_context=ssl_context if enable_mtls else None,
        )
    )