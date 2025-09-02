import asyncio
import os
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional

import uvicorn
import uvicorn.config
from fastapi import FastAPI
from pydantic import AnyHttpUrl

from pebbling.server.applications import PebbleApplication
from pebbling.storage.memory_storage import InMemoryStorage
from pebbling.storage.postgres_storage import PostgreSQLStorage
from pebbling.storage.qdrant_storage import QdrantStorage
from pebbling.server.scheduler.memory_scheduler import InMemoryScheduler
from pebbling.server.scheduler.redis_scheduler import RedisScheduler
from pebbling.protocol.types import AgentManifest


class PebbleServer:
    """Pebble server for hosting agents with Pebble protocol support."""
    
    def __init__(self) -> None:
        """Initialize the Pebble server."""
        self.penguins: list[AgentManifest] = []
        self.server: Optional[uvicorn.Server] = None
        self._storage: Optional[InMemoryStorage | PostgreSQLStorage | QdrantStorage] = None
        self._scheduler: Optional[InMemoryScheduler | RedisScheduler] = None
        self._task_manager: Optional[TaskManager] = None
        

    
    async def serve(
        self,
        *,
        penguin_id: str = "pebble-server",
        host: str = "127.0.0.1",
        port: int = 8000,
        debug: bool = False,
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
            storage: Storage backend
            scheduler: Task scheduler
            uds: Unix domain socket
            fd: File descriptor
            loop: Event loop
            http: HTTP protocol
            ws: WebSocket protocol
            ws_max_size: Maximum size of WebSocket message
            ws_max_queue: Maximum queue size of WebSocket message
            ws_ping_interval: Ping interval
            ws_ping_timeout: Ping timeout
            ws_per_message_deflate: Enable per-message deflate
            lifespan: Lifespan
            env_file: Environment file
            log_config: Logging configuration
            log_level: Logging level
            access_log: Enable access log
            use_colors: Enable colors
            interface: Interface
            reload: Enable auto-reload
            reload_dirs: Directories to watch for auto-reload
            reload_delay: Delay between auto-reload checks
            reload_includes: Files to include for auto-reload
            reload_excludes: Files to exclude for auto-reload
            workers: Number of workers
            proxy_headers: Enable proxy headers
            server_header: Enable server header
            date_header: Enable date header
            forwarded_allow_ips: Forwarded allow IPs
            root_path: Root path
            limit_concurrency: Limit concurrency
            limit_max_requests: Limit max requests
            backlog: Backlog
            timeout_keep_alive: Timeout keep alive
            timeout_notify: Timeout notify
            timeout_graceful_shutdown: Timeout graceful shutdown
            callback_notify: Callback notify
            ssl_keyfile: SSL keyfile
            ssl_certfile: SSL certfile
            ssl_keyfile_password: SSL keyfile password
            ssl_version: SSL version
            ssl_cert_reqs: SSL cert reqs
            ssl_ca_certs: SSL CA certs
            ssl_ciphers: SSL ciphers
            headers: Headers
            factory: Factory
            h11_max_incomplete_event_size: H11 max incomplete event size
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

    