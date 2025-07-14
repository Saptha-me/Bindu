"""
Enhanced Pebbling server with mTLS support.

This module extends the core Pebbling server functionality with mTLS security
features, allowing secure agent-to-agent communication with mutual TLS
authentication combined with DID-based verification.
"""

import os
import ssl
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union, Tuple

from aiohttp import web
from aiohttp.web import middleware
import uvicorn
from loguru import logger

from pebbling.server.pebbling_server import pebblify as base_pebblify
from pebbling.server.mtls_server_utils import start_mtls_servers
from pebbling.security.did_manager import DIDManager
from pebbling.security.middleware import SecurityMiddleware
from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.security.mtls.exceptions import (
    CertificateError, 
    SSLContextError
)
from pebbling.security.config import DEFAULT_SHELDON_CA_URL


async def pebblify_secure(
    app_name: str,
    handlers: Dict[str, Callable],
    did_key_path: Optional[str] = None,
    sheldon_ca_url: str = DEFAULT_SHELDON_CA_URL,
    certificate_dir: Optional[str] = None,
    host: str = "localhost",
    port: int = 3773,
    hosting_method: str = "local",  # Can be "local", "docker", "flyio"
    middlewares: Optional[List[middleware]] = None,
    rest_app: Optional[web.Application] = None,
    rest_port: Optional[int] = None,
    enable_mtls: bool = True,
    auto_renew_certificates: bool = True
) -> Tuple[web.Application, DIDManager, Optional[CertificateManager]]:
    """Initialize a Pebbling server with enhanced mTLS security.
    
    This function extends the base pebblify function to add mTLS support:
    1. Initializes a DID Manager for agent identity
    2. Initializes a Certificate Manager for mTLS certificates
    3. Sets up Security Middleware for authentication
    4. Starts secure servers with mTLS
    
    Args:
        app_name: Name of the application
        handlers: Dictionary mapping method names to handler functions
        did_key_path: Path to the DID key file (created if not exists)
        sheldon_ca_url: URL of the Sheldon CA service
        certificate_dir: Directory for storing certificates
        host: Host to bind to
        port: Port to bind to
        hosting_method: Hosting method ("local", "docker", or "flyio")
        middlewares: Additional middlewares to apply
        rest_app: REST server application (optional)
        rest_port: Port for the REST server
        enable_mtls: Whether to enable mTLS
        auto_renew_certificates: Whether to automatically renew certificates
        
    Returns:
        Tuple of (web application, DID manager, certificate manager)
        
    Raises:
        CertificateError: If certificate initialization fails
    """
    # Generate default paths if not provided
    if not did_key_path:
        # Create a key in the user's home directory
        home_dir = os.path.expanduser("~")
        pebble_dir = os.path.join(home_dir, ".pebble")
        os.makedirs(pebble_dir, exist_ok=True)
        did_key_path = os.path.join(pebble_dir, f"{app_name}_did_key.json")
        
    if not certificate_dir and enable_mtls:
        # Create certificate directory
        home_dir = os.path.expanduser("~")
        certificate_dir = os.path.join(home_dir, ".pebble", "certs")
        os.makedirs(certificate_dir, exist_ok=True)
    
    # Initialize DID Manager
    did_manager = DIDManager(did_key_path)
    
    # Initialize Certificate Manager if mTLS is enabled
    certificate_manager = None
    if enable_mtls:
        try:
            logger.info(f"Initializing Certificate Manager with CA at {sheldon_ca_url}")
            certificate_manager = CertificateManager(
                did_manager,
                sheldon_ca_url,
                cert_dir=certificate_dir,
                auto_renewal=auto_renew_certificates
            )
            # Initialize certificate manager (get/request certificates)
            await certificate_manager.initialize()
            logger.info(f"Certificate Manager initialized for {did_manager.did}")
            
            # Start certificate renewal task if auto-renewal is enabled
            if auto_renew_certificates:
                await certificate_manager.start_renewal_task()
                
        except Exception as e:
            error_msg = f"Failed to initialize Certificate Manager: {str(e)}"
            logger.error(error_msg)
            if isinstance(e, CertificateError):
                raise
            raise CertificateError(error_msg) from e
    
    # Initialize Security Middleware
    security_middleware = SecurityMiddleware(
        did_manager,
        certificate_manager
    )
    
    # Combine middlewares
    if middlewares is None:
        middlewares = []
    middlewares.append(security_middleware.verify_security)
    
    # Create the JSON-RPC application
    app = web.Application(middlewares=middlewares)
    
    # Apply the security middleware (adds routes)
    security_middleware.apply(app)
    
    # Add handlers to the application
    # Here we're calling the base pebblify function
    base_pebblify(
        app_name,
        handlers,
        app=app,
        did_key_path=did_key_path,
        host=host,
        port=port,
        hosting_method=hosting_method
    )
    
    # Start servers in a background task if mTLS is enabled
    if enable_mtls and certificate_manager:
        ssl_context = certificate_manager.create_ssl_context(server_side=True)
        
        async def start_servers_task():
            try:
                await start_mtls_servers(
                    app,
                    rest_app,
                    certificate_manager,
                    host=host,
                    pebbling_port=port,
                    user_port=rest_port
                )
            except Exception as e:
                logger.error(f"Error starting mTLS servers: {str(e)}")
                
        # Start servers in background task
        asyncio.create_task(start_servers_task())
    
    return app, did_manager, certificate_manager


# Export API
__all__ = ["pebblify_secure"]
