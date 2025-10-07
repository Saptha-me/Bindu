from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional, Sequence
from uuid import UUID

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Lifespan, Receive, Scope, Send

from bindu.common.models import AgentManifest

from .endpoints import (
    agent_card_endpoint,
    agent_info_endpoint,
    agent_page_endpoint,
    agent_run_endpoint,
    chat_page_endpoint,
    common_css_endpoint,
    common_js_endpoint,
    did_resolve_endpoint,
    docs_endpoint,
    footer_component_endpoint,
    header_component_endpoint,
    layout_js_endpoint,
    storage_page_endpoint,
)
from .scheduler.memory_scheduler import InMemoryScheduler
from .storage.memory_storage import InMemoryStorage
from .task_manager import TaskManager


class BinduApplication(Starlette):
    """Pebble application class for creating Pebble-compatible servers."""

    def __init__(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        penguin_id: UUID,
        manifest: AgentManifest,
        url: str = "http://localhost",
        port: int = 3773,
        version: str = "1.0.0",
        description: Optional[str] = None,
        debug: bool = False,
        static_dir: Optional[Path] = None,
        lifespan: Optional[Lifespan] = None,
        routes: Optional[Sequence[Route]] = None,
        middleware: Optional[Sequence[Middleware]] = None
    ):
        """Initialize Pebble application.

        Args:
            manifest: Agent manifest to serve
            storage: Storage backend (defaults to InMemoryStorage)
            scheduler: Task scheduler (defaults to InMemoryScheduler)
            penguin_id: Unique server identifier
            url: Server URL
            version: Server version
            description: Server description
            debug: Enable debug mode
            static_dir: Optional custom static files directory (defaults to bindu's static dir)
            lifespan: Optional custom lifespan
            routes: Optional custom routes
            middleware: Optional middleware
        """
        # Create default lifespan if none provided
        if lifespan is None:
            lifespan = self._create_default_lifespan(storage, scheduler, manifest)

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            lifespan=lifespan,
        )

        self.penguin_id = penguin_id
        self.url = url
        self.version = version
        self.description = description
        self.manifest = manifest
        self.static_dir = static_dir
        self.default_input_modes = ["application/json"]
        self.default_output_modes = ["application/json"]

        # TaskManager will be initialized in lifespan
        self.task_manager: Optional[TaskManager] = None
        self._storage = storage
        self._scheduler = scheduler

        # Setup
        self._agent_card_json_schema: bytes | None = None
        
        # Agent card and protocol endpoints
        self.router.add_route(
            "/.well-known/agent.json", 
            self._wrap_agent_card_endpoint, 
            methods=["HEAD", "GET", "OPTIONS"]
        )
        self.router.add_route("/", self._wrap_agent_run_endpoint, methods=["POST"])
        
        # Static file endpoints
        self.router.add_route("/docs", self._wrap_docs_endpoint, methods=["GET"])
        self.router.add_route("/docs.html", self._wrap_docs_endpoint, methods=["GET"])
        self.router.add_route("/agent.html", self._wrap_agent_page_endpoint, methods=["GET"])
        self.router.add_route("/chat.html", self._wrap_chat_page_endpoint, methods=["GET"])
        self.router.add_route("/storage.html", self._wrap_storage_page_endpoint, methods=["GET"])
        self.router.add_route("/common.js", self._wrap_common_js_endpoint, methods=["GET"])
        self.router.add_route("/common.css", self._wrap_common_css_endpoint, methods=["GET"])
        self.router.add_route("/components/layout.js", self._wrap_layout_js_endpoint, methods=["GET"])
        self.router.add_route("/components/header.html", self._wrap_header_component_endpoint, methods=["GET"])
        self.router.add_route("/components/footer.html", self._wrap_footer_component_endpoint, methods=["GET"])
        
        # DID endpoints
        self.router.add_route("/did/resolve", self._wrap_did_resolve_endpoint, methods=["GET", "POST"])
        self.router.add_route("/agent/info", self._wrap_agent_info_endpoint, methods=["GET"])

    def _create_default_lifespan(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        manifest: AgentManifest,
    ) -> Lifespan:
        """Create default lifespan that manages TaskManager lifecycle."""

        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            # Initialize TaskManager and enter its context
            task_manager = TaskManager(scheduler=scheduler, storage=storage, manifest=manifest)
            async with task_manager:
                # Store reference for use in endpoints
                app.task_manager = task_manager
                yield

        return lifespan

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and (self.task_manager is None or not self.task_manager.is_running):
            raise RuntimeError("TaskManager was not properly initialized.")
        await super().__call__(scope, receive, send)

    # Wrapper methods to pass app instance to endpoint functions
    async def _wrap_agent_card_endpoint(self, request: Request) -> Response:
        """Wrapper for agent card endpoint."""
        return await agent_card_endpoint(self, request)

    async def _wrap_agent_run_endpoint(self, request: Request) -> Response:
        """Wrapper for agent run endpoint."""
        return await agent_run_endpoint(self, request)

    async def _wrap_did_resolve_endpoint(self, request: Request) -> Response:
        """Wrapper for DID resolve endpoint."""
        return await did_resolve_endpoint(self, request)

    async def _wrap_agent_info_endpoint(self, request: Request) -> Response:
        """Wrapper for agent info endpoint."""
        return await agent_info_endpoint(self, request)

    # Static file endpoint wrappers
    async def _wrap_docs_endpoint(self, request: Request) -> Response:
        """Wrapper for docs endpoint."""
        return await docs_endpoint(request, self.static_dir)

    async def _wrap_agent_page_endpoint(self, request: Request) -> Response:
        """Wrapper for agent page endpoint."""
        return await agent_page_endpoint(request, self.static_dir)

    async def _wrap_chat_page_endpoint(self, request: Request) -> Response:
        """Wrapper for chat page endpoint."""
        return await chat_page_endpoint(request, self.static_dir)

    async def _wrap_storage_page_endpoint(self, request: Request) -> Response:
        """Wrapper for storage page endpoint."""
        return await storage_page_endpoint(request, self.static_dir)

    async def _wrap_common_js_endpoint(self, request: Request) -> Response:
        """Wrapper for common js endpoint."""
        return await common_js_endpoint(request, self.static_dir)

    async def _wrap_common_css_endpoint(self, request: Request) -> Response:
        """Wrapper for common css endpoint."""
        return await common_css_endpoint(request, self.static_dir)

    async def _wrap_layout_js_endpoint(self, request: Request) -> Response:
        """Wrapper for layout js endpoint."""
        return await layout_js_endpoint(request, self.static_dir)

    async def _wrap_header_component_endpoint(self, request: Request) -> Response:
        """Wrapper for header component endpoint."""
        return await header_component_endpoint(request, self.static_dir)

    async def _wrap_footer_component_endpoint(self, request: Request) -> Response:
        """Wrapper for footer component endpoint."""
        return await footer_component_endpoint(request, self.static_dir)
