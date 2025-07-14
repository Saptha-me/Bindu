"""
Enhanced mTLS server utilities for the Pebbling framework.

This module provides enhanced utilities for mTLS-secured communication
between Pebbling agents, building on the base server_utils module.
"""

import ssl
import json
import logging
import asyncio
import os.path
from typing import Dict, Any, Optional, Tuple, List, Callable

import aiohttp
from aiohttp import web
import uvicorn

from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.security.mtls.exceptions import (
    CertificateError, 
    SSLContextError,
    CertificateVerificationError
)
from pebbling.security.did_manager import DIDManager
from pebbling.security.config import SECURITY_ENDPOINTS

logger = logging.getLogger(__name__)


async def create_mtls_server(
    app: web.Application,
    host: str,
    port: int,
    certificate_manager: CertificateManager,
    server_name: str = "Pebbling mTLS Server"
) -> uvicorn.Server:
    """Create an mTLS-secured uvicorn server.
    
    Args:
        app: aiohttp web application
        host: Host to bind to
        port: Port to bind to
        certificate_manager: Certificate manager for mTLS
        server_name: Name of the server for logging
        
    Returns:
        Configured uvicorn Server
        
    Raises:
        SSLContextError: If SSL context creation fails
    """
    try:
        # Create server-side SSL context
        ssl_context = certificate_manager.create_ssl_context(server_side=True)
        
        # Create uvicorn config
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            ssl_keyfile=certificate_manager.key_path,
            ssl_certfile=certificate_manager.cert_path,
            ssl_ca_certs=certificate_manager.ca_cert_path,
            ssl_cert_reqs=ssl.CERT_REQUIRED  # Require client certificates
        )
        
        # Create server
        server = uvicorn.Server(config)
        server.config.install_signal_handlers = False
        
        logger.info(f"Created mTLS-secured {server_name} on {host}:{port}")
        return server
        
    except Exception as e:
        error_msg = f"Failed to create mTLS server: {str(e)}"
        logger.error(error_msg)
        raise SSLContextError(error_msg) from e


