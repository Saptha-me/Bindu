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
    Skill,
    AgentTrust,
)
from pebbling.penguin.manifest import create_manifest, validate_agent_function
from pebbling.extensions.did import DIDAgentExtension
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

    # Validate and process configuration
    from .config_validator import ConfigValidator
    validated_config = ConfigValidator.validate_and_process(config)
    
    # Generate agent_id if not provided
    agent_id = validated_config.get("id", uuid.uuid4().hex)
    
    # Create config objects if dictionaries provided
    deployment_config = DeploymentConfig(**validated_config["deployment"]) if validated_config.get("deployment") else None
    storage_config = StorageConfig(**validated_config["storage"]) if validated_config.get("storage") else None
    scheduler_config = SchedulerConfig(**validated_config["scheduler"]) if validated_config.get("scheduler") else None
    
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

    did_extension = DIDAgentExtension(
        recreate_keys=validated_config["recreate_keys"],
        key_dir=Path(os.path.join(caller_dir, PKI_DIR)),
        author=validated_config.get("author"),
        agent_name=validated_config.get("name"),
        key_password=validated_config.get("key_password")
    )
    did_extension.generate_and_save_key_pair()
    
    # Set agent metadata for DID document
    did_extension.set_agent_metadata(
        description=validated_config["description"],
        version=validated_config["version"],
        author=validated_config.get("author"),
        skills=[skill.dict() if hasattr(skill, 'dict') else skill for skill in (validated_config.get("skills") or [])],
        capabilities=validated_config.get("capabilities"),
        url=deployment_config.url if deployment_config else "http://localhost:3773",
        kind=validated_config["kind"],
        telemetry=validated_config["telemetry"],
        monitoring=validated_config["monitoring"],
        documentation_url=validated_config.get("documentation_url"),
    )

    logger.info(f"DID Extension setup complete", did=did_extension.did)
    logger.info("📋 Creating agent manifest...")

    # Update capabilities to include DID extension
    capabilities = validated_config["capabilities"]
    if capabilities and isinstance(capabilities, dict):
        if "extensions" in capabilities:
            capabilities["extensions"].append(did_extension.agent_extension)
        else:
            capabilities["extensions"] = [did_extension.agent_extension]
        capabilities = AgentCapabilities(**capabilities)
    elif capabilities:
        # capabilities is already an AgentCapabilities object
        if hasattr(capabilities, 'extensions') and capabilities.extensions:
            capabilities.extensions.append(did_extension.agent_extension)
        else:
            capabilities.extensions = [did_extension.agent_extension]
    else:
        capabilities = AgentCapabilities(extensions=[did_extension.agent_extension])

    _manifest = create_manifest(
        agent_function=handler,
        id=agent_id,
        name=validated_config["name"],
        description=validated_config["description"],
        skills=validated_config["skills"],
        capabilities=capabilities,
        did_extension=did_extension,
        agent_trust=validated_config["agent_trust"],
        version=validated_config["version"],
        url=deployment_config.url if deployment_config else "http://localhost:3773",
        protocol_version=deployment_config.protocol_version if deployment_config else "1.0.0",
        kind=validated_config["kind"],
        debug_mode=validated_config["debug_mode"],
        debug_level=validated_config["debug_level"],
        monitoring=validated_config["monitoring"],
        telemetry=validated_config["telemetry"],
        num_history_sessions=validated_config["num_history_sessions"],
        documentation_url=validated_config["documentation_url"],
        extra_metadata=validated_config["extra_metadata"],
    )

    agent_did = did_extension.did
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
        version=validated_config["version"],
    )

    if validated_config["telemetry"]:
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
