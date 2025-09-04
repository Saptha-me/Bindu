from contextlib import asynccontextmanager
from typing import Any, Union, Sequence, Optional, AsyncIterator
from uuid import UUID
from pathlib import Path
from pebbling.common.models import AgentManifest

from .scheduler.memory_scheduler import InMemoryScheduler
from .scheduler.redis_scheduler import RedisScheduler
from .storage.memory_storage import InMemoryStorage
from .storage.postgres_storage import PostgreSQLStorage
from .storage.qdrant_storage import QdrantStorage
from .task_manager import TaskManager
from .routers.run import agent_run_endpoint

from pebbling.common.protocol.types import AgentCard
from pebbling.common.protocol.types import agent_card_ta
from pebbling.common.protocol.types import pebble_request_ta
from pebbling.common.protocol.types import pebble_response_ta

from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response, FileResponse
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
        manifest: AgentManifest,
        url: str = "http://localhost",
        port: int = 3773,
        version: str = "1.0.0",
        description: Optional[str] = None,
        debug: bool = False,
        lifespan: Optional[Lifespan] = None,
        routes: Optional[Sequence[Route]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[dict[Any, ExceptionHandler]] = None
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
            lifespan: Optional custom lifespan
            routes: Optional custom routes
            middleware: Optional middleware
            exception_handlers: Optional exception handlers
        """
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
        self.manifest = manifest
        self.default_input_modes = ['application/json']
        self.default_output_modes = ['application/json']

        # Initialize TaskManager following Pebble pattern
        self.task_manager = TaskManager(scheduler=scheduler, storage=storage, manifest=manifest)

        # Setup
        self._agent_card_json_schema: bytes | None = None
        self.router.add_route('/.well-known/agent.json', self._agent_card_endpoint, methods=['HEAD', 'GET', 'OPTIONS'])
        self.router.add_route('/', self._agent_run_endpoint, methods=['POST'])
        self.router.add_route('/docs', self._docs_endpoint, methods=['GET'])


    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'http' and not self.task_manager.is_running:
            raise RuntimeError('TaskManager was not properly initialized.')
        await super().__call__(scope, receive, send)

    async def _agent_card_endpoint(self, request: Request) -> Response:
        if self._agent_card_json_schema is None:
            agent_card = AgentCard(
                name=self.manifest.name,
                description=self.manifest.description or 'An AI agent exposed as an Pebble agent.',
                url=self.url,
                version=self.version,
                protocol_version='0.2.5',
                skills=self.manifest.skills,
                capabilities=self.manifest.capabilities,
            )
            self._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)
        return Response(content=self._agent_card_json_schema, media_type='application/json')

    async def _docs_endpoint(self, request: Request) -> Response:
        """Serve the documentation interface."""
        docs_path = Path(__file__).parent / 'static' / 'docs.html'
        return FileResponse(docs_path, media_type='text/html')

    async def _agent_run_endpoint(self, request: Request) -> Response:
        """This is the main endpoint for the Pebble server.

        Although the specification allows freedom of choice and implementation, I'm pretty sure about some decisions.

        1. The server will always either send a "submitted" or a "failed" on `tasks/send`.
            Never a "completed" on the first message.
        2. There are three possible ends for the task:
            2.1. The task was "completed" successfully.
            2.2. The task was "canceled".
            2.3. The task "failed".
        3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
        """
        data = await request.body()
        pebble_request = pebble_request_ta.validate_json(data)

        if pebble_request['method'] == 'message/send':
            jsonrpc_response = await self.task_manager.send_message(pebble_request)
        elif pebble_request['method'] == 'tasks/get':
            jsonrpc_response = await self.task_manager.get_task(pebble_request)
        elif pebble_request['method'] == 'tasks/cancel':
            jsonrpc_response = await self.task_manager.cancel_task(pebble_request)
        else:
            raise NotImplementedError(f'Method {pebble_request["method"]} not implemented.')
        return Response(
            content=pebble_response_ta.dump_json(jsonrpc_response, by_alias=True), media_type='application/json'
        )
    