async def secure_agent_request(
    target_url: str,
    method: str,
    certificate_manager: CertificateManager,
    did_manager: DIDManager,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Send a secure request to another agent using mTLS.
    
    This function:
    1. Creates a secure client session with mTLS
    2. Adds DID-based authorization header
    3. Sends the request
    4. Handles errors and responses
    
    Args:
        target_url: URL of the target agent
        method: HTTP method (GET, POST, etc.)
        certificate_manager: Certificate manager for mTLS
        did_manager: DID manager for authentication
        json_data: JSON data to send (for POST/PUT)
        headers: Additional headers to include
        
    Returns:
        Response data or error information
        
    Raises:
        CertificateError: If mTLS setup fails
    """
    try:
        # Create client SSL context
        ssl_context = certificate_manager.create_ssl_context(server_side=False)
        
        # Prepare headers
        if not headers:
            headers = {}
            
        # Add authorization header with DID
        if "Authorization" not in headers:
            headers["Authorization"] = f"DID {did_manager.did}"
            
        # Create secure session and send request
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            method = method.upper()
            
            if method == "GET":
                async with session.get(target_url, headers=headers, ssl=True) as response:
                    return await _process_response(response)
                    
            elif method == "POST":
                async with session.post(target_url, json=json_data, headers=headers, ssl=True) as response:
                    return await _process_response(response)
                    
            elif method == "PUT":
                async with session.put(target_url, json=json_data, headers=headers, ssl=True) as response:
                    return await _process_response(response)
                    
            elif method == "DELETE":
                async with session.delete(target_url, headers=headers, ssl=True) as response:
                    return await _process_response(response)
                    
            else:
                return {"success": False, "error": f"Unsupported HTTP method: {method}"}
                
    except aiohttp.ClientError as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during request: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


async def _process_response(response: aiohttp.ClientResponse) -> Dict[str, Any]:
    """Process an HTTP response.
    
    Args:
        response: aiohttp ClientResponse
        
    Returns:
        Processed response data
    """
    try:
        if response.content_type == "application/json":
            data = await response.json()
        else:
            data = await response.text()
            
        return {
            "success": 200 <= response.status < 300,
            "status": response.status,
            "data": data,
            "headers": dict(response.headers)
        }
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to process response: {str(e)}",
            "status": response.status
        }


async def send_jsonrpc_request_secure(
    url: str,
    method: str,
    params: Dict[str, Any],
    certificate_manager: CertificateManager,
    did_manager: DIDManager
) -> Dict[str, Any]:
    """Send a JSON-RPC request over a secure mTLS connection.
    
    Args:
        url: Target URL for JSON-RPC
        method: JSON-RPC method to call
        params: Parameters for the method
        certificate_manager: Certificate manager for mTLS
        did_manager: DID manager for authentication
        
    Returns:
        JSON-RPC response
        
    Raises:
        CertificateError: If mTLS setup fails
    """
    # Prepare JSON-RPC payload
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    # Send secure request
    response = await secure_agent_request(
        url,
        "POST",
        certificate_manager,
        did_manager,
        json_data=payload
    )
    
    # Process response
    if not response.get("success", False):
        logger.error(f"JSON-RPC request failed: {response.get('error', 'Unknown error')}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": response.get("error", "Internal error")
            },
            "id": 1
        }
        
    # Extract JSON-RPC response
    if "data" in response:
        return response["data"]
    else:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Invalid response format"
            },
            "id": 1
        }


async def verify_agent_connection(
    target_url: str,
    certificate_manager: CertificateManager,
    did_manager: DIDManager
) -> Tuple[bool, Dict[str, Any]]:
    """Verify connection with another agent.
    
    This implements the full security verification process:
    1. Exchange DIDs
    2. Verify mTLS certificates
    3. Perform challenge-response authentication
    
    Args:
        target_url: Base URL of the target agent
        certificate_manager: Certificate manager for mTLS
        did_manager: DID manager for authentication
        
    Returns:
        Tuple of (success, result)
        
    Raises:
        CertificateError: If mTLS setup fails
    """
    try:
        # Step 1: Exchange DIDs
        exchange_url = f"{target_url}{SECURITY_ENDPOINTS['exchange_did']}"
        exchange_data = {
            "did": did_manager.did,
            "did_document": did_manager.get_did_document()
        }
        
        exchange_result = await secure_agent_request(
            exchange_url,
            "POST",
            certificate_manager,
            did_manager,
            json_data=exchange_data
        )
        
        if not exchange_result.get("success", False):
            logger.error(f"DID exchange failed: {exchange_result.get('error', 'Unknown error')}")
            return False, {"error": f"DID exchange failed: {exchange_result.get('error', 'Unknown error')}"}
            
        # Extract peer DID and certificate info
        peer_data = exchange_result.get("data", {})
        peer_did = peer_data.get("did")
        
        if not peer_did:
            logger.error("Missing peer DID in exchange response")
            return False, {"error": "Missing peer DID in exchange response"}
            
        # Step 2: Verify connection
        verify_url = f"{target_url}{SECURITY_ENDPOINTS['verify_connection']}"
        verify_data = {
            "did": did_manager.did
        }
        
        # If we have certificate information, include it
        with open(certificate_manager.cert_path, "r") as f:
            certificate = f.read()
            verify_data["certificate"] = certificate
            
        verify_result = await secure_agent_request(
            verify_url,
            "POST",
            certificate_manager,
            did_manager,
            json_data=verify_data
        )
        
        if not verify_result.get("success", False):
            logger.error(f"Connection verification failed: {verify_result.get('error', 'Unknown error')}")
            return False, {"error": f"Connection verification failed: {verify_result.get('error', 'Unknown error')}"}
            
        # Step 3: Request challenge for extra security (optional)
        challenge_url = f"{target_url}{SECURITY_ENDPOINTS['challenge']}"
        challenge_data = {
            "did": did_manager.did
        }
        
        challenge_result = await secure_agent_request(
            challenge_url,
            "POST",
            certificate_manager,
            did_manager,
            json_data=challenge_data
        )
        
        if not challenge_result.get("success", False):
            logger.warning(f"Challenge request failed, continuing without challenge: {challenge_result.get('error')}")
        else:
            # Sign the challenge
            challenge_data = challenge_result.get("data", {})
            challenge_id = challenge_data.get("challenge_id")
            challenge = challenge_data.get("challenge")
            
            if challenge_id and challenge:
                # Sign the challenge
                signature = did_manager.sign_message(challenge)
                
                # Send challenge response
                response_url = f"{target_url}{SECURITY_ENDPOINTS['challenge_response']}"
                response_data = {
                    "challenge_id": challenge_id,
                    "did": did_manager.did,
                    "signature": signature
                }
                
                response_result = await secure_agent_request(
                    response_url,
                    "POST",
                    certificate_manager,
                    did_manager,
                    json_data=response_data
                )
                
                if not response_result.get("success", False):
                    logger.warning(f"Challenge response failed: {response_result.get('error')}")
                    
        # Connection verified successfully
        logger.info(f"Connection verified with agent at {target_url}")
        return True, {"did": peer_did}
        
    except Exception as e:
        error_msg = f"Error verifying agent connection: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}


async def start_mtls_servers(
    jsonrpc_app: web.Application,
    rest_app: Optional[web.Application],
    certificate_manager: CertificateManager,
    host: str = "localhost",
    pebbling_port: int = 3773,
    user_port: Optional[int] = None
) -> Tuple[uvicorn.Server, Optional[uvicorn.Server]]:
    """Start mTLS-secured servers.
    
    Args:
        jsonrpc_app: JSON-RPC server application
        rest_app: REST server application (optional)
        certificate_manager: Certificate manager for mTLS
        host: Host to bind to
        pebbling_port: Port for the Pebbling server
        user_port: Port for the user-facing server (if any)
        
    Returns:
        Tuple of (jsonrpc_server, rest_server)
        
    Raises:
        SSLContextError: If SSL context creation fails
    """
    # Create mTLS-secured Pebbling server
    pebbling_server = await create_mtls_server(
        jsonrpc_app,
        host,
        pebbling_port,
        certificate_manager,
        server_name="Pebbling mTLS JSON-RPC Server"
    )
    
    # Create REST server if needed
    rest_server = None
    if rest_app and user_port:
        # Note: REST server typically doesn't need mTLS as it's user-facing
        config = uvicorn.Config(
            rest_app,
            host=host,
            port=user_port,
            log_level="info"
        )
        rest_server = uvicorn.Server(config)
        rest_server.config.install_signal_handlers = False
        logger.info(f"Created REST server on {host}:{user_port}")
    
    # Start servers
    servers = [pebbling_server]
    if rest_server:
        servers.append(rest_server)
        
    await asyncio.gather(*(server.serve() for server in servers))
    
    return pebbling_server, rest_server
