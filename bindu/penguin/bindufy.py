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
from uuid import uuid4

import uvicorn

from bindu.common.models import (
    AgentManifest,
    DeploymentConfig,
    SchedulerConfig,
    SentryConfig,
    StorageConfig,
    TelemetryConfig,
)
from bindu.extensions.did import DIDAgentExtension
from bindu.extensions.x402 import X402AgentExtension
from bindu.penguin.manifest import create_manifest, validate_agent_function
from bindu.settings import app_settings
from bindu.utils import add_extension_to_capabilities
from bindu.utils.display import prepare_server_display
from bindu.utils.logging import get_logger
from bindu.utils.skill_loader import load_skills

# Configure logging for the module
logger = get_logger("bindu.penguin.bindufy")


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

    if "url" not in deploy_dict or "expose" not in deploy_dict:
        logger.warning(
            "Deployment config missing required fields (url, expose), using defaults"
        )
        return None

    return DeploymentConfig(
        url=deploy_dict["url"],
        expose=deploy_dict["expose"],
        protocol_version=deploy_dict.get("protocol_version", "1.0.0"),
        proxy_urls=deploy_dict.get("proxy_urls"),
        cors_origins=deploy_dict.get("cors_origins"),
        openapi_schema=deploy_dict.get("openapi_schema"),
    )


def _create_storage_config(validated_config: Dict[str, Any]) -> StorageConfig | None:
    """Create storage config from validated config dict.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        StorageConfig instance or None if invalid/missing
    """
    storage_dict = validated_config.get("storage")
    if not storage_dict:
        return None

    if "type" not in storage_dict:
        logger.warning("Storage config missing required field 'type', using defaults")
        return None

    return StorageConfig(
        type=storage_dict["type"],
        database_url=storage_dict.get("database_url"),
    )


def _create_scheduler_config(
    validated_config: Dict[str, Any],
) -> SchedulerConfig | None:
    """Create scheduler config from validated config dict.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        SchedulerConfig instance or None if invalid/missing
    """
    scheduler_dict = validated_config.get("scheduler")
    if not scheduler_dict:
        return None

    if "type" not in scheduler_dict:
        logger.warning("Scheduler config missing required field 'type', using defaults")
        return None

    return SchedulerConfig(type=scheduler_dict["type"])


def _create_sentry_config(validated_config: Dict[str, Any]) -> SentryConfig | None:
    """Create SentryConfig from validated configuration.

    Args:
        validated_config: Validated configuration dictionary

    Returns:
        SentryConfig object or None if not configured
    """
    sentry_dict = validated_config.get("sentry")
    if not sentry_dict:
        return None

    return SentryConfig(
        enabled=sentry_dict.get("enabled", False),
        dsn=sentry_dict.get("dsn"),
        environment=sentry_dict.get("environment", "development"),
        release=sentry_dict.get("release"),
        traces_sample_rate=sentry_dict.get("traces_sample_rate", 1.0),
        profiles_sample_rate=sentry_dict.get("profiles_sample_rate", 0.1),
        enable_tracing=sentry_dict.get("enable_tracing", True),
        send_default_pii=sentry_dict.get("send_default_pii", False),
        debug=sentry_dict.get("debug", False),
    )


