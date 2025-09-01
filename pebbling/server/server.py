import asyncio
import os
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional

import uvicorn
import uvicorn.config
from fastapi import FastAPI
from pydantic import AnyHttpUrl

from pebbling.common.models.agent_manifest import AgentManifest
from pebbling.server.applications import create_app
from pebbling.storage.memory_storage import InMemoryStorage
from pebbling.storage.postgres_storage import PostgreSQLStorage
from pebbling.storage.qdrant_storage import QdrantStorage
from pebbling.server.scheduler.memory_scheduler import InMemoryScheduler
from pebbling.server.scheduler.redis_scheduler import RedisScheduler
from pebbling.protocol.types import AgentSkill


class Server:
    """Pebble server for hosting agents with A2A protocol support."""
    
    def __init__(self) -> None:
        """Initialize the Pebble server."""
        self.agents: list[AgentManifest] = []
        self.server: Optional[uvicorn.Server] = None
        self._storage: Optional[InMemoryStorage | PostgreSQLStorage | QdrantStorage] = None
        self._scheduler: Optional[InMemoryScheduler | RedisScheduler] = None

    def agent(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        skills: Optional[list[AgentSkill]] = None,
    ) -> Callable:
        """Decorator to register an agent with the server.
        
        Args:
            name: Agent name
            description: Agent description  
            version: Agent version
            skills: List of agent skills
            
        Returns:
            Decorator function
        """
        def decorator(fn: Callable) -> Callable:
            # Create agent manifest from function
            agent_manifest = AgentManifest(
                id=name or fn.__name__,
                name=name or fn.__name__.replace('_', ' ').title(),
                description=description or fn.__doc__ or f"Agent {name or fn.__name__}",
                version=version,
                skills=skills or [],
                function=fn
            )
            self.register(agent_manifest)
            return fn

        return decorator

    def register(self, *agents: AgentManifest) -> None:
        """Register agent manifests with the server.
        
        Args:
            *agents: Agent manifests to register
        """
        self.agents.extend(agents)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Default lifespan manager for the server."""
        yield

    def set_storage(self, storage: InMemoryStorage | PostgreSQLStorage | QdrantStorage) -> None:
        """Set the storage backend for the server.
        
        Args:
            storage: Storage backend instance
        """
        self._storage = storage

    def set_scheduler(self, scheduler: InMemoryScheduler | RedisScheduler) -> None:
        """Set the task scheduler for the server.
        
        Args:
            scheduler: Scheduler instance
        """
        self._scheduler = scheduler

    async def serve(
        self,
        *,
        penguin_id: str = "pebble-server",
        host: str = "127.0.0.1",
        port: int = 8000,
        debug: bool = False,
        configure_logger: bool = True,
        self_registration: bool = True,
        storage: Optional[InMemoryStorage | PostgreSQLStorage | QdrantStorage] = None,
        scheduler: Optional[InMemoryScheduler | RedisScheduler] = None,
        # Uvicorn parameters
        uds: Optional[str] = None,
        fd: Optional[int] = None,
        loop: uvicorn.config.LoopSetupType = "auto",
        http: type[asyncio.Protocol] | uvicorn.config.HTTPProtocolType = "auto",
        ws: type[asyncio.Protocol] | uvicorn.config.WSProtocolType = "auto",
        ws_max_size: int = 16 * 1024 * 1024,
        ws_max_queue: int = 32,
        ws_ping_interval: Optional[float] = 20.0,
        ws_ping_timeout: Optional[float] = 20.0,
        ws_per_message_deflate: bool = True,
        lifespan: uvicorn.config.LifespanType = "auto",
        env_file: Optional[str | os.PathLike[str]] = None,
        log_config: Optional[dict[str, Any] | str | uvicorn.config.RawConfigParser | uvicorn.config.IO[Any]] = uvicorn.config.LOGGING_CONFIG,
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
        headers: Optional[list[tuple[str, str]]] = None,
        factory: bool = False,
        h11_max_incomplete_event_size: Optional[int] = None,
    ) -> None:
        """Start the Pebble server.
        
        Args:
            penguin_id: Unique server identifier
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
            configure_logger: Configure logging
            self_registration: Enable self-registration
            storage: Storage backend
            scheduler: Task scheduler
            **kwargs: Additional uvicorn configuration parameters
        """
        if self.server:
            raise RuntimeError("The server is already running")

        if headers is None:
            headers = [("server", "pebble")]
        elif not any(k.lower() == "server" for k, _ in headers):
            headers.append(("server", "pebble"))

        # Use provided storage/scheduler or defaults
        final_storage = storage or self._storage or InMemoryStorage()
        final_scheduler = scheduler or self._scheduler or InMemoryScheduler()

        # Create FastAPI app
        app = create_app(
            *self.agents,
            storage=final_storage,
            scheduler=final_scheduler,
            penguin_id=penguin_id,
            url=f"http://{host}:{port}",
            debug=debug
        )

        # Configure uvicorn
        config = uvicorn.Config(
            app,
            host,
            port,
            uds,
            fd,
            loop,
            http,
            ws,
            ws_max_size,
            ws_max_queue,
            ws_ping_interval,
            ws_ping_timeout,
            ws_per_message_deflate,
            lifespan,
            env_file,
            log_config,
            log_level,
            access_log,
            use_colors,
            interface,
            reload,
            reload_dirs,
            reload_delay,
            reload_includes,
            reload_excludes,
            workers,
            proxy_headers,
            server_header,
            date_header,
            forwarded_allow_ips,
            root_path,
            limit_concurrency,
            limit_max_requests,
            backlog,
            timeout_keep_alive,
            timeout_notify,
            timeout_graceful_shutdown,
            callback_notify,
            ssl_keyfile,
            ssl_certfile,
            ssl_keyfile_password,
            ssl_version,
            ssl_cert_reqs,
            ssl_ca_certs,
            ssl_ciphers,
            headers,
            factory,
            h11_max_incomplete_event_size,
        )
        
        self.server = uvicorn.Server(config)
        await self.server.serve()

    def run(
        self,
        *,
        penguin_id: str = "pebble-server",
        host: str = "127.0.0.1",
        port: int = 8000,
        debug: bool = False,
        configure_logger: bool = True,
        self_registration: bool = True,
        storage: Optional[InMemoryStorage | PostgreSQLStorage | QdrantStorage] = None,
        scheduler: Optional[InMemoryScheduler | RedisScheduler] = None,
        # Uvicorn parameters
        uds: Optional[str] = None,
        fd: Optional[int] = None,
        loop: uvicorn.config.LoopSetupType = "auto",
        http: type[asyncio.Protocol] | uvicorn.config.HTTPProtocolType = "auto",
        ws: type[asyncio.Protocol] | uvicorn.config.WSProtocolType = "auto",
        ws_max_size: int = 16 * 1024 * 1024,
        ws_max_queue: int = 32,
        ws_ping_interval: Optional[float] = 20.0,
        ws_ping_timeout: Optional[float] = 20.0,
        ws_per_message_deflate: bool = True,
        lifespan: uvicorn.config.LifespanType = "auto",
        env_file: Optional[str | os.PathLike[str]] = None,
        log_config: Optional[dict[str, Any] | str | uvicorn.config.RawConfigParser | uvicorn.config.IO[Any]] = uvicorn.config.LOGGING_CONFIG,
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
        headers: Optional[list[tuple[str, str]]] = None,
        factory: bool = False,
        h11_max_incomplete_event_size: Optional[int] = None,
    ) -> None:
        """Run the Pebble server (blocking).
        
        Args:
            penguin_id: Unique server identifier
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
            configure_logger: Configure logging
            self_registration: Enable self-registration
            storage: Storage backend
            scheduler: Task scheduler
            **kwargs: Additional uvicorn configuration parameters
        """
        asyncio.run(
            self.serve(
                penguin_id=penguin_id,
                host=host,
                port=port,
                debug=debug,
                configure_logger=configure_logger,
                self_registration=self_registration,
                storage=storage,
                scheduler=scheduler,
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
                headers=headers,
                factory=factory,
                h11_max_incomplete_event_size=h11_max_incomplete_event_size,
            )
        )
