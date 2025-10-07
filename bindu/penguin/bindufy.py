#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
bindufy decorator for transforming regular agents into secure, networked agents.
"""

import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import urlparse
from uuid import uuid4

import uvicorn

import bindu.observability.openinference as OpenInferenceObservability
from bindu.common.models import AgentManifest, DeploymentConfig, SchedulerConfig, StorageConfig
from bindu.common.protocol.types import AgentCapabilities
from bindu.extensions.did import DIDAgentExtension
from bindu.penguin.manifest import create_manifest, validate_agent_function
from bindu.server import BinduApplication, InMemoryScheduler, InMemoryStorage
from bindu.server.utils.display import prepare_server_display
from bindu.utils.constants import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_URL, PKI_DIR
from bindu.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("bindu.penguin.bindufy")


def _update_capabilities_with_did(
    capabilities: AgentCapabilities | Dict[str, Any] | None,
    did_extension_obj: Any
) -> AgentCapabilities:
    """Update capabilities to include DID extension.
    
    Args:
        capabilities: Existing capabilities (dict or AgentCapabilities object)
        did_extension_obj: DID extension object to add
        
    Returns:
        AgentCapabilities object with DID extension included
    """
    if capabilities and isinstance(capabilities, dict):
        if "extensions" in capabilities:
            capabilities["extensions"].append(did_extension_obj)
        else:
            capabilities["extensions"] = [did_extension_obj]
        return AgentCapabilities(**capabilities)
    elif capabilities:
        # capabilities is already an AgentCapabilities object
        if hasattr(capabilities, 'extensions') and capabilities.extensions:
            capabilities.extensions.append(did_extension_obj)
        else:
            capabilities.extensions = [did_extension_obj]
        return capabilities
    else:
        return AgentCapabilities(extensions=[did_extension_obj])


def _parse_deployment_url(deployment_config: DeploymentConfig | None) -> tuple[str, int]:
    """Parse deployment URL to extract host and port.
    
    Args:
        deployment_config: Deployment configuration object
        
    Returns:
        Tuple of (host, port)
    """
    if not deployment_config:
        return DEFAULT_HOST, DEFAULT_PORT
    
    parsed_url = urlparse(deployment_config.url)
    host = parsed_url.hostname or DEFAULT_HOST
    port = parsed_url.port or DEFAULT_PORT
    
    return host, port


def _create_storage_instance(storage_config: StorageConfig | None) -> InMemoryStorage:
    """Factory function to create storage instance based on configuration.
    
    Note: Currently only InMemoryStorage is supported.
    Future implementations will support PostgreSQL and other backends.
    """
    # TODO: Implement PostgreSQL and other storage backends
    return InMemoryStorage()


def _create_scheduler_instance(scheduler_config: SchedulerConfig | None) -> InMemoryScheduler:
    """Factory function to create scheduler instance based on configuration.
    
    Note: Currently only InMemoryScheduler is supported.
    Future implementations will support Redis and other backends.
    """
    # TODO: Implement Redis and other scheduler backends
    return InMemoryScheduler()


def bindufy(
    agent: Any,
    config: Dict[str, Any],
    handler: Callable[[str], str]
) -> AgentManifest:
    """Transform an agent instance and handler into a bindu-compatible agent.

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
        
        manifest = bindufy(agent, config, my_handler)
    """

    # Validate and process configuration
    from .config_validator import ConfigValidator
    
    validated_config = ConfigValidator.validate_and_process(config)
    
    # Generate agent_id if not provided
    agent_id = validated_config.get("id", uuid4().hex)
    
    # Create config objects if dictionaries provided
    deployment_config = (
        DeploymentConfig(**validated_config["deployment"]) 
        if validated_config.get("deployment") else None
    )
    storage_config = (
        StorageConfig(**validated_config["storage"]) 
        if validated_config.get("storage") else None
    )
    scheduler_config = (
        SchedulerConfig(**validated_config["scheduler"]) 
        if validated_config.get("scheduler") else None
    )
    
    # Store the agent reference in the handler's closure (for potential future use)
    handler._pebble_agent = agent
    
    # Validate that this is a protocol-compliant function
    logger.info(f"🔍 Validating handler function: {handler.__name__}")
    validate_agent_function(handler)
    logger.info(f"🔍 Agent ID: {agent_id}")

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
            key_dir=caller_dir / PKI_DIR,
            author=validated_config.get("author"),
            agent_name=validated_config.get("name"),
            key_password=validated_config.get("key_password")
        )
        did_extension.generate_and_save_key_pair()
    except Exception as exc:
        logger.error(f"Failed to initialize DID extension: {exc}")
        raise
    
    # Set agent metadata for DID document
    agent_url = deployment_config.url if deployment_config else DEFAULT_URL
    skills_data = [
        skill.dict() if hasattr(skill, 'dict') else skill 
        for skill in (validated_config.get("skills") or [])
    ]
    
    did_extension.set_agent_metadata(
        description=validated_config["description"],
        version=validated_config["version"],
        author=validated_config.get("author"),
        skills=skills_data,
        capabilities=validated_config.get("capabilities"),
        url=agent_url,
        kind=validated_config["kind"],
        telemetry=validated_config["telemetry"],
        monitoring=validated_config["monitoring"],
        documentation_url=validated_config.get("documentation_url"),
    )

    logger.info("DID Extension setup complete", did=did_extension.did)
    logger.info("📋 Creating agent manifest...")

    # Update capabilities to include DID extension
    capabilities = _update_capabilities_with_did(
        validated_config["capabilities"], 
        did_extension.agent_extension
    )

    # Create agent manifest
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
        url=agent_url,
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

    # Log manifest creation
    skill_count = len(_manifest.skills) if _manifest.skills else 0
    logger.info(f"🚀 Agent '{did_extension.did}' successfully pebblified!")
    logger.debug(
        f"📊 Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | "
        f"{skill_count} skills | {_manifest.url}"
    )

    logger.info(f"🚀 Starting deployment for agent: {agent_id}")

    # Create server components
    storage_instance = _create_storage_instance(storage_config)
    scheduler_instance = _create_scheduler_instance(scheduler_config)

    # Create the Pebble application
    pebble_app = BinduApplication(
        storage=storage_instance,
        scheduler=scheduler_instance,
        penguin_id=agent_id,
        manifest=_manifest,
        version=validated_config["version"],
    )

    # Setup telemetry if enabled
    if validated_config["telemetry"]:
        try:
            OpenInferenceObservability.setup()
        except Exception as exc:
            logger.warning("OpenInference telemetry setup failed", error=str(exc))

    # Parse deployment URL
    host, port = _parse_deployment_url(deployment_config)

    # Display server startup banner and run
    logger.info(prepare_server_display(host=host, port=port, agent_id=agent_id))
    uvicorn.run(pebble_app, host=host, port=port)

    return _manifest
