"""
Server configuration and startup for the Pebble framework.

This module provides utilities for configuring and starting the FastAPI server
for agent deployment.
"""

from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pebble.core.protocol import AgentProtocol
from pebble.api.routes import register_routes
from pebble.schemas.models import DeploymentConfig


def create_app(
    adapter: AgentProtocol,
    config: Optional[DeploymentConfig] = None,
    additional_adapters: Optional[List[AgentProtocol]] = None
) -> FastAPI:
    """Create and configure a FastAPI application for agent deployment.
    
    Args:
        adapter: The primary agent protocol adapter
        config: Configuration for deployment
        additional_adapters: Additional agent protocol adapters to register
        
    Returns:
        FastAPI: The configured FastAPI application
    """
    # Use default config if none provided
    if config is None:
        config = DeploymentConfig()
    
    # Create the FastAPI app
    app = FastAPI(
        title=f"Pebble Agent: {adapter.name}",
        description=f"Pebble API for interacting with the '{adapter.name}' agent",
        version="0.1.0",
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register the API routes
    register_routes(
        app=app,
        adapter=adapter,
        require_auth=config.require_auth,
        additional_adapters=additional_adapters
    )

    if config.security and config.security.use_mtls:
        # Generate certificate for this server if needed
        agent_id = str(adapter.agent_id)
        cert_dir = Path(config.security.certs_dir) if config.security.certs_dir else None
        cert_path, key_path = generate_agent_certificate(agent_id, cert_dir)
        
        # Store paths in config for server startup
        config.security.cert_path = str(cert_path)
        config.security.key_path = str(key_path)
        
        # Store endpoint in adapter metadata for other agents to connect
        adapter.metadata["endpoint"] = f"https://{config.host}:{config.port}"
        
        # Setup client certificate verification
        @app.middleware("https")
        async def verify_client_cert(request: Request, call_next):
            # This middleware will only be effective when running with uvicorn SSL
            client_cert = request.scope.get("client_cert")
            if not client_cert and config.security.require_client_cert:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Client certificate required"}
                )
            return await call_next(request)
    
    # ... rest of existing code ...
    return app
    
    return app


def start_server(
    app: FastAPI,
    config: Optional[DeploymentConfig] = None
) -> None:
    """Start the FastAPI server.
    
    Args:
        app: The FastAPI application
        config: Configuration for deployment
    """
    import uvicorn
    
    # Use default config if none provided
    mport uvicorn
    
    uvicorn_config = {
        "app": app,
        "host": config.host,
        "port": config.port,
        "log_level": config.log_level.lower(),
    }
    
    # Add SSL configuration if using mTLS
    if config.security and config.security.use_mtls:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile=config.security.cert_path,
            keyfile=config.security.key_path
        )
        
        # Require client certificate if configured
        if config.security.require_client_cert:
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # Load CA bundle if provided
            if config.security.ca_bundle_path:
                ssl_context.load_verify_locations(cafile=config.security.ca_bundle_path)
        
        uvicorn_config["ssl"] = ssl_context
    
    uvicorn.run(**uvicorn_config)
