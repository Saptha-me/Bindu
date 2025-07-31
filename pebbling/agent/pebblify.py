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
from typing import Any, Callable, Dict, List, Optional, Union

from pebbling.protocol.types import AgentCapabilities, AgentManifest, AgentSkill
from pebbling.common.models.models import SecurityCredentials

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.agent.pebblify")

def pebblify(
    name: Optional[str] = None,
    description: Optional[str] = None,
    skills: Optional[AgentSkill] = None,
    capabilities: Optional[AgentCapabilities] = None,
    version: str = "1.0.0",
    
    # Configuration objects (preferred approach)
    credentials: SecurityCredentials = None,  
) -> Callable:
    """Transform a protocol-compliant function into a Pebbling-compatible agent.
    
    """
    def decorator(agent_function: Callable) -> AgentManifest:
        # Validate that this is a protocol-compliant function
        _validate_agent_function(agent_function)
        
        @functools.wraps(agent_function)
        def wrapper(*args, **kwargs) -> AgentManifest:
            logger.debug("Creating agent with pebblify decorator")
            
            # skills: AgentSkill = 
            # # Create agent manifest from function metadata
            # agent_manifest = _create_agent_manifest(
            #     agent_function=agent_function,
            #     name=name,
            #     description=description,
            #     skills=skills,
            #     capabilities=capabilities,
            #     version=version,
            #     user_id=user_id,
            #     extra_metadata=extra_metadata
            # )
            
            # # Setup basic agent metadata
            # setup_agent_metadata(agent_manifest, name)
            
            # # Merge config objects with legacy parameters
            # security_config = security or SecurityConfig(
            #     did_required=True,
            #     keys_required=True,
            #     pki_dir=None,
            #     recreate_keys=False,
            #     issue_certificate=True,
            #     cert_authority="sheldon",
            #     verify_requests=True
            # )
            
            # registry_config = registry or RegistryConfig(
            #     store_in_hibiscus=True,
            #     registry_url="http://localhost:19191",
            #     pat_token=None,
            #     registry_type="hibiscus"
            # )
            
            # deployment_config = deployment or DeploymentConfig(
            #     expose=False,
            #     port=3773,
            #     endpoint_type="json-rpc",
            #     proxy_urls=None,
            #     cors_origins=None,
            #     openapi_schema=None
            # )
            
            # # Setup security if requested
            # if security_config.did_required or security_config.keys_required:
            #     logger.info(
            #         f"Setting up security for agent '{agent_manifest.name}' "
            #         f"(did_required={security_config.did_required}, keys_required={security_config.keys_required})"
            #     )
            #     agent_manifest = setup_security(
            #         agent_manifest=agent_manifest,
            #         name=agent_manifest.name,
            #         keys_required=security_config.keys_required,
            #         pki_dir=security_config.pki_dir,
            #         did_required=security_config.did_required,
            #         recreate_keys=security_config.recreate_keys
            #     )
            # else:
            #     logger.info(f"Skipping security setup for agent '{agent_manifest.name}'")
            
            # # Create agent adapter
            # adapter = create_agent_adapter(agent_function, agent_manifest)
            
            # # Register adapter with runner if agent has DID
            # if hasattr(agent_manifest, 'did') and agent_manifest.did:
            #     register_agent_adapter(agent_manifest.did, adapter)
            #     logger.debug(f"Registered agent adapter with runner for DID: {agent_manifest.did}")
            
            # # Register with registry if requested
            # if (registry_config.store_in_hibiscus and 
            #     hasattr(agent_manifest, 'did') and agent_manifest.did):
            #     logger.info(
            #         f"Registering agent '{agent_manifest.name}' with registry '{registry_config.registry_type}' "
            #         f"at {registry_config.registry_url}"
            #     )
            #     agent_manifest = register_with_registry(
            #         agent_manifest=agent_manifest,
            #         agent_registry=registry_config.registry_type,
            #         agent_registry_url=registry_config.registry_url,
            #         agent_registry_pat_token=registry_config.pat_token,
            #         **kwargs
            #     )
            #     logger.debug(f"Registry registration completed for agent '{agent_manifest.name}'")
            # else:
            #     if not registry_config.store_in_hibiscus:
            #         logger.info(f"Registry registration not requested for agent '{agent_manifest.name}'")
            #     elif not hasattr(agent_manifest, 'did') or not agent_manifest.did:
            #         logger.warning(f"Cannot register agent '{agent_manifest.name}' without a DID")
            
            # # Issue certificate if requested
            # if security_config.issue_certificate and hasattr(agent_manifest, 'did'):
            #     logger.info("Generating CSR for agent")
            #     # Note: generate_csr function needs to be imported if used
            #     # generate_csr(pki_dir=security_config.pki_dir, agent_name=agent_manifest.did)
            
            # return agent_manifest
            
        return wrapper
    return decorator


def _validate_agent_function(agent_function: Callable):
    """Validate that the function has the correct signature for protocol compliance."""
    signature = inspect.signature(agent_function)
    params = list(signature.parameters.values())
    
    if len(params) < 1:
        raise ValueError(
            "Agent function must have at least 'input' parameter of type PebblingMessage"
        )
    
    if len(params) > 2:
        raise ValueError(
            "Agent function must have only 'input' and optional 'context' parameters"
        )
    
    # Check parameter names
    if params[0].name != "input":
        raise ValueError("First parameter must be named 'input'")
    
    if len(params) == 2 and params[1].name != "context":
        raise ValueError("Second parameter must be named 'context'")


def _create_agent_manifest(
    agent_function: Callable,
    name: Optional[str],
    description: Optional[str],
    skills: Optional[List[Union[str, AgentSkill]]],
    domains: Optional[List[str]],
    capabilities: Optional[AgentCapabilities],
    version: str,
    user_id: str,
    extra_metadata: Optional[Dict[str, Any]]
) -> AgentManifest:
    """Create an AgentManifest from function metadata and parameters."""
    
    # Use function name if name not provided
    agent_name = name or agent_function.__name__.replace('_', '-')
    
    # Use docstring if description not provided
    agent_description = description or inspect.getdoc(agent_function) or f"Agent: {agent_name}"
    
    # Convert skills to AgentSkill objects
    agent_skills = []
    if skills:
        for skill in skills:
            if isinstance(skill, str):
                agent_skills.append(AgentSkill(
                    id=skill.lower().replace(' ', '-'),
                    name=skill.title(),
                    description=f"Skill: {skill}",
                    input_modes=["text"],
                    output_modes=["text"],
                    tags=domains or [skill.lower()]
                ))
            elif isinstance(skill, AgentSkill):
                agent_skills.append(skill)
    
    # Create default capabilities if not provided
    if capabilities is None:
        capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True
        )
    
    # Create the manifest
    manifest = AgentManifest(
        id=agent_name,
        name=agent_name.title(),
        description=agent_description,
        user_id=user_id,
        capabilities=capabilities,
        skills=agent_skills,
        version=version
    )
    
    # Add extra metadata if provided
    if extra_metadata:
        for key, value in extra_metadata.items():
            setattr(manifest, key, value)
    
    return manifest