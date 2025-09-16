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
import uuid
from typing import Optional, Callable, List, Dict, Any, Literal
from pathlib import Path
import os
from functools import partial
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn

from pebbling.common.protocol.types import (
    AgentCapabilities, 
    AgentSkill,
    AgentIdentity,
    AgentTrust,
)
from pebbling.common.models import (
    DeploymentConfig,
    StorageConfig,
    SchedulerConfig
)
from pebbling.utils.constants import (
    PKI_DIR,
    CERTIFICATE_DIR
)
from pebbling.security.agent_identity import create_agent_identity
from pebbling.penguin.manifest import validate_agent_function, create_manifest
from pebbling.common.models import AgentManifest

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Import server components for deployment
from pebbling.server import (
    InMemoryScheduler, 
    RedisScheduler,
    InMemoryStorage, 
    QdrantStorage,
    PostgreSQLStorage,
    ManifestWorker,
    PebbleApplication
)

# Configure logging for the module
logger = get_logger("pebbling.penguin.pebblify")


def _create_storage_instance(storage_config: Optional[StorageConfig]) -> Any:
    """Factory function to create storage instance based on configuration."""
    if not storage_config:
        return InMemoryStorage()
    
    if storage_config.type == "postgres":
        storage = PostgreSQLStorage(connection_string=storage_config.connection_string)
        storage.initialize()
        return storage
    elif storage_config.type == "qdrant":
        storage = QdrantStorage(connection_string=storage_config.connection_string)
        storage.initialize()
        return storage
    else:
        return InMemoryStorage()


def _create_scheduler_instance(scheduler_config: Optional[SchedulerConfig]) -> Any:
    """Factory function to create scheduler instance based on configuration."""
    if not scheduler_config:
        return InMemoryScheduler()
    
    scheduler_factories = {
        "redis": lambda: RedisScheduler(),
        "memory": lambda: InMemoryScheduler()
    }
    
    factory = scheduler_factories.get(scheduler_config.type, scheduler_factories["memory"])
    return factory()


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
    kind: Literal['agent', 'team', 'workflow'] = 'agent',
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
            create_csr=True,
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

        logger.info(f"🚀 Agent '{_manifest.identity['did']}' successfully pebblified!")
        logger.debug(f"📊 Manifest: {_manifest.name} v{_manifest.version} | {_manifest.kind} | {len(_manifest.skills) if _manifest.skills else 0} skills | {_manifest.url}")

        async def run_agent():
            """Async function to initialize storage and run the agent."""
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
                version=version
            )    

            # Deploy the server
            from urllib.parse import urlparse
            parsed_url = urlparse(deployment_config.url)
            uvicorn.run(pebble_app, host=parsed_url.hostname or "localhost", port=parsed_url.port or 3773)

        # Attach the run function to the manifest for later execution
        _manifest.run_agent = run_agent
            
        return _manifest
    return decorator