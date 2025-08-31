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

import functools
import inspect
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path
import os

from pebbling.protocol.types import (
    AgentCapabilities, 
    AgentManifest, 
    AgentSkill, 
)
from pebbling.common.models.models import ( 
    SecurityConfig, 
    AgentRegistrationConfig, 
    CAConfig, 
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
from pebbling.server.task_manager import TaskManager
from pebbling.server.workers.base import Worker
from pebbling.server.scheduler import InMemoryScheduler
from pebbling.server.storage import InMemoryStorage
from pebbling.server.schema import TaskSendParams, TaskIdParams, Message, Artifact
from pebbling.protocol.types import AgentSecurity, AgentIdentity
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

# Configure logging for the module
logger = get_logger("pebbling.penguin.pebblify")


class ManifestWorkerAdapter(Worker):
    """Adapts AgentManifest to Worker interface for A2A protocol compatibility."""
    
    def __init__(self, manifest: AgentManifest, scheduler, storage):
        self.manifest = manifest
        super().__init__(broker=broker, storage=storage)
    
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute task using the manifest's run method."""
        task = await self.storage.load_task(params['id'])
        if task is None:
            raise ValueError(f'Task {params["id"]} not found')
        
        if task['status']['state'] != 'submitted':
            raise ValueError(f'Task {params["id"]} has already been processed')
        
        await self.storage.update_task(task['id'], state='working')
        
        try:
            # Extract message from task
            message_text = task.get('message', {}).get('parts', [{}])[0].get('text', '')
            
            # Load context from storage
            context = await self.storage.load_context(task['context_id']) or {}
            
            # Execute manifest's run method
            if inspect.iscoroutinefunction(self.manifest.run) or inspect.isasyncgenfunction(self.manifest.run):
                if inspect.isasyncgenfunction(self.manifest.run):
                    # Handle async generator (streaming)
                    results = []
                    async for result in self.manifest.run(message_text, context):
                        results.append(str(result))
                    final_result = '\n'.join(results)
                else:
                    # Handle async function
                    final_result = await self.manifest.run(message_text, context)
            else:
                # Handle sync function/generator
                if inspect.isgeneratorfunction(self.manifest.run):
                    results = list(self.manifest.run(message_text, context))
                    final_result = '\n'.join(str(r) for r in results)
                else:
                    final_result = self.manifest.run(message_text, context)
            
            # Build artifacts and messages
            artifacts = self.build_artifacts(final_result)
            messages = [Message(
                role='agent',
                parts=[{'kind': 'text', 'text': str(final_result)}],
                kind='message',
                message_id=str(uuid.uuid4())
            )]
            
            await self.storage.update_task(
                task['id'], 
                state='completed', 
                new_artifacts=artifacts, 
                new_messages=messages
            )
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self.storage.update_task(task['id'], state='failed')
            raise
    
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a task."""
        await self.storage.update_task(params['id'], state='cancelled')
    
    def build_message_history(self, history: List[Message]) -> List[Any]:
        """Convert A2A messages to context format."""
        return [msg.get('parts', [{}])[0].get('text', '') for msg in history]
    
    def build_artifacts(self, result: Any) -> List[Artifact]:
        """Build artifacts from agent result."""
        artifact_id = str(uuid.uuid4())
        return [Artifact(
            artifact_id=artifact_id,
            name='result',
            parts=[{'kind': 'text', 'text': str(result)}]
        )]


def deploy_agent(
    agent_id: str,
    deployment_config: DeploymentConfig,
    security: Optional[AgentSecurity] = None,
    identity: Optional[AgentIdentity] = None,
    manifest: Optional[AgentManifest] = None
) -> "FastAPI":
    """Deploy an agent as a server with A2A protocol support.
    
    Args:
        agent_id: Unique identifier for the agent
        deployment_config: Deployment configuration
        security: Optional security configuration
        identity: Optional agent identity
        manifest: The agent manifest to deploy
        
    Returns:
        FastAPI application instance
    """
    from pebbling.server.app import create_app
    from contextlib import asynccontextmanager
    
    logger.info(f"🚀 Starting deployment for agent: {agent_id}")
    
    
    
    # Create worker adapter if manifest is provided
    worker = None
    if manifest:
        worker = ManifestWorkerAdapter(manifest, broker, storage)
        logger.info(f"✅ Created worker adapter for manifest: {manifest.name}")
    
    # Create task manager
    task_manager = TaskManager(broker=broker, storage=storage)
    
    # Create lifespan manager that starts the worker
    @asynccontextmanager
    async def agent_lifespan(app):
        """Lifespan manager that starts worker during app startup."""
        if worker:
            async with worker.run():
                logger.info("✅ Worker started successfully")
                yield
        else:
            yield
    
    # Create FastAPI app using the centralized create_app function
    agents = [manifest] if manifest else []
    app = create_app(
        *agents,
        lifespan=agent_lifespan,
        task_manager=task_manager,
        storage=storage,
        broker=broker
    )
    
    # Update app title for specific agent
    app.title = f"Pebble Agent: {agent_id}"
    app.description = f"A2A-compatible agent server for {agent_id}"
    
    logger.info(f"✅ Agent {agent_id} deployed successfully")
    logger.info(f"📡 Server endpoints: /message/send, /task/{{task_id}}, /agents, /health")
    
    return app


def pebblify(
    author: Optional[str] = None,
    name: Optional[str] = None,
    id: Optional[str] = None,
    version: str = "1.0.0",
    skill: Optional[AgentSkill] = None,
    capabilities: Optional[AgentCapabilities] = None,
    security_config: SecurityConfig = None,  
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
        security = security_setup_result.security_config
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
            security=security,
            identity=identity
        )

        logger.info(f"🚀 Agent '{_manifest.name}' successfully pebblified!")
        logger.debug(f"📊 Manifest details: {_manifest}")
        logger.info(f"🚀 Starting deployment for agent: {agent_id}")

        # Create server components
        storage = InMemoryStorage()
        broker = InMemoryBroker()

        
        
        if deployment_config:
            logger.info("📋 Deploying agent...")
            app = deploy_agent(
                agent_id=agent_id,
                deployment_config=deployment_config,
                security=security,
                identity=identity,
                manifest=_manifest
            )
            logger.info("✅ Agent deployed successfully!")
            
            # Store the FastAPI app in the manifest for later access
            _manifest._deployment_app = app
        else:
            logger.info("📋 Deployment configuration not provided. Agent will not be deployed.")
            
        return _manifest
    return decorator