#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""bindufy decorator for transforming regular agents into secure, networked agents."""

import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import urlparse
from uuid import UUID

from bindu.common.models import (
    AgentManifest,
    DeploymentConfig,
    TelemetryConfig,
)
from bindu.extensions.x402 import X402AgentExtension
from bindu.penguin.did_setup import initialize_did_extension
from bindu.penguin.manifest import create_manifest, validate_agent_function
from bindu.penguin.mtls_setup import initialize_mtls_extension
from bindu.settings import app_settings
from bindu.utils import add_extension_to_capabilities
from bindu.utils.config import (
    create_auth_config_from_env,
    create_storage_config_from_env,
    create_scheduler_config_from_env,
    create_sentry_config_from_env,
    create_vault_config_from_env,
    load_config_from_env,
    resolve_key_directory,
    update_auth_settings,
    update_vault_settings,
)
from bindu.utils.display import prepare_server_display
from bindu.utils.logging import get_logger
from bindu.utils.server_runner import run_server as start_uvicorn_server
from bindu.utils.skills import load_skills

# Configure logging for the module
logger = get_logger("bindu.penguin.bindufy")

# Payment defaults for X402 extension
DEFAULT_TOKEN = "USDC"
DEFAULT_NETWORK = "base-sepolia"

# Default protocol version
DEFAULT_PROTOCOL_VERSION = "1.0.0"


def _generate_agent_id(validated_config: Dict[str, Any]) -> UUID:
    """Generate deterministic agent ID from author + name.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        UUID: Deterministic agent ID
    """
    import hashlib

    author = validated_config.get("author", "")
    agent_name = validated_config.get("name", "")

    # Create deterministic ID from author + agent_name
    deterministic_string = f"{author}:{agent_name}"
    agent_id_hex = hashlib.sha256(deterministic_string.encode()).hexdigest()[:32]
    # Convert to UUID for type compatibility
    agent_id = UUID(agent_id_hex)
    logger.info(f"Generated deterministic agent_id from author+name: {agent_id}")
    return agent_id


def _normalize_execution_costs(execution_cost: Any) -> list[dict[str, Any]]:
    """Normalize execution_cost to list of cost entries.

    Args:
        execution_cost: Single dict or list of dicts

    Returns:
        List of normalized cost dictionaries

    Raises:
        ValueError: If execution_cost format is invalid
    """
    # Normalize to list
    if isinstance(execution_cost, dict):
        cost_entries = [execution_cost]
    elif isinstance(execution_cost, list):
        if not execution_cost:
            raise ValueError("execution_cost list cannot be empty when configured")
        cost_entries = execution_cost
    else:
        raise ValueError("execution_cost must be either a dict or a list of dicts")

    normalized_costs: list[dict[str, Any]] = []

    for idx, cost in enumerate(cost_entries):
        if not isinstance(cost, dict):
            raise ValueError("Each entry in execution_cost list must be a dictionary")

        amount = cost.get("amount")
        token = cost.get("token", DEFAULT_TOKEN)
        network = cost.get("network", DEFAULT_NETWORK)
        pay_to_address = cost.get("pay_to_address")

        if not amount:
            raise ValueError(
                "execution_cost.amount is required when execution_cost is configured"
            )

        logger.info(f"Execution cost option {idx + 1}: {amount} {token} on {network}")

        normalized_costs.append(
            {
                "amount": amount,
                "token": token,
                "network": network,
                "pay_to_address": pay_to_address,
            }
        )

    return normalized_costs


def _setup_x402_extension(normalized_costs: list[dict[str, Any]]) -> X402AgentExtension:
    """Create X402 extension from normalized costs.

    Args:
        normalized_costs: List of normalized cost dictionaries

    Returns:
        X402AgentExtension instance
    """
    primary = normalized_costs[0]
    x402_extension = X402AgentExtension(
        amount=primary["amount"],
        token=primary.get("token", DEFAULT_TOKEN),
        network=primary.get("network", DEFAULT_NETWORK),
        pay_to_address=primary.get("pay_to_address") or "",
        required=True,
        payment_options=normalized_costs,
    )

    logger.info(f"X402 extension created: {x402_extension}")
    return x402_extension


def _register_in_hydra(
    agent_id_str: str,
    validated_config: Dict[str, Any],
    agent_url: str,
    did_extension: Any,
    caller_dir: Path,
) -> Any | None:
    """Register agent in Hydra OAuth2 server if enabled.

    Args:
        agent_id_str: Agent ID as string
        validated_config: Validated configuration dictionary
        agent_url: Agent URL
        did_extension: DID extension instance
        caller_dir: Caller directory path

    Returns:
        AgentCredentials if successful, None otherwise
    """
    if not (app_settings.auth.enabled and app_settings.auth.provider == "hydra"):
        return None

    logger.info(
        "Registering agent in Hydra OAuth2 server with DID-based authentication..."
    )
    import asyncio
    from bindu.auth.hydra.registration import register_agent_in_hydra

    credentials = asyncio.run(
        register_agent_in_hydra(
            agent_id=agent_id_str,
            agent_name=validated_config["name"],
            agent_url=agent_url,
            did=did_extension.did,
            credentials_dir=caller_dir / app_settings.did.pki_dir,
            did_extension=did_extension,
        )
    )

    if credentials:
        logger.info(
            f"✅ Agent registered with OAuth client ID: {credentials.client_id}"
        )
    else:
        logger.warning(
            "⚠️  Agent registration in Hydra failed or was skipped. "
            "Authentication may not work correctly."
        )

    return credentials


def _setup_tunnel(
    tunnel_config: Any,
    port: int,
    manifest: AgentManifest,
    bindu_app: Any,
) -> str | None:
    """Set up tunnel if enabled and update URLs.

    Args:
        tunnel_config: Tunnel configuration
        port: Local port number
        manifest: Agent manifest to update
        bindu_app: Bindu application to update

    Returns:
        Tunnel URL if successful, None otherwise
    """
    if not (tunnel_config and tunnel_config.enabled):
        return None

    from bindu.tunneling.manager import TunnelManager

    logger.info("Tunnel enabled, creating public URL...")
    tunnel_config.local_port = port

    try:
        tunnel_manager = TunnelManager()
        tunnel_url = tunnel_manager.create_tunnel(
            local_port=port,
            config=tunnel_config,
            subdomain=tunnel_config.subdomain,
        )
        logger.info(f"✅ Tunnel created: {tunnel_url}")

        # Update manifest URL to use tunnel URL
        manifest.url = tunnel_url

        # Update BinduApplication URL to use tunnel URL
        bindu_app.url = tunnel_url

        # Invalidate cached agent card so it gets regenerated with new URL
        bindu_app._agent_card_json_schema = None

        return tunnel_url

    except Exception as e:
        logger.error(f"Failed to create tunnel: {e}")
        logger.warning("Continuing with local-only server...")
        return None


def _create_telemetry_config(validated_config: Dict[str, Any]) -> TelemetryConfig:
    """Create telemetry configuration from validated config.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        TelemetryConfig instance
    """
    return TelemetryConfig(
        enabled=validated_config["telemetry"],
        endpoint=validated_config.get("oltp_endpoint"),
        service_name=validated_config.get("oltp_service_name"),
        headers=validated_config.get("oltp_headers"),
        verbose_logging=validated_config.get("oltp_verbose_logging", False),
        service_version=validated_config.get("oltp_service_version", "1.0.0"),
        deployment_environment=validated_config.get(
            "oltp_deployment_environment", "production"
        ),
        batch_max_queue_size=validated_config.get("oltp_batch_max_queue_size", 2048),
        batch_schedule_delay_millis=validated_config.get(
            "oltp_batch_schedule_delay_millis", 5000
        ),
        batch_max_export_batch_size=validated_config.get(
            "oltp_batch_max_export_batch_size", 512
        ),
        batch_export_timeout_millis=validated_config.get(
            "oltp_batch_export_timeout_millis", 30000
        ),
    )


def _parse_deployment_url(
    deployment_config: DeploymentConfig | None,
) -> tuple[str, int]:
    """Parse deployment URL to extract host and port.

    Args:
        deployment_config: Deployment configuration object

    Returns:
        Tuple of (host, port)
    """
    if not deployment_config:
        return app_settings.network.default_host, app_settings.network.default_port

    parsed_url = urlparse(deployment_config.url)
    host = parsed_url.hostname or app_settings.network.default_host
    port = parsed_url.port or app_settings.network.default_port

    return host, port


