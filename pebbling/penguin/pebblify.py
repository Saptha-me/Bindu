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
from pebbling.security.setup_security import create_security_config
from pebbling.penguin.manifest import validate_agent_function, create_manifest
from pebbling.hibiscus.agent_registry import register_with_registry

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.penguin.pebblify")

def pebblify(
    author: Optional[str] = None,
    name: Optional[str] = None,
    id: Optional[str] = None,
    version: str = "1.0.0",
    skill: Optional[AgentSkill] = None,
    capabilities: Optional[AgentCapabilities] = None,
    security_config: SecurityConfig = None,  
    registration_config: Optional[AgentRegistrationConfig] = None,
    ca_config: Optional[CAConfig] = None,
    deployment_config: Optional[DeploymentConfig] = None,
    pat_token: Optional[str] = None,    
    
) -> Callable:
    """Transform a protocol-compliant function into a Pebbling-compatible agent.
    
    """
    def decorator(agent_function: Callable) -> AgentManifest:
        # Validate that this is a protocol-compliant function
        logger.info(f"🔍 Validating agent function: {agent_function.__name__}")
        validate_agent_function(agent_function)

        agent_id = id or uuid.uuid4().hex
        logger.info(f"🔍 Agent ID: {agent_id}")

        security_setup_result: SecuritySetupResult = create_security_config(
            id=agent_id,
            did_required=security_config.did_required,
            recreate_keys=security_config.recreate_keys,
            require_challenge_response=security_config.require_challenge_response,
            create_csr=security_config.create_csr,
            verify_requests=security_config.verify_requests,
            allow_anonymous=security_config.allow_anonymous
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

        if registration_config:
            logger.info("📋 Registering agent...")
            register_with_registry(
                author=author,
                agent_manifest=_manifest,
                agent_registry_pat_token=pat_token,
                agent_registry=registration_config.type,
                agent_registry_url=registration_config.url,
            )
            logger.info("✅ Agent registered successfully!")

        if ca_config:
            logger.info("📋 Setting up CA...")
            setup_ca(
                ca_config=ca_config,
                security=security,
                identity=identity
            )
            logger.info("✅ CA setup complete!")

        if deployment_config:
            logger.info("📋 Deploying agent...")
            deploy_agent(
                agent_id=agent_id,
                deployment_config=deployment_config,
                security=security,
                identity=identity
            )
            logger.info("✅ Agent deployed successfully!")
            
        return _manifest
    return decorator