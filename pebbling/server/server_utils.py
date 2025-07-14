"""Server utilities for Pebbling servers."""

import ssl
import asyncio
from typing import Optional, Tuple, Dict, Any

import aiohttp
from aiohttp import web
from loguru import logger
import uvicorn

from pebbling.server.display import prepare_server_display


async def start_servers(
    jsonrpc_app: web.Application,
    rest_app: Optional[web.Application],
    host: str = "localhost",
    hosting_method: str = "local",  # Can be "local", "docker", "flyio"
    pebbling_port: int = 3773,
    user_port: int = 3774,
    ssl_context: Optional[ssl.SSLContext] = None,
) -> Tuple[web.AppRunner, Optional[web.AppRunner]]:
    """Start the JSON-RPC and REST servers.
    
    Args:
        jsonrpc_app: JSON-RPC server application
        rest_app: REST server application (optional)
        host: Host to bind to
        hosting_method: Hosting method ("local", "docker", or "flyio")
        port: Port to bind to
        ssl_context: SSL context for secure connections
        
    Returns:
        Tuple of (jsonrpc_runner, rest_runner)
    """
    # Display the server banner
    logger.info(prepare_server_display())
    
    # Determine protocol based on SSL context
    protocol = "https" if ssl_context else "http"

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


def create_uvicorn_config(
    app: web.Application,
    host: str,
    port: int, 
    ssl_context: Optional[ssl.SSLContext] = None
) -> dict:
    """Create a uvicorn server configuration.
    
    Args:
        app: aiohttp Application
        host: Host to bind server to
        port: Port to bind server to
        ssl_context: Optional SSL context for secure connections
        
    Returns:
        Uvicorn configuration dictionary
    """
    config = {
        "app": app,
        "host": host,
        "port": port,
        "log_level": "info",
    }
    
    if ssl_context:
        config["ssl_keyfile"] = getattr(ssl_context, "keyfile", None)
        config["ssl_certfile"] = getattr(ssl_context, "certfile", None)
        
    return config


async def create_secure_client_session(ssl_context: ssl.SSLContext) -> aiohttp.ClientSession:
    """Create a secure client session with mTLS support.
    
    Args:
        ssl_context: SSL context for the client
        
    Returns:
        Secure aiohttp ClientSession
    """
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    return aiohttp.ClientSession(connector=connector)


async def send_secure_request(
    session: aiohttp.ClientSession, 
    url: str, 
    method: str = "POST", 
    json_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Send a secure request to another agent using mTLS.
    
    Args:
        session: aiohttp ClientSession with mTLS configured
        url: Target URL
        method: HTTP method (default: POST)
        json_data: JSON data to send
        
    Returns:
        Response data
    """
    try:
        if method.upper() == "POST":
            async with session.post(url, json=json_data, verify_ssl=True) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Request failed with status {response.status}: {await response.text()}")
                    return {"success": False, "error": f"HTTP error {response.status}"}
        elif method.upper() == "GET":
            async with session.get(url, verify_ssl=True) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Request failed with status {response.status}: {await response.text()}")
                    return {"success": False, "error": f"HTTP error {response.status}"}
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except Exception as e:
        logger.error(f"Error sending secure request: {e}")
        return {"success": False, "error": str(e)}


async def establish_mtls_connection(
    target_url: str,
    client_ssl_context: ssl.SSLContext,
    exchange_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Establish a mutual TLS connection with another agent.
    
    This implements Phase 2 of the architecture - mTLS Connection Establishment.
    
    Args:
        target_url: URL of the target agent
        client_ssl_context: Client SSL context
        exchange_data: Certificate exchange data
        
    Returns:
        Connection result
    """
    try:
        # Create secure session
        async with create_secure_client_session(client_ssl_context) as session:
            # Send certificate exchange request
            exchange_result = await send_secure_request(
                session=session,
                url=f"{target_url}/exchange_certificates",
                json_data=exchange_data
            )
            
            if not exchange_result.get("success", False):
                logger.error(f"Certificate exchange failed: {exchange_result.get('error', 'Unknown error')}")
                return {"success": False, "error": "Certificate exchange failed"}
                
            # Verify connection
            verify_result = await send_secure_request(
                session=session,
                url=f"{target_url}/verify_connection",
                json_data={"agent_did": exchange_data.get("did")}
            )
            
            if not verify_result.get("success", False):
                logger.error(f"Connection verification failed: {verify_result.get('error', 'Unknown error')}")
                return {"success": False, "error": "Connection verification failed"}
                
            logger.info(f"mTLS connection established with {target_url}")
            return {"success": True, "connection_info": verify_result}
            
    except Exception as e:
        logger.error(f"Error establishing mTLS connection: {e}")
        return {"success": False, "error": str(e)}


async def start_fastapi_servers(
    jsonrpc_app: Any,  # FastAPI app
    rest_app: Optional[Any] = None,  # FastAPI app
    host: str = "localhost",
    hosting_method: str = "local",  # Can be "local", "docker", "flyio"
    port: int = 3773,
    ssl_context: Optional[ssl.SSLContext] = None,
) -> None:
    """Start the JSON-RPC and REST FastAPI servers using Uvicorn.
    
    Args:
        jsonrpc_app: FastAPI JSON-RPC server application
        rest_app: FastAPI REST server application (optional)
        host: Host to bind to
        hosting_method: Hosting method ("local", "docker", or "flyio")
        port: Port to bind to
        ssl_context: SSL context for secure connections
    """
    import uvicorn
    
    # Display the server banner
    logger.info(prepare_server_display())
    
    # Determine protocol based on SSL context
    protocol = "https" if ssl_context else "http"
    
    # Simple approach - use uvicorn.Server directly without asyncio.run
    ssl_args = {}
    if ssl_context:
        ssl_args = {
            "ssl_certfile": getattr(ssl_context, "_certfile", None),
            "ssl_keyfile": getattr(ssl_context, "_keyfile", None),
            "ssl_ca_certs": getattr(ssl_context, "_cafile", None),
        }
    
    # Log server start information
    logger.info(f"JSON-RPC server starting at {protocol}://{host}:{port}")
    if rest_app:
        logger.info(f"REST server starting at {protocol}://{host}:{port+1}")
    
    # Create server configurations
    jsonrpc_config = uvicorn.Config(
        jsonrpc_app,
        host=host,
        port=port,
        log_level="info",
        **ssl_args
    )
    
    # Create server instances
    jsonrpc_server = uvicorn.Server(jsonrpc_config)
    # Critical: Disable signal handlers to prevent conflicts
    jsonrpc_server.config.install_signal_handlers = False
    
    # Create REST server if provided
    rest_server = None
    if rest_app:
        rest_config = uvicorn.Config(
            rest_app,
            host=host,
            port=port+1,
            log_level="info",
            **ssl_args
        )
        rest_server = uvicorn.Server(rest_config)
        rest_server.config.install_signal_handlers = False
    
    # Start servers using serve() method directly
    try:
        if rest_server:
            # Run both servers concurrently
            await asyncio.gather(
                jsonrpc_server.serve(),
                rest_server.serve()
            )
        else:
            # Run only the JSON-RPC server
            await jsonrpc_server.serve()
    except Exception as e:
        logger.error(f"Error starting servers: {str(e)}")
        raise