def _create_deployment_config(
    validated_config: Dict[str, Any],
) -> DeploymentConfig | None:
    """Create deployment config from validated config dict.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        DeploymentConfig instance or None if invalid/missing
    """
    deploy_dict = validated_config.get("deployment")
    if not deploy_dict:
        return None

    missing = []

    if "url" not in deploy_dict:
        missing.append("deployment.url")

    if "expose" not in deploy_dict:
        missing.append("deployment.expose")

    if missing:
        raise ValueError(f"Missing required config field(s): {', '.join(missing)}")

    return DeploymentConfig(
        url=deploy_dict["url"],
        expose=deploy_dict["expose"],
        protocol_version=deploy_dict.get("protocol_version", "1.0.0"),
        proxy_urls=deploy_dict.get("proxy_urls"),
        cors_origins=deploy_dict.get("cors_origins"),
        openapi_schema=deploy_dict.get("openapi_schema"),
    )


def _bindufy_core(
    config: Dict[str, Any],
    handler_callable: Callable,
    run_server: bool = True,
    key_dir: str | Path | None = None,
    launch: bool = False,
    caller_dir: Path | None = None,
    skills_override: list | None = None,
    skip_handler_validation: bool = False,
    run_server_in_background: bool = False,
) -> AgentManifest:
    """Core bindufy logic shared by both Python and gRPC registration paths.

    This is the internal engine that transforms a config + callable into a
    fully running Bindu microservice with DID, auth, x402, A2A, scheduler,
    and storage. Both bindufy() (Python path) and BinduServiceImpl.RegisterAgent()
    (gRPC path) delegate to this function.

    Args:
        config: Raw or pre-validated configuration dictionary.
        handler_callable: The handler to execute tasks. Either a Python function
            (from bindufy()) or a GrpcAgentClient (from gRPC registration).
        run_server: If True, starts the uvicorn HTTP server.
        key_dir: Directory for storing DID keys.
        launch: If True, creates a public tunnel via FRP.
        caller_dir: Directory of the calling file (for skill/key resolution).
            Required for Python path, optional for gRPC path.
        skills_override: Pre-loaded skills list (from gRPC path where SDK sends
            skill content). If None, skills are loaded from config paths.
        skip_handler_validation: If True, skip validate_agent_function().
            Used for gRPC path where handler is a GrpcAgentClient.
        run_server_in_background: If True, start uvicorn in a background thread
            instead of blocking. Used by gRPC service so RegisterAgent can return.

    Returns:
        AgentManifest: The manifest for the bindufied agent.
    """
    if not isinstance(config, dict):
        raise TypeError("config must be a dictionary")

    # Load capability-specific configs from environment variables (webhooks, negotiation)
    config = load_config_from_env(config)

    # Validate and process configuration
    from .config_validator import ConfigValidator

    validated_config = ConfigValidator.validate_and_process(config)

    # Early validation for required author field
    if (
        not validated_config.get("author")
        or not str(validated_config["author"]).strip()
    ):
        raise ValueError("'author' is required in config and cannot be empty.")

    # Generate agent_id if not provided
    if "id" not in validated_config:
        agent_id = _generate_agent_id(validated_config)
    else:
        # Convert string ID to UUID if needed
        id_value = validated_config["id"]
        agent_id = UUID(id_value) if isinstance(id_value, str) else id_value

    # Convert to string once for reuse
    agent_id_str = str(agent_id)

    # Create config objects directly from environment and validated config
    deployment_config = _create_deployment_config(validated_config)
    storage_config = create_storage_config_from_env(validated_config)
    scheduler_config = create_scheduler_config_from_env(validated_config)
    sentry_config = create_sentry_config_from_env(validated_config)
    vault_config = create_vault_config_from_env(validated_config)
    auth_config = create_auth_config_from_env(validated_config)

    # Update vault settings before DID initialization (needed for key restoration)
    if vault_config:
        update_vault_settings(vault_config)

    # Create tunnel config only if launch parameter is True
    tunnel_config = None
    if launch:
        from bindu.tunneling.config import TunnelConfig

        tunnel_config = TunnelConfig(enabled=True)

    # Update app_settings.auth based on config
    if auth_config is not None:
        update_auth_settings(auth_config)

    # Validate handler if required (skipped for gRPC path)
    if not skip_handler_validation:
        handler_name = getattr(handler_callable, "__name__", "<unknown>")
        logger.info(f"Validating handler function: {handler_name}")
        validate_agent_function(handler_callable)

    logger.info(f"Agent ID: {agent_id}")

    # Determine key directory with fallback strategy.
    # resolve_key_directory returns the *parent* dir — initialize_did_extension
    # appends app_settings.did.pki_dir itself, so keys land at
    # <resolved_key_dir>/<pki_dir>.
    resolved_key_dir = resolve_key_directory(
        explicit_dir=key_dir,
        caller_dir=caller_dir or Path.cwd(),
        subdir=app_settings.did.pki_dir,
    )

    # Initialize DID extension with key management
    did_extension = initialize_did_extension(
        agent_id=agent_id,
        author=validated_config.get("author"),
        agent_name=validated_config.get("name"),
        key_dir=resolved_key_dir,
        recreate_keys=validated_config["recreate_keys"],
        key_password=validated_config.get("key_password"),
    )

    # Load skills: use override (gRPC path) or load from config paths (Python path)
    logger.info("Loading agent skills...")
    if skills_override is not None:
        skills_list = skills_override
    else:
        skills_list = load_skills(
            validated_config.get("skills") or [],
            caller_dir or Path.cwd(),
        )

    # Private skills follow the same loader contract as the public ones — same
    # file format, same on-disk layout, just kept apart so the public agent
    # card endpoint never sees them. `allowed_dids` is the allowlist of caller
    # DIDs that can read them through the auth-gated private endpoint.
    private_skills_list = (
        load_skills(
            validated_config.get("private_skills") or [],
            caller_dir or Path.cwd(),
        )
        if validated_config.get("private_skills")
        else []
    )
    allowed_dids_list = list(validated_config.get("allowed_dids") or [])

    # Set agent metadata for DID document
    agent_url = (
        deployment_config.url if deployment_config else app_settings.network.default_url
    )

    logger.info(f"DID Extension setup complete: {did_extension.did}")
    logger.info("Creating agent manifest...")

    # Update capabilities to include DID extension
    capabilities = add_extension_to_capabilities(
        validated_config.get("capabilities", {}), did_extension
    )

    # Only add x402 extension if execution_cost is configured
    execution_cost = validated_config.get("execution_cost")
    x402_extension = None

    if execution_cost:
        normalized_costs = _normalize_execution_costs(execution_cost)
        x402_extension = _setup_x402_extension(normalized_costs)

        # Add x402 extension to capabilities
        capabilities = add_extension_to_capabilities(capabilities, x402_extension)

    # Create agent manifest with loaded skills
    _manifest = create_manifest(
        agent_function=handler_callable,
        id=agent_id,
        did_extension=did_extension,
        name=validated_config["name"],
        description=validated_config["description"],
        skills=skills_list,
        capabilities=capabilities,
        agent_trust=validated_config["agent_trust"],
        version=validated_config["version"],
        url=agent_url,
        protocol_version=deployment_config.protocol_version
        if deployment_config
        else DEFAULT_PROTOCOL_VERSION,
        kind=validated_config["kind"],
        debug_mode=validated_config["debug_mode"],
        debug_level=validated_config["debug_level"],
        monitoring=validated_config["monitoring"],
        telemetry=validated_config["telemetry"],
        oltp_endpoint=validated_config.get("oltp_endpoint"),
        oltp_service_name=validated_config.get("oltp_service_name"),
        num_history_sessions=validated_config["num_history_sessions"],
        enable_system_message=validated_config.get("enable_system_message", True),
        enable_context_based_history=validated_config.get(
            "enable_context_based_history", False
        ),
        negotiation=validated_config.get("negotiation"),
        documentation_url=validated_config["documentation_url"],
        extra_metadata=validated_config["extra_metadata"],
        global_webhook_url=validated_config.get("global_webhook_url"),
        global_webhook_token=validated_config.get("global_webhook_token"),
        private_skills=private_skills_list,
        allowed_dids=allowed_dids_list,
    )

    # Log manifest creation
    skill_count = len(_manifest.skills) if _manifest.skills else 0
    logger.info(f"Agent '{did_extension.did}' successfully bindufied!")
    logger.debug(
        f"Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | {skill_count} skills | {_manifest.url}"
    )

    # Register agent in Hydra if authentication is enabled with Hydra provider
    credentials = _register_in_hydra(
        agent_id_str,
        validated_config,
        agent_url,
        did_extension,
        caller_dir or Path.cwd(),
    )

    # Bootstrap mTLS. Off by default (mtls.enabled=False) so existing
    # deployments are unaffected. When on, requires Hydra credentials because
    # step-ca's OIDC provisioner validates the cert request against Hydra.
    mtls_extension = initialize_mtls_extension(
        agent_id=agent_id_str,
        agent_did=did_extension.did,
        agent_url=agent_url,
        pki_dir=resolved_key_dir / app_settings.did.pki_dir,
        hydra_credentials=credentials,
    )
    if mtls_extension is not None:
        # Populate AgentTrust on the manifest so the cert fingerprint flows
        # into the agent card and downstream trust decisions.
        fingerprint = mtls_extension.cert_fingerprint
        if fingerprint is not None:
            _manifest.agent_trust["certificate_fingerprint"] = fingerprint
    elif app_settings.mtls.enabled and app_settings.mtls.require_client_cert:
        # Operator asked for strict mTLS but bootstrap failed — refuse to start
        # rather than fall through to plain HTTP and create a false sense of
        # security.
        raise RuntimeError(
            "mTLS is enabled with require_client_cert=True but cert bootstrap "
            "failed. Check step-ca reachability and Hydra OIDC config."
        )

    logger.info(f"Starting deployment for agent: {agent_id}")

    # Import server components (deferred to avoid circular import)
    from bindu.server import BinduApplication

    # Create telemetry configuration
    telemetry_config = _create_telemetry_config(validated_config)

    # Create Bindu application with configs. `url=agent_url` is load-bearing:
    # the agent-card endpoint reads `app.url` (not `manifest.url`) when
    # building /.well-known/agent.json, so without this the card advertises
    # the BinduApplication default of "http://localhost" — peers fetching
    # the card can't reach back. See bindu/server/endpoints/agent_card.py:126.
    bindu_app = BinduApplication(
        penguin_id=agent_id,
        manifest=_manifest,
        url=agent_url,
        version=validated_config["version"],
        auth_enabled=app_settings.auth.enabled,
        telemetry_config=telemetry_config,
        storage_config=storage_config,
        scheduler_config=scheduler_config,
        sentry_config=sentry_config,
        cors_origins=deployment_config.cors_origins if deployment_config else None,
        mtls_extension=mtls_extension,
    )

    # Parse deployment URL
    host, port = _parse_deployment_url(deployment_config)

    # Create tunnel if enabled
    tunnel_url = _setup_tunnel(tunnel_config, port, _manifest, bindu_app)

    # Start server if requested
    if run_server:
        # Display server startup banner
        prepare_server_display(
            host=host,
            port=port,
            agent_id=agent_id_str,
            agent_did=did_extension.did,
            client_id=credentials.client_id if credentials else None,
            client_secret=credentials.client_secret if credentials else None,
            tunnel_url=tunnel_url,
        )

        # When mTLS is configured and bootstrap succeeded, hand uvicorn the
        # cert/key/CA-bundle paths so the HTTP server runs over TLS with
        # mutual-auth peer verification.
        ssl_kwargs = (
            mtls_extension.get_uvicorn_ssl_kwargs()
            if mtls_extension is not None
            else None
        )
        if ssl_kwargs and agent_url.startswith("http://"):
            logger.warning(
                "mTLS is on but agent_url starts with http://; downstream callers "
                "will fail TLS. Set deployment URL to https://… to match."
            )

        if run_server_in_background:
            # Start uvicorn in a background thread (used by gRPC service)
            import threading

            server_thread = threading.Thread(
                target=start_uvicorn_server,
                args=(bindu_app,),
                kwargs={
                    "host": host,
                    "port": port,
                    "display_info": True,
                    "ssl_kwargs": ssl_kwargs,
                },
                daemon=True,
                name=f"uvicorn-{validated_config['name']}",
            )
            server_thread.start()
            logger.info(f"HTTP server started in background thread on {host}:{port}")
        else:
            # Run server blocking (normal Python bindufy path)
            start_uvicorn_server(
                bindu_app,
                host=host,
                port=port,
                display_info=True,
                ssl_kwargs=ssl_kwargs,
            )
    else:
        logger.info(
            "Server not started (run_server=False). Manifest returned for programmatic use."
        )

    return _manifest


