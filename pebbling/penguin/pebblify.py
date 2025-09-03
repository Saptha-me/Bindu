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
from typing import Callable, Optional
from pathlib import Path
import os
from functools import partial
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn

from pebbling.common.protocol.types import (
    AgentCapabilities, 
    AgentManifest, 
    AgentSkill, 
)
from pebbling.common.models.models import ( 
    DeploymentConfig,
    SecuritySetupResult
)
from pebbling.utils.constants import (
    PKI_DIR,
    CERTIFICATE_DIR
)
from pebbling.security.setup_security import create_security_config
from pebbling.penguin.manifest import validate_agent_function, create_manifest

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Import server components for deployment
from pebbling.server.scheduler import InMemoryScheduler, RedisScheduler
from pebbling.server.storage import InMemoryStorage, PostgreSQLStorage, QdrantStorage
from pebbling.server.workers import ManifestWorker
from pebbling.server.applications import PebbleApplication
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

# Configure logging for the module
logger = get_logger("pebbling.penguin.pebblify")

@asynccontextmanager
async def worker_lifespan(
    app: PebbleApplication,
    manifest_worker: ManifestWorker
) -> AsyncIterator[None]:
    """Manages the ManifestWorker lifecycle during FastAPI startup/shutdown.

    Key Components:
    - manifest_worker: Manages agent execution, handling message processing through broker and storage
    - Startup: Initializes worker, sets up connections to broker and storage
    - Runtime: Worker processes incoming requests through Pebbling protocol
    - Shutdown: Cleanly closes worker, ensuring proper resource cleanup
    
    This prevents resource leaks and ensures your agent is ready to process requests
    as soon as the server starts, running as a persistent service within FastAPI.
    """
    # Startup: Initialize the worker and start processing
    await manifest_worker.start()
    try:
        # Worker is now ready to process incoming requests
        yield
    finally:
        # Shutdown: Clean up worker resources
        await manifest_worker.stop()

def pebblify(
    author: Optional[str] = None,
    name: Optional[str] = None,
    id: Optional[str] = None,
    version: str = "1.0.0",
    skill: Optional[AgentSkill] = None,
    capabilities: Optional[AgentCapabilities] = None, 
    storage: Optional[InMemoryStorage | PostgreSQLStorage | QdrantStorage] = None,
    scheduler: Optional[InMemoryScheduler | RedisScheduler] = None,
    deployment_config: Optional[DeploymentConfig] = None,
    
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

        security_setup_result: SecuritySetupResult = create_security_config(
            id=agent_id,
            did_required=security_config.did_required,
            recreate_keys=security_config.recreate_keys,
            require_challenge_response=security_config.require_challenge_response,
            create_csr=security_config.create_csr,
            verify_requests=security_config.verify_requests,
            allow_anonymous=security_config.allow_anonymous,
            pki_dir=Path(os.path.join(caller_dir, PKI_DIR)),
            cert_dir=Path(os.path.join(caller_dir, CERTIFICATE_DIR)),
        )
       
        # Extract security and identity from setup result
        identity = security_setup_result.identity

        logger.info(f"✅ Security setup complete - DID: {identity.did if identity else 'None'}")
        logger.info("📋 Creating agent manifest...")

        _manifest = create_manifest(
            agent_function=agent_function,
            name=name,
            id=agent_id,
            description=None,
            skills=[skill] if skill else None,
            capabilities=capabilities,
            version=version,
            extra_metadata=None,
            identity=identity
        )

        logger.info(f"🚀 Agent '{_manifest.name}' successfully pebblified!")
        logger.debug(f"📊 Manifest details: {_manifest}")
        logger.info(f"🚀 Starting deployment for agent: {agent_id}")

        # Create server components
        storage_instance = storage or InMemoryStorage()
        scheduler_instance = scheduler or InMemoryScheduler()
        manifest_worker = ManifestWorker(manifest=_manifest, scheduler=scheduler_instance, storage=storage_instance)

        lifespan = partial(worker_lifespan, manifest_worker=manifest_worker, manifest=_manifest)

        pebble_app = PebbleApplication(
            storage=storage_instance,
            scheduler=scheduler_instance,
            penguin_id=agent_id,
            agents=[_manifest],
            skills=[skill] if skill else None,
            version=version,
            description=description,
            debug=debug,
            lifespan=lifespan
        )    

        # Deploy the server
        uvicorn.run(pebble_app, host=deployment_config.host, port=deployment_config.port)
            
        return _manifest
    return decorator