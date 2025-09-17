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
Pebblify decorator for transforming regular agents into secure, networked Pebble agents.

This module provides the core decorator that handles:
1. Protocol-compliant function wrapping with AgentAdapter
2. Key generation and DID document creation
3. Certificate management via Sheldon
4. Secure server setup with MLTS
5. Agent registration with Hibiscus
6. Runner registration for execution
"""

import inspect
import os
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic.types import SecretStr
from urllib.parse import urlparse
import uvicorn

from pebbling.common.models import AgentManifest, DeploymentConfig, SchedulerConfig, StorageConfig
from pebbling.common.protocol.types import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    AgentTrust,
)
from pebbling.penguin.manifest import create_manifest, validate_agent_function
from pebbling.security.agent_identity import create_agent_identity
import pebbling.observability.openinference as OpenInferenceObservability

# Import server components for deployment
from pebbling.server import (
    InMemoryScheduler,
    InMemoryStorage,
    PebbleApplication,
    # PostgreSQLStorage,
    # QdrantStorage,
    # RedisScheduler,
)
from pebbling.server.utils.display import prepare_server_display
from pebbling.utils.constants import CERTIFICATE_DIR, PKI_DIR

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.penguin.pebblify")


def _create_storage_instance(storage_config: Optional[StorageConfig]) -> Any:
    """Factory function to create storage instance based on configuration."""
    if not storage_config:
        return InMemoryStorage()

    if storage_config.type == "postgres":
        return InMemoryStorage()
    elif storage_config.type == "qdrant":
        return InMemoryStorage()
    else:
        return InMemoryStorage()


def _create_scheduler_instance(scheduler_config: Optional[SchedulerConfig]) -> Any:
    """Factory function to create scheduler instance based on configuration."""
    return InMemoryScheduler()


def pebblify(
    author: Optional[str] = None,
    name: Optional[str] = None,
    id: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    recreate_keys: bool = True,
    skills: List[Optional[AgentSkill]] = None,
    capabilities: Optional[AgentCapabilities] = None,
    agent_trust: Optional[AgentTrust] = None,
    kind: Literal["agent", "team", "workflow"] = "agent",
    debug_mode: bool = False,
    debug_level: Literal[1, 2] = 1,
    monitoring: bool = False,
    telemetry: bool = True,
    num_history_sessions: int = 10,
    documentation_url: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = {},
    deployment_config: Optional[DeploymentConfig] = None,
    storage_config: Optional[StorageConfig] = None,
    scheduler_config: Optional[SchedulerConfig] = None,
) -> Callable:
    """Transform a protocol-compliant function into a Pebbling-compatible agent.

    Args:
        author: Agent author email (required for Hibiscus registration, or set PEBBLE_HIBISCUS_EMAIL env var)
        name: Human-readable agent name
        id: Unique agent identifier
        description: Agent description
        version: Agent version string
        recreate_keys: Force regeneration of existing keys
        skills: List of agent skills/capabilities
        capabilities: Technical capabilities (streaming, notifications, etc.)
        agent_trust: Trust and security configuration
        kind: Agent type ('agent', 'team', or 'workflow')
        debug_mode: Enable debug logging
        debug_level: Debug verbosity level
        monitoring: Enable monitoring/metrics
        telemetry: Enable telemetry collection
        num_history_sessions: Number of conversation histories to maintain
        documentation_url: URL to agent documentation
        extra_metadata: Additional metadata dictionary
        deployment_config: Server deployment configuration
        storage_config: Storage backend configuration
        scheduler_config: Task scheduler configuration
        register_with_hibiscus: Whether to register agent with Hibiscus registry
        hibiscus_url: Hibiscus registry URL (default: http://localhost:19191)
        hibiscus_pat_token: Hibiscus Personal Access Token (required for registration, or set PEBBLE_HIBISCUS_PAT_TOKEN env var)
        issue_certificate: Whether to issue a certificate during registration
        certificate_validity_days: Certificate validity period in days (default: 365)

    Environment Variables:
        PEBBLE_HIBISCUS_EMAIL: Agent author email for Hibiscus registration (alternative to 'author' parameter)
        PEBBLE_HIBISCUS_PAT_TOKEN: Hibiscus Personal Access Token (alternative to 'hibiscus_pat_token' parameter)

    Returns:
        Decorated function that returns an AgentManifest
    """

    def decorator(agent_function: Callable) -> AgentManifest:
        # Validate that this is a protocol-compliant function
        logger.info(f"🔍 Validating agent function: {agent_function.__name__}")
        validate_agent_function(agent_function)

        agent_id = id or uuid.uuid4().hex
        logger.info(f"🔍 Agent ID: {agent_id}")

        caller_file = inspect.getframeinfo(inspect.currentframe().f_back).filename
        if not caller_file:
            raise RuntimeError("Unable to determine caller file path")

        caller_dir = Path(os.path.abspath(caller_file)).parent

        agent_identity: AgentIdentity = create_agent_identity(
            id=agent_id,
            did_required=True,  # We encourage the use of DID for agent-to-agent communication
            recreate_keys=recreate_keys,
            create_csr=True,  # Generate CSR only if certificate will be issued
            pki_dir=Path(os.path.join(caller_dir, PKI_DIR)),
            cert_dir=Path(os.path.join(caller_dir, CERTIFICATE_DIR)),
        )

        logger.info(f"✅ Security setup complete - DID: {agent_identity['did'] if agent_identity else 'None'}")
        logger.info("📋 Creating agent manifest...")

        _manifest = create_manifest(
            agent_function=agent_function,
            id=agent_id,
            name=name,
            identity=agent_identity,
            description=description,
            skills=skills,
            capabilities=capabilities,
            agent_trust=agent_trust,
            version=version,
            url=deployment_config.url,
            protocol_version=deployment_config.protocol_version,
            kind=kind,
            debug_mode=debug_mode,
            debug_level=debug_level,
            monitoring=monitoring,
            telemetry=telemetry,
            num_history_sessions=num_history_sessions,
            documentation_url=documentation_url,
            extra_metadata=extra_metadata,
        )

        agent_did = _manifest.identity.get("did", "None") if _manifest.identity else "None"
        logger.info(f"🚀 Agent '{agent_did}' successfully pebblified!")
        logger.debug(
            f"📊 Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | {len(_manifest.skills) if _manifest.skills else 0} skills | {_manifest.url}"
        )

        logger.info(f"🚀 Starting deployment for agent: {agent_id}")

        # Create server components using factory functions
        storage_instance = _create_storage_instance(storage_config)
        scheduler_instance = _create_scheduler_instance(scheduler_config)

        # Create the manifest worker
        pebble_app = PebbleApplication(
            storage=storage_instance,
            scheduler=scheduler_instance,
            penguin_id=agent_id,
            manifest=_manifest,
            version=version,
        )

        if telemetry:
            try:
                OpenInferenceObservability.setup()
            except Exception as exc:
                logger.warn("OpenInference telemetry setup failed", error=str(exc))

        # Deploy the server
        parsed_url = urlparse(deployment_config.url)
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or 3773

        # Display beautiful server startup banner with all info
        print(prepare_server_display(host=host, port=port, agent_id=agent_id))
        uvicorn.run(pebble_app, host=host, port=port)

        return _manifest

    return decorator
