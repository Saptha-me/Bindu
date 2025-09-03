from contextlib import asynccontextmanager
from typing import Any, Union, Sequence, Optional, AsyncIterator
from uuid import UUID

from .server.scheduler.memory_scheduler import InMemoryScheduler
from .server.scheduler.redis_scheduler import RedisScheduler
from .server.storage.memory_storage import InMemoryStorage
from .server.storage.postgres_storage import PostgreSQLStorage
from .server.storage.qdrant_storage import QdrantStorage
from .server.protocol.types import AgentManifest, AgentSkill
from .task_manager import TaskManager
from .routers.run import agent_run_endpoint

from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.types import ExceptionHandler, Scope, Receive, Send
from starlette.types import Lifespan
from starlette.applications import Starlette

class PebbleApplication(Starlette):
    """Pebble application class for creating Pebble-compatible servers."""
    
    def __init__(
        self,
        storage: Union[InMemoryStorage, PostgreSQLStorage, QdrantStorage],
        scheduler: Union[InMemoryScheduler, RedisScheduler],
        penguin_id: UUID,
        agents: list[AgentManifest],
        skills: Optional[list[AgentSkill]] = None,
        url: str = "http://localhost",
        port: int = 3773,
        version: str = "1.0.0",
        description: Optional[str] = None,
        debug: bool = False,
        routes: Optional[Sequence[Route]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[dict[Any, ExceptionHandler]] = None
    ):
        """Initialize Pebble application.
        
        Args:
            agents: List of agent manifests to serve
            storage: Storage backend (defaults to InMemoryStorage)
            scheduler: Task scheduler (defaults to InMemoryScheduler)
            penguin_id: Unique server identifier
            url: Server URL
            version: Server version
            description: Server description
            debug: Enable debug mode
            routes: Optional custom routes
            middleware: Optional middleware
            exception_handlers: Optional exception handlers
        """
        lifespan = _default_lifespan

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            exception_handlers=exception_handlers,
            lifespan=lifespan,
        )

        self.penguin_id = penguin_id
        self.url = url
        self.version = version
        self.description = description
        self.skills = skills or []
        self.agents = agents
        self.default_input_modes = ['application/json']
        self.default_output_modes = ['application/json']

        # Store scheduler and storage for lifespan initialization
        self._scheduler = scheduler
        self._storage = storage
        self.task_manager: TaskManager | None = None

        # Setup
        self._agent_card_json_schema: bytes | None = None
        self.router.add_route('/', agent_run_endpoint, methods=['POST'])
        # self.router.add_route("/agents", agents.router)
        # self.router.add_route("/messages", messages.router)
        # self.router.add_route("/tasks", tasks.router)
        # self.router.add_route("/health", health.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await super().__call__(scope, receive, send)

    
@asynccontextmanager
async def _default_lifespan(app: PebbleApplication) -> AsyncIterator[None]:
    # Initialize TaskManager during application startup
    app.task_manager = TaskManager(scheduler=app._scheduler, storage=app._storage)
    
    async with app.task_manager:
        yield
    