def bindufy(
    config: Dict[str, Any],
    handler: Callable[[list[dict[str, Any]]], Any],
    run_server: bool = True,
    key_dir: str | Path | None = None,
    launch: bool = False,
) -> AgentManifest | None:
    """Transform an agent handler into a Bindu microservice.

    This is the main entry point for Python agents. It validates the handler,
    resolves the caller directory, and delegates to _bindufy_core() which
    handles DID, auth, x402, manifest creation, and server startup.

    Args:
        config: Configuration dictionary containing:
            - author: Agent author email (required)
            - name: Human-readable agent name
            - id: Unique agent identifier (optional, auto-generated if not provided)
            - description: Agent description
            - version: Agent version string (default: "1.0.0")
            - recreate_keys: Force regeneration of existing keys (default: True)
            - skills: List of agent skills/capabilities
            - env_file: Path to .env file (optional, for local development)
            - capabilities: Technical capabilities (streaming, notifications, etc.)
            - agent_trust: Trust and security configuration
            - kind: Agent type ('agent', 'team', or 'workflow') (default: "agent")
            - debug_mode: Enable debug logging (default: False)
            - debug_level: Debug verbosity level (default: 1)
            - monitoring: Enable monitoring/metrics (default: False)
            - telemetry: Enable telemetry collection (default: True)
            - num_history_sessions: Number of conversation histories to maintain (default: 10)
            - documentation_url: URL to agent documentation
            - extra_metadata: Additional metadata dictionary
            - deployment: Deployment configuration dict
            - storage: Storage backend configuration dict
            - scheduler: Task scheduler configuration dict
            - global_webhook_url: Default webhook URL for all tasks (optional)
            - global_webhook_token: Authentication token for global webhook (optional)
        handler: The handler function that processes messages and returns responses.
                Must have signature: (messages: list[dict[str, Any]]) -> Any.
                Each message is an A2A protocol message: {"role": "user" |
                "agent" | "system", "kind": "message", "parts": [...]} where
                parts are {"kind": "text", "text": ...}, {"kind": "file",
                "file": {"bytes", "mimeType", "name"}}, or {"kind": "data",
                "data": {...}}. Read text via the message's parts, and file
                bytes via part["file"]["bytes"] (base64).
        run_server: If True, starts the uvicorn server (blocking). If False, returns manifest
                   immediately for testing/programmatic usage (default: True)
        key_dir: Directory for storing DID keys. If None, attempts to detect from caller's
                directory (may fail in REPL/notebooks). Falls back to current working directory.
        launch: If True, creates a public tunnel via FRP to expose the server to the internet
               with an auto-generated subdomain (default: False)

    Returns:
        AgentManifest: The manifest for the bindufied agent

    Example:
        def my_handler(messages: list[dict[str, Any]]) -> str:
            # A2A contract: message text lives in parts.
            user_text = " ".join(
                p.get("text", "")
                for p in messages[-1].get("parts", [])
                if p.get("kind") == "text"
            )
            result = agent.run(input=user_text)
            return result.to_dict()["content"]

        config = {
            "author": "user@example.com",
            "name": "my-agent",
            "description": "A helpful assistant",
            "capabilities": {"streaming": True},
            "deployment": {"url": "http://localhost:3773", "protocol_version": "1.0.0"},
        }

        manifest = bindufy(config, my_handler)
    """
    if not callable(handler):
        raise TypeError(
            "HandlerError: 'handler' must be a callable function or coroutine function."
        )

    # Get caller information for file paths
    frame = inspect.currentframe()
    if not frame or not frame.f_back:
        raise RuntimeError("Unable to determine caller file path")

    caller_file = inspect.getframeinfo(frame.f_back).filename
    caller_dir = Path(os.path.abspath(caller_file)).parent

    # Capture sentinel: when set by ``bindu deploy``, dump the agent name and
    # source directory to JSON so the deploy CLI can package + ship the agent
    # without re-implementing config in flag-land. Returning here skips all
    # heavy runtime setup (DID, server, etc.) on the host. Inside the deployed
    # VM the env var is unset, so ``bindufy()`` runs normally.
    if capture_path := os.environ.get("BINDU_DEPLOY_CAPTURE"):
        import json

        agent_name = config.get("name") or config.get("id")
        if not agent_name:
            raise ValueError("config must include 'name' for runtime deployment")
        Path(capture_path).write_text(
            json.dumps({"agent_name": agent_name, "caller_dir": str(caller_dir)})
        )
        return None

    return _bindufy_core(
        config=config,
        handler_callable=handler,
        run_server=run_server,
        key_dir=key_dir,
        launch=launch,
        caller_dir=caller_dir,
    )
