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
from typing import Any, AsyncIterator, Callable, Sequence
from uuid import UUID, uuid4

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Lifespan, Receive, Scope, Send

from bindu.common.models import AgentManifest, TelemetryConfig
from bindu.settings import app_settings

from .middleware import Auth0Middleware
from .scheduler.memory_scheduler import InMemoryScheduler
from .storage.memory_storage import InMemoryStorage
from .task_manager import TaskManager
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.applications")


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
        telemetry_config: TelemetryConfig | None = None,
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
            telemetry_config: Optional telemetry configuration (defaults to disabled)
        """
        # Generate penguin_id if not provided
        if penguin_id is None:
            penguin_id = uuid4()

        # Store telemetry config for lifespan
        self._telemetry_config = telemetry_config or TelemetryConfig()

        # Create default lifespan if none provided
        if lifespan is None:
            lifespan = self._create_default_lifespan(storage, scheduler, manifest)

        # Setup middleware chain
        from bindu.utils import get_x402_extension_from_capabilities

        x402_ext = get_x402_extension_from_capabilities(manifest)
        payment_requirements_for_middleware = (
            self._create_payment_requirements(x402_ext, manifest, resource_suffix="/")
            if x402_ext
            else None
        )

        middleware_list = self._setup_middleware(
            middleware,
            x402_ext,
            payment_requirements_for_middleware,
            manifest,
            auth_enabled,
        )

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
        self._x402_ext = x402_ext
        self._payment_session_manager = None
        self._payment_requirements = None
        self._paywall_config = None

        # Initialize payment session manager and payment config if x402 enabled
        if x402_ext and payment_requirements_for_middleware:
            self._setup_payment_session_manager(
                manifest, payment_requirements_for_middleware
            )

        # In-memory not a good practice, but for development purposes
        # in production, use a database or redis
        self.payment_sessions: dict[str, dict[str, Any]] = {}

        # Register all routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all application routes."""
        from .endpoints import (
            agent_card_endpoint,
            agent_run_endpoint,
            did_resolve_endpoint,
            skill_detail_endpoint,
            skill_documentation_endpoint,
            skills_list_endpoint,
        )

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

        if self._x402_ext:
            self._register_payment_endpoints()

    def _register_payment_endpoints(self) -> None:
        """Register payment session endpoints."""
        from .endpoints import (
            payment_capture_endpoint,
            payment_status_endpoint,
            start_payment_session_endpoint,
        )

        self._add_route(
            "/api/start-payment-session",
            start_payment_session_endpoint,
            ["POST"],
            with_app=True,
        )
        self._add_route(
            "/payment-capture",
            payment_capture_endpoint,
            ["GET"],
            with_app=True,
        )
        self._add_route(
            "/api/payment-status/{session_id}",
            payment_status_endpoint,
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
            if self._telemetry_config.enabled:
                self._setup_observability()

            # Start payment session manager cleanup task if x402 enabled
            if app._payment_session_manager:
                await app._payment_session_manager.start_cleanup_task()

            # Start TaskManager
            task_manager = TaskManager(
                scheduler=scheduler, storage=storage, manifest=manifest
            )
            async with task_manager:
                app.task_manager = task_manager
                yield

            # Stop payment session manager cleanup task
            if app._payment_session_manager:
                await app._payment_session_manager.stop_cleanup_task()

        return lifespan

    def _setup_observability(self) -> None:
        """Set up OpenTelemetry observability."""
        from bindu.observability import setup as setup_observability

        config = self._telemetry_config
        try:
            setup_observability(
                oltp_endpoint=config.endpoint,
                oltp_service_name=config.service_name,
                verbose_logging=config.verbose_logging,
                service_version=config.service_version,
                deployment_environment=config.deployment_environment,
                batch_max_queue_size=config.batch_max_queue_size,
                batch_schedule_delay_millis=config.batch_schedule_delay_millis,
                batch_max_export_batch_size=config.batch_max_export_batch_size,
                batch_export_timeout_millis=config.batch_export_timeout_millis,
            )
            if config.verbose_logging:
                logger.info(
                    "OpenInference telemetry initialized in lifespan",
                    endpoint=config.endpoint or "console",
                    service_name=config.service_name or "bindu-agent",
                )
        except Exception as exc:
            logger.warning("OpenInference telemetry setup failed", error=str(exc))

    def _create_payment_requirements(
        self,
        x402_ext: Any,
        manifest: AgentManifest,
        resource_suffix: str = "/",
    ) -> list[Any] | None:
        """Create payment requirements for X402 extension.

        Args:
            x402_ext: X402 extension instance
            manifest: Agent manifest
            resource_suffix: Suffix to append to manifest URL for resource path

        Returns:
            List of PaymentRequirements or None
        """
        if not x402_ext:
            return None

        from x402.common import process_price_to_atomic_amount
        from x402.types import PaymentRequirements, SupportedNetworks
        from typing import cast

        max_amount_required, asset_address, eip712_domain = (
            process_price_to_atomic_amount(x402_ext.amount, x402_ext.network)
        )

        return [
            PaymentRequirements(
                scheme="exact",
                network=cast(SupportedNetworks, x402_ext.network),
                asset=asset_address,
                max_amount_required=max_amount_required,
                resource=f"{manifest.url}{resource_suffix}",
                description=f"Payment required to use {manifest.name}",
                mime_type="",
                pay_to=x402_ext.pay_to_address,
                max_timeout_seconds=60,
                output_schema={
                    "input": {
                        "type": "http",
                        "method": "POST",
                        "discoverable": True,
                    },
                    "output": {},
                },
                extra=eip712_domain,
            )
        ]

    def _setup_middleware(
        self,
        middleware: Sequence[Middleware] | None,
        x402_ext: Any,
        payment_requirements: list[Any] | None,
        manifest: AgentManifest,
        auth_enabled: bool,
    ) -> list[Middleware]:
        """Set up middleware chain with X402 and Auth0 middleware.

        Args:
            middleware: Custom middleware to include
            x402_ext: X402 extension instance
            payment_requirements: Payment requirements for X402
            manifest: Agent manifest
            auth_enabled: Whether authentication is enabled

        Returns:
            List of configured middleware
        """
        middleware_list = list(middleware) if middleware else []

        # Add X402 middleware if configured
        if x402_ext and payment_requirements:
            from .middleware import X402Middleware

            logger.info(
                f"X402 payment middleware enabled: "
                f"{x402_ext.amount} {x402_ext.token} on {x402_ext.network})"
            )

            facilitator_config = {"url": app_settings.x402.facilitator_url}
            x402_middleware = Middleware(
                X402Middleware,
                manifest=manifest,
                facilitator_config=facilitator_config,
                x402_ext=x402_ext,
                payment_requirements=payment_requirements,
            )
            middleware_list.insert(0, x402_middleware)

        # Add authentication middleware if enabled
        if auth_enabled and app_settings.auth.enabled:
            auth_middleware = self._create_auth_middleware()
            # Add auth middleware after X402 (if present)
            middleware_list.insert(1 if x402_ext else 0, auth_middleware)

        return middleware_list

    def _create_auth_middleware(self) -> Middleware:
        """Create authentication middleware based on provider.

        Returns:
            Configured auth middleware

        Raises:
            ValueError: If authentication provider is unknown
        """
        provider = app_settings.auth.provider.lower()

        if provider == "auth0":
            logger.info("Auth0 authentication enabled")
            return Middleware(Auth0Middleware, auth_config=app_settings.auth)
        else:
            logger.error(f"Unknown authentication provider: {provider}")
            raise ValueError(
                f"Unknown authentication provider: '{provider}'. "
                f"Supported providers: auth0, cognito, azure, custom"
            )

    def _setup_payment_session_manager(
        self,
        manifest: AgentManifest,
        payment_requirements_for_middleware: list[Any],
    ) -> None:
        """Initialize payment session manager and related configuration.

        Args:
            manifest: Agent manifest
            payment_requirements_for_middleware: Payment requirements from middleware setup
        """
        from bindu.server.middleware.x402.payment_session_manager import (
            PaymentSessionManager,
        )
        from x402.types import PaywallConfig
        import os

        self._payment_session_manager = PaymentSessionManager()

        # Create payment requirements for endpoints (with /payment-capture resource)
        self._payment_requirements = [
            req.model_copy(update={"resource": f"{manifest.url}/payment-capture"})
            for req in payment_requirements_for_middleware
        ]

        self._paywall_config = PaywallConfig(
            cdp_client_key=os.getenv("CDP_CLIENT_KEY") or "",
            app_name=f"{manifest.name} - x402 Payment",
            app_logo="/assets/light.svg",
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests with TaskManager validation."""
        if scope["type"] == "http" and (
            self.task_manager is None or not self.task_manager.is_running
        ):
            raise RuntimeError("TaskManager was not properly initialized.")
        await super().__call__(scope, receive, send)
