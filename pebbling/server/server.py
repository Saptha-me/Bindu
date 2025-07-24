# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Pebbling Server.

Main server class for running Pebbling agents with unified protocol support.
Follows the acp pattern for easy agent registration and server management.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, Optional

import uvicorn
import uvicorn.config
from fastapi import FastAPI
from pydantic import AnyHttpUrl

from pebbling.protocol.types import AgentManifest
from pebbling.server.app import create_app
from pebbling.server.store import StoreManager

logger = logging.getLogger(__name__)


class Server:
    """
    Pebbling Server for running agents with unified protocol support.
    
    Provides both JSON-RPC (a2a-style) and HTTP REST (acp-style) interfaces
    with shared task management and session contexts.
    """
    
    def __init__(self, *, store_manager: Optional[StoreManager] = None) -> None:
        """
        Initialize the Pebbling server.
        
        Args:
            store_manager: Optional custom store manager instance
        """
        self.agents: list[AgentManifest] = []
        self.server: Optional[uvicorn.Server] = None
        self.store_manager = store_manager or StoreManager()
        self._app: Optional[FastAPI] = None
    
    def agent(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        skills: Optional[list] = None,
        capabilities: Optional[dict] = None,
        user_id: str = "default-user",
        version: str = "1.0.0",
        **metadata: Any
    ) -> Callable:
        """
        Decorator to register an agent with the server.
        
        Args:
            name: Agent name (defaults to function name)
            description: Agent description
            skills: List of agent skills
            capabilities: Agent capabilities
            user_id: User ID who owns the agent
            version: Agent version
            **metadata: Additional metadata
            
        Returns:
            Decorator function
        """
        def decorator(fn: Callable) -> Callable:
            # Create agent manifest
            agent_name = name or fn.__name__.replace('_', ' ').title()
            agent_description = description or fn.__doc__ or f"{agent_name} agent"
            
            manifest = AgentManifest(
                id=fn.__name__.replace('_', '-'),
                name=agent_name,
                description=agent_description,
                user_id=user_id,
                version=version,
                instance=fn,  # Store the function as the instance
                skills=skills,
                capabilities=capabilities,
                extra_data=metadata
            )
            
            self.register(manifest)
            return fn
        
        return decorator
    
    def register(self, *agents: AgentManifest) -> None:
        """
        Register one or more agents with the server.
        
        Args:
            *agents: Agent manifests to register
        """
        self.agents.extend(agents)
        logger.info(f"Registered {len(agents)} agent(s)")
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None]:
        """
        Application lifespan manager.
        
        Handles startup and shutdown tasks including agent registration.
        """
        logger.info("Starting Pebbling Server lifespan...")
        
        # Register all agents with the store
        for agent in self.agents:
            try:
                await self.store_manager.register_agent(agent)
                logger.info(f"Registered agent: {agent.name} ({agent.id})")
            except Exception as e:
                logger.error(f"Failed to register agent {agent.name}: {e}")
        
        logger.info(f"Server ready with {len(self.agents)} agent(s)")
        
        yield
        
        logger.info("Shutting down Pebbling Server...")
    
    def create_app(
        self,
        *,
        title: str = "Pebbling Server",
        description: str = "Unified agent-to-agent communication server",
        version: str = "1.0.0",
        **kwargs: Any
    ) -> FastAPI:
        """
        Create the FastAPI application.
        
        Args:
            title: Application title
            description: Application description
            version: Application version
            **kwargs: Additional FastAPI arguments
            
        Returns:
            Configured FastAPI application
        """
        if self._app is None:
            # Create app with custom lifespan
            app = create_app(
                title=title,
                description=description,
                version=version,
                store_manager=self.store_manager,
                **kwargs
            )
            
            # Override the lifespan to include agent registration
            original_lifespan = app.router.lifespan_context
            
            @asynccontextmanager
            async def combined_lifespan(app: FastAPI) -> AsyncGenerator[None]:
                # Run our lifespan first
                async with self.lifespan(app):
                    # Then run the original lifespan
                    if original_lifespan:
                        async with original_lifespan(app):
                            yield
                    else:
                        yield
            
            app.router.lifespan_context = combined_lifespan
            self._app = app
        
        return self._app
    
    async def serve(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
        uds: Optional[str] = None,
        fd: Optional[int] = None,
        loop: uvicorn.config.LoopSetupType = "auto",
        http: uvicorn.config.HTTPProtocolType = "auto",
        ws: uvicorn.config.WSProtocolType = "auto",
        ws_max_size: int = 16 * 1024 * 1024,
        ws_max_queue: int = 32,
        ws_ping_interval: Optional[float] = 20.0,
        ws_ping_timeout: Optional[float] = 20.0,
        ws_per_message_deflate: bool = True,
        lifespan: uvicorn.config.LifespanType = "auto",
        env_file: Optional[str | os.PathLike[str]] = None,
        log_config: Optional[
            dict[str, Any] | str | uvicorn.config.RawConfigParser | uvicorn.config.IO[Any]
        ] = uvicorn.config.LOGGING_CONFIG,
        log_level: Optional[str | int] = None,
        access_log: bool = True,
        use_colors: Optional[bool] = None,
        interface: uvicorn.config.InterfaceType = "auto",
        reload: bool = False,
        reload_dirs: Optional[list[str] | str] = None,
        reload_delay: float = 0.25,
        reload_includes: Optional[list[str] | str] = None,
        reload_excludes: Optional[list[str] | str] = None,
        workers: Optional[int] = None,
        proxy_headers: bool = True,
        server_header: bool = True,
        date_header: bool = True,
        forwarded_allow_ips: Optional[list[str] | str] = None,
        root_path: str = "",
        limit_concurrency: Optional[int] = None,
        limit_max_requests: Optional[int] = None,
        backlog: int = 2048,
        timeout_keep_alive: int = 5,
        timeout_notify: int = 30,
        timeout_graceful_shutdown: Optional[int] = None,
        callback_notify: Optional[Callable[..., Awaitable[None]]] = None,
        ssl_keyfile: Optional[str | os.PathLike[str]] = None,
        ssl_certfile: Optional[str | os.PathLike[str]] = None,
        ssl_keyfile_password: Optional[str] = None,
        ssl_version: int = uvicorn.config.SSL_PROTOCOL_VERSION,
        ssl_cert_reqs: int = uvicorn.config.ssl.CERT_NONE,
        ssl_ca_certs: Optional[str] = None,
        ssl_ciphers: str = "TLSv1",
        **kwargs: Any
    ) -> None:
        """
        Serve the application using uvicorn.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional uvicorn configuration options
        """
        app = self.create_app()
        
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            uds=uds,
            fd=fd,
            loop=loop,
            http=http,
            ws=ws,
            ws_max_size=ws_max_size,
            ws_max_queue=ws_max_queue,
            ws_ping_interval=ws_ping_interval,
            ws_ping_timeout=ws_ping_timeout,
            ws_per_message_deflate=ws_per_message_deflate,
            lifespan=lifespan,
            env_file=env_file,
            log_config=log_config,
            log_level=log_level,
            access_log=access_log,
            use_colors=use_colors,
            interface=interface,
            reload=reload,
            reload_dirs=reload_dirs,
            reload_delay=reload_delay,
            reload_includes=reload_includes,
            reload_excludes=reload_excludes,
            workers=workers,
            proxy_headers=proxy_headers,
            server_header=server_header,
            date_header=date_header,
            forwarded_allow_ips=forwarded_allow_ips,
            root_path=root_path,
            limit_concurrency=limit_concurrency,
            limit_max_requests=limit_max_requests,
            backlog=backlog,
            timeout_keep_alive=timeout_keep_alive,
            timeout_notify=timeout_notify,
            timeout_graceful_shutdown=timeout_graceful_shutdown,
            callback_notify=callback_notify,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_keyfile_password=ssl_keyfile_password,
            ssl_version=ssl_version,
            ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs,
            ssl_ciphers=ssl_ciphers,
            **kwargs
        )
        
        self.server = uvicorn.Server(config)
        await self.server.serve()
    
    def run(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
        **kwargs: Any
    ) -> None:
        """
        Run the server synchronously.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional serve arguments
        """
        asyncio.run(self.serve(host=host, port=port, **kwargs))
    
    async def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "registered_agents": len(self.agents),
            "agent_names": [agent.name for agent in self.agents],
            "store_stats": await self.store_manager.get_stats()
        }