def bindufy(
    config: Dict[str, Any], handler: Callable[[list[dict[str, str]]], Any]
) -> AgentManifest:
    """Transform an agent instance and handler into a bindu-compatible agent.

    Args:
        config: Configuration dictionary containing:
            - author: Agent author email (required for Hibiscus registration)
            - name: Human-readable agent name
            - id: Unique agent identifier (optional, auto-generated if not provided)
            - description: Agent description
            - version: Agent version string (default: "1.0.0")
            - recreate_keys: Force regeneration of existing keys (default: True)
            - skills: List of agent skills/capabilities
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
                Must have signature: (messages: str) -> str

    Returns:
        AgentManifest: The manifest for the bindufied agent

    Example:
        def my_handler(messages: str) -> str:
            result = agent.run(input=messages)
            return result.to_dict()["content"]

        config = {
            "author": "user@example.com",
            "name": "my-agent",
            "description": "A helpful assistant",
            "capabilities": {"streaming": True},
            "deployment": {"url": "http://localhost:3773", "protocol_version": "1.0.0"},
            "storage": {"type": "memory"},
            "scheduler": {"type": "memory"}
        }

        manifest = bindufy(agent, config, my_handler)
    """
    # Validate and process configuration
    from .config_validator import ConfigValidator

    validated_config = ConfigValidator.validate_and_process(config)

    # Update app_settings.auth based on config
    auth_config = validated_config.get("auth")
    if auth_config and auth_config.get("enabled"):
        # Auth is enabled - configure all settings
        app_settings.auth.enabled = True
        app_settings.auth.domain = auth_config.get("domain", "")
        app_settings.auth.audience = auth_config.get("audience", "")
        app_settings.auth.algorithms = auth_config.get("algorithms", ["RS256"])
        app_settings.auth.issuer = auth_config.get("issuer", "")
        app_settings.auth.jwks_uri = auth_config.get("jwks_uri", "")
        app_settings.auth.public_endpoints = auth_config.get(
            "public_endpoints", app_settings.auth.public_endpoints
        )
        app_settings.auth.require_permissions = auth_config.get(
            "require_permissions", False
        )
        app_settings.auth.permissions = auth_config.get(
            "permissions", app_settings.auth.permissions
        )

        logger.info(
            f"Auth0 configuration loaded: domain={auth_config.get('domain')}, audience={auth_config.get('audience')}"
        )
    else:
        # Auth is not provided or disabled - ensure it's disabled
        app_settings.auth.enabled = False
        logger.info("Authentication disabled")

    # Generate agent_id if not provided
    agent_id = validated_config.get("id", uuid4().hex)

    # Create config objects from validated config
    deployment_config = _create_deployment_config(validated_config)
    storage_config = _create_storage_config(validated_config)
    scheduler_config = _create_scheduler_config(validated_config)
    sentry_config = _create_sentry_config(validated_config)

    # Validate that this is a protocol-compliant function
    handler_name = getattr(handler, "__name__", "<unknown>")
    logger.info(f"Validating handler function: {handler_name}")
    validate_agent_function(handler)
    logger.info(f"Agent ID: {agent_id}")

    # Get caller information for file paths
    frame = inspect.currentframe()
    if not frame or not frame.f_back:
        raise RuntimeError("Unable to determine caller file path")

    caller_file = inspect.getframeinfo(frame.f_back).filename
    caller_dir = Path(os.path.abspath(caller_file)).parent

    # Initialize DID extension with key management
    try:
        did_extension = DIDAgentExtension(
            recreate_keys=validated_config["recreate_keys"],
            key_dir=caller_dir / app_settings.did.pki_dir,
            author=validated_config.get("author"),
            agent_name=validated_config.get("name"),
            agent_id=str(agent_id),
            key_password=validated_config.get("key_password"),
        )
        did_extension.generate_and_save_key_pair()
    except Exception as exc:
        logger.error(f"Failed to initialize DID extension: {exc}")
        raise

    logger.info(f"DID extension initialized: {did_extension.did}")

    # Load skills from configuration (supports both file-based and inline)
    logger.info("Loading agent skills...")
    skills_list = load_skills(validated_config.get("skills") or [], caller_dir)

    # Set agent metadata for DID document
    agent_url = (
        deployment_config.url if deployment_config else app_settings.network.default_url
    )

    logger.info("DID Extension setup complete", did=did_extension.did)
    logger.info("Creating agent manifest...")

    # Update capabilities to include DID extension
    capabilities = add_extension_to_capabilities(
        validated_config.get("capabilities", {}), did_extension
    )

    # Only add x402 extension if execution_cost is configured
    execution_cost = validated_config.get("execution_cost")
    x402_extension = None

    if execution_cost:
        # Create X402 extension with payment configuration
        amount = execution_cost.get("amount")
        token = execution_cost.get("token", "USDC")
        network = execution_cost.get("network", "base-sepolia")
        pay_to_address = execution_cost.get("pay_to_address")

        if not amount:
            raise ValueError(
                "execution_cost.amount is required when execution_cost is configured"
            )

        logger.info(f"Execution cost configured: {amount} {token} on {network}")

        x402_extension = X402AgentExtension(
            amount=amount,
            token=token,
            network=network,
            required=True,  # Payment is required for paid agents
            pay_to_address=pay_to_address,
        )

        logger.info(f"X402 extension created: {x402_extension}")

        # Add x402 extension to capabilities
        capabilities = add_extension_to_capabilities(capabilities, x402_extension)

    # Create agent manifest with loaded skills
    _manifest = create_manifest(
        agent_function=handler,
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
        else "1.0.0",
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
    )

    # Log manifest creation
    skill_count = len(_manifest.skills) if _manifest.skills else 0
    logger.info(f"Agent '{did_extension.did}' successfully bindufied!")
    logger.debug(
        f"Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | {skill_count} skills | {_manifest.url}"
    )

    logger.info(f"Starting deployment for agent: {agent_id}")

    # Import server components (deferred to avoid circular import)
    from bindu.server import BinduApplication

    # Storage and scheduler will be initialized in BinduApplication's lifespan
    # No need to create instances here - just pass the config

    # Create telemetry configuration
    telemetry_config = TelemetryConfig(
        enabled=validated_config["telemetry"],
        endpoint=validated_config.get("oltp_endpoint"),
        service_name=validated_config.get("oltp_service_name"),
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

    # Create Bindu application with configs
    # Storage and scheduler will be initialized in the application lifespan context
    bindu_app = BinduApplication(
        storage_config=storage_config,
        scheduler_config=scheduler_config,
        penguin_id=agent_id,
        manifest=_manifest,
        version=validated_config["version"],
        auth_enabled=app_settings.auth.enabled,
        telemetry_config=telemetry_config,
        sentry_config=sentry_config,
    )

    # Parse deployment URL
    host, port = _parse_deployment_url(deployment_config)

    # Display server startup banner
    prepare_server_display(
        host=host, port=port, agent_id=agent_id, agent_did=did_extension.did
    )
    uvicorn.run(bindu_app, host=host, port=port)
    return _manifest
