"""Pebbling server main entry point."""

import uuid
import ssl
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union

from aiohttp import web
from loguru import logger

from pebbling.core.protocol import CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod, pebblingProtocol
from pebbling.server.jsonrpc_server import create_jsonrpc_server
from pebbling.server.rest_server import create_rest_server
from pebbling.security.did_manager import DIDManager

# Import modularized components
from pebbling.server.logging import configure_logger
from pebbling.server.display import prepare_server_display
from pebbling.server.protocol_handler import setup_protocol_handler
from pebbling.server.security.middleware_setup import (
    setup_security_methods,
    setup_security_middleware,
    setup_mtls_middleware,
    extract_did_manager
)
from pebbling.server.security.hibiscus_registry import register_with_hibiscus_registry
from pebbling.server.security.sheldon_service import setup_sheldon_certificates
from pebbling.server.server_utils import start_servers


async def pebblify(
    agent: Any,
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
    hibiscus_api_key: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    agent_capabilities: Optional[List[Dict[str, str]]] = None,
    agent_domains: Optional[List[str]] = None,
    agent_tags: Optional[List[str]] = None,
    agent_metadata: Optional[Dict[str, Any]] = None,
    agent_author: Optional[str] = None,
    agent_version: str = "1.0.0",
    sheldon_ca_url: Optional[str] = None
) -> None:
    """
    Start pebbling protocol servers for an agent.
    
    This is the main entry point for starting a Pebbling agent server.
    The function coordinates the setup of all required components and
    starts the server with the specified configuration.
    """
    # Configure logging
    configure_logger()
    logger.info(f"Starting pebbling server for agent {agent_id}")
    
    # Generate agent ID if not provided
    if agent_id is None:
        agent_id = str(uuid.uuid4())
        logger.debug(f"Agent ID not provided, generated: {agent_id}")

    # Set up supported methods
    supported_methods = supported_methods or []
    supported_methods = setup_security_methods(supported_methods, enable_security, enable_mtls)
    
    # Initialize protocol
    protocol = pebblingProtocol(protocol_config_path)
    
    # Set up protocol handler
    protocol_handler = setup_protocol_handler(agent, agent_id)
    
    # Set up security middleware if enabled
    security_middleware, did_manager = setup_security_middleware(
        enable_security, 
        agent_id, 
        did_manager
    )
    
    # Register agent DID with Hibiscus (if enabled)
    if register_with_hibiscus:
        # Try to get DID manager if not provided
        if did_manager is None:
            did_manager = extract_did_manager(agent)
            
        # Register with Hibiscus
        endpoint = f"{'https' if enable_mtls else 'http'}://{host}:{pebbling_port}"
        await register_with_hibiscus_registry(
            did_manager=did_manager,
            agent=agent,
            agent_id=agent_id,
            hibiscus_url=hibiscus_url,
            hibiscus_api_key=hibiscus_api_key,
            agent_name=agent_name,
            agent_description=agent_description,
            agent_capabilities=agent_capabilities,
            agent_domains=agent_domains,
            agent_tags=agent_tags,
            agent_metadata=agent_metadata,
            endpoint=endpoint,
            author_name=agent_author,
            version=agent_version
        )
    
    # Set up Sheldon CA certificates if required
    cert_manager = None
    if enable_security and enable_mtls:
        # Setup certificates
        cert_manager = setup_sheldon_certificates(
            did_manager=did_manager,
            cert_path=cert_path,
            sheldon_ca_url=sheldon_ca_url,
        )
    
    # Set up mTLS middleware if enabled
    mtls_middleware, ssl_context = setup_mtls_middleware(
        enable_mtls,
        agent_id,
        did_manager,
        cert_path=cert_path,
        cert_manager=cert_manager
    )
    
    # Create the servers
    jsonrpc_app = create_jsonrpc_server(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=supported_methods,
        security_middleware=security_middleware,
        mtls_middleware=mtls_middleware
    )
    
    rest_app = create_rest_server(
        protocol_handler=protocol_handler
    )
    
    # Determine the appropriate hosting method based on host value
    hosting_method = "docker" if host == "0.0.0.0" else "local"
    
    logger.info(f"Server initialization complete, starting servers")
    
    # Start the servers
    await start_servers(
        jsonrpc_app=jsonrpc_app,
        rest_app=rest_app,
        host=host,
        hosting_method=hosting_method,
        pebbling_port=pebbling_port,
        user_port=user_port,
        ssl_context=ssl_context if enable_mtls else None,
    )