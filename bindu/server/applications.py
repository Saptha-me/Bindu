# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""
Bindu Application Server Module.

This module provides the core BinduApplication class - a Starlette-based ASGI application
that serves AI agents following the A2A (Agent-to-Agent) protocol.

"""

from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncIterator, Callable, Sequence
from uuid import UUID, uuid4

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Lifespan, Receive, Scope, Send

from bindu.common.models import AgentManifest
from bindu.settings import app_settings

from .endpoints import (
    agent_card_endpoint,
    agent_run_endpoint,
    did_resolve_endpoint,
    skill_detail_endpoint,
    skill_documentation_endpoint,
    skills_list_endpoint,
)
from .middleware import Auth0Middleware
from .scheduler.memory_scheduler import InMemoryScheduler
from .storage.memory_storage import InMemoryStorage
from .task_manager import TaskManager


class BinduApplication(Starlette):
    """Bindu application class for creating Bindu-compatible servers."""

    def __init__(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        manifest: AgentManifest,
        penguin_id: UUID | None = None,
        url: str = "http://localhost",
        port: int = 3773,
        version: str = "1.0.0",
        description: str | None = None,
        debug: bool = False,
        lifespan: Lifespan | None = None,
        routes: Sequence[Route] | None = None,
        middleware: Sequence[Middleware] | None = None,
        auth_enabled: bool = False,
        telemetry_enabled: bool = False,
        oltp_endpoint: str | None = None,
        oltp_service_name: str | None = None,
        oltp_verbose_logging: bool = False,
        oltp_service_version: str = "1.0.0",
        oltp_deployment_environment: str = "production",
        oltp_batch_max_queue_size: int = 2048,
        oltp_batch_schedule_delay_millis: int = 5000,
        oltp_batch_max_export_batch_size: int = 512,
        oltp_batch_export_timeout_millis: int = 30000,
    ):
        """Initialize Bindu application.

        Args:
            manifest: Agent manifest to serve
            storage: Storage backend (defaults to InMemoryStorage)
            scheduler: Task scheduler (defaults to InMemoryScheduler)
            penguin_id: Unique server identifier (auto-generated if not provided)
            url: Server URL
            version: Server version
            description: Server description
            debug: Enable debug mode
            lifespan: Optional custom lifespan
            routes: Optional custom routes
            middleware: Optional middleware
            auth_enabled: Enable Auth0 authentication middleware
            telemetry_enabled: Enable OpenTelemetry observability
            oltp_endpoint: OTLP endpoint URL for telemetry
            oltp_service_name: Service name for telemetry traces
            oltp_verbose_logging: Enable verbose telemetry logging
            oltp_service_version: Service version for traces
            oltp_deployment_environment: Deployment environment (dev/staging/production)
            oltp_batch_max_queue_size: Max queue size for batch processor
            oltp_batch_schedule_delay_millis: Schedule delay for batch processor
            oltp_batch_max_export_batch_size: Max export batch size
            oltp_batch_export_timeout_millis: Export timeout in milliseconds
        """
        # Generate penguin_id if not provided
        if penguin_id is None:
            penguin_id = uuid4()

        # Store telemetry config for lifespan
        self._telemetry_enabled = telemetry_enabled
        self._oltp_endpoint = oltp_endpoint
        self._oltp_service_name = oltp_service_name
        self._oltp_verbose_logging = oltp_verbose_logging
        self._oltp_service_version = oltp_service_version
        self._oltp_deployment_environment = oltp_deployment_environment
        self._oltp_batch_max_queue_size = oltp_batch_max_queue_size
        self._oltp_batch_schedule_delay_millis = oltp_batch_schedule_delay_millis
        self._oltp_batch_max_export_batch_size = oltp_batch_max_export_batch_size
        self._oltp_batch_export_timeout_millis = oltp_batch_export_timeout_millis

        # Create default lifespan if none provided
        if lifespan is None:
            lifespan = self._create_default_lifespan(storage, scheduler, manifest)

        # Add authentication middleware if enabled
        middleware_list = list(middleware) if middleware else []
        if auth_enabled and app_settings.auth.enabled:
            from bindu.utils.logging import get_logger

            logger = get_logger("bindu.server.applications")

            # Select middleware based on provider
            provider = app_settings.auth.provider.lower()

            if provider == "auth0":
                logger.info("Auth0 authentication enabled")
                auth_middleware = Middleware(
                    Auth0Middleware, auth_config=app_settings.auth
                )
            # elif provider == "cognito": # TODO: Implement Cognito authentication
            #     logger.info("AWS Cognito authentication enabled")
            #     from .middleware.auth_cognito import CognitoMiddleware

            #     auth_middleware = Middleware(
            #         CognitoMiddleware, auth_config=app_settings.auth
            #     )
            # elif provider == "azure":
            #     logger.warning("Azure AD authentication not yet implemented")
            #     raise NotImplementedError(
            #         "Azure AD authentication is not yet implemented. "
            #         "Use 'auth0' provider or implement AzureADMiddleware."
            #     )
            # elif provider == "custom":
            #     logger.warning("Custom JWT authentication not yet implemented")
            #     raise NotImplementedError(
            #         "Custom JWT authentication is not yet implemented. "
            #         "Use 'auth0' provider or implement CustomJWTMiddleware."
            #     )
            else:
                logger.error(f"Unknown authentication provider: {provider}")
                raise ValueError(
                    f"Unknown authentication provider: '{provider}'. Supported providers: auth0, cognito, azure, custom"
                )

            # Add auth middleware to the beginning of middleware chain
            middleware_list.insert(0, auth_middleware)

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware_list if middleware_list else None,
            lifespan=lifespan,
        )

        self.penguin_id = penguin_id
        self.url = url
        self.version = version
        self.description = description
        self.manifest = manifest
        self.default_input_modes = ["application/json"]
        self.task_manager: TaskManager | None = None
        self._storage = storage
        self._scheduler = scheduler
        self._agent_card_json_schema: bytes | None = None

        # Register all routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all application routes."""
        # Protocol endpoints
        self._add_route(
            "/.well-known/agent.json",
            agent_card_endpoint,
            ["HEAD", "GET", "OPTIONS"],
            with_app=True,
        )
        self._add_route("/", agent_run_endpoint, ["POST"], with_app=True)

        # DID endpoints
        self._add_route(
            "/did/resolve", did_resolve_endpoint, ["GET", "POST"], with_app=True
        )

        # Skills endpoints
        self._add_route(
            "/agent/skills",
            skills_list_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/agent/skills/{skill_id}",
            skill_detail_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/agent/skills/{skill_id}/documentation",
            skill_documentation_endpoint,
            ["GET"],
            with_app=True,
        )

    def _add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: list[str],
        with_app: bool = False,
    ) -> None:
        """Add a route with appropriate wrapper.

        Args:
            path: Route path
            endpoint: Endpoint function
            methods: HTTP methods
            with_app: Pass app instance to endpoint
        """
        if with_app:
            handler = partial(self._wrap_with_app, endpoint)
        else:
            handler = endpoint

        self.router.add_route(path, handler, methods=methods)

    async def _wrap_with_app(self, endpoint: Callable, request: Request) -> Response:
        """Wrap endpoint that requires app instance."""
        return await endpoint(self, request)

    def _create_default_lifespan(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        manifest: AgentManifest,
    ) -> Lifespan:
        """Create default Lifespan that manages TaskManager lifecycle and observability."""

        @asynccontextmanager
        async def lifespan(app: BinduApplication) -> AsyncIterator[None]:
            # Setup observability if enabled
            if self._telemetry_enabled:
                from bindu.observability import setup as setup_observability
                from bindu.utils.logging import get_logger

                logger = get_logger("bindu.server.applications")

                try:
                    setup_observability(
                        oltp_endpoint=self._oltp_endpoint,
                        oltp_service_name=self._oltp_service_name,
                        verbose_logging=self._oltp_verbose_logging,
                        service_version=self._oltp_service_version,
                        deployment_environment=self._oltp_deployment_environment,
                        batch_max_queue_size=self._oltp_batch_max_queue_size,
                        batch_schedule_delay_millis=self._oltp_batch_schedule_delay_millis,
                        batch_max_export_batch_size=self._oltp_batch_max_export_batch_size,
                        batch_export_timeout_millis=self._oltp_batch_export_timeout_millis,
                    )
                    if self._oltp_verbose_logging:
                        logger.info(
                            "OpenInference telemetry initialized in lifespan",
                            endpoint=self._oltp_endpoint or "console",
                            service_name=self._oltp_service_name or "bindu-agent",
                        )
                except Exception as exc:
                    logger.warning(
                        "OpenInference telemetry setup failed", error=str(exc)
                    )

            # Start TaskManager
            task_manager = TaskManager(
                scheduler=scheduler, storage=storage, manifest=manifest
            )
            async with task_manager:
                app.task_manager = task_manager
                yield

        return lifespan

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests with TaskManager validation."""
        if scope["type"] == "http" and (
            self.task_manager is None or not self.task_manager.is_running
        ):
            raise RuntimeError("TaskManager was not properly initialized.")
        await super().__call__(scope, receive, send)
