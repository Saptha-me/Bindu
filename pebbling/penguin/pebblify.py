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
    agent: Any,
    config: Dict[str, Any],
    handler: Callable[[str], str]
) -> AgentManifest:
    """Transform an agent instance and handler into a Pebbling-compatible agent.

    Args:
        agent: The agent instance (e.g., from agno.agent.Agent)
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
        handler: The handler function that processes messages and returns responses.
                Must have signature: (messages: str) -> str

    Returns:
        AgentManifest: The manifest for the pebblified agent
    
    Example:
        agent = Agent(
            instructions="You are a helpful assistant",
            model=OpenAIChat(id="gpt-4")
        )
        
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
        
        manifest = pebblify(agent, config, my_handler)
    """

    # Extract configuration with defaults
    author = config.get("author")
    name = config.get("name", "pebble-agent")
    agent_id = config.get("id", uuid.uuid4().hex)
    description = config.get("description", "A Pebble agent")
    version = config.get("version", "1.0.0")
    recreate_keys = config.get("recreate_keys", True)
    skills = config.get("skills", [])
    capabilities = config.get("capabilities")
    agent_trust = config.get("agent_trust")
    kind = config.get("kind", "agent")
    debug_mode = config.get("debug_mode", False)
    debug_level = config.get("debug_level", 1)
    monitoring = config.get("monitoring", False)
    telemetry = config.get("telemetry", True)
    num_history_sessions = config.get("num_history_sessions", 10)
    documentation_url = config.get("documentation_url")
    extra_metadata = config.get("extra_metadata", {})
    
    # Extract nested configs
    deployment_config_dict = config.get("deployment", {})
    storage_config_dict = config.get("storage", {})
    scheduler_config_dict = config.get("scheduler", {})
    
    # Create config objects if dictionaries provided
    deployment_config = DeploymentConfig(**deployment_config_dict) if deployment_config_dict else None
    storage_config = StorageConfig(**storage_config_dict) if storage_config_dict else None
    scheduler_config = SchedulerConfig(**scheduler_config_dict) if scheduler_config_dict else None
    
    # Store the agent reference in the handler's closure (for potential future use)
    handler._pebble_agent = agent
    # Validate that this is a protocol-compliant function
    logger.info(f"🔍 Validating handler function: {handler.__name__}")
    validate_agent_function(handler)

    logger.info(f"🔍 Agent ID: {agent_id}")

    # Get caller information for file paths
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller_file = inspect.getframeinfo(frame.f_back).filename
    else:
        caller_file = None
    
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
        agent_function=handler,
        id=agent_id,
        name=name,
        identity=agent_identity,
        description=description,
        skills=skills,
        capabilities=capabilities,
        agent_trust=agent_trust,
        version=version,
        url=deployment_config.url if deployment_config else "http://localhost:3773",
        protocol_version=deployment_config.protocol_version if deployment_config else "1.0.0",
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
    if deployment_config:
        parsed_url = urlparse(deployment_config.url)
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or 3773
    else:
        host = "localhost"
        port = 3773

    # Display beautiful server startup banner with all info
    print(prepare_server_display(host=host, port=port, agent_id=agent_id))
    uvicorn.run(pebble_app, host=host, port=port)

    return _manifest
