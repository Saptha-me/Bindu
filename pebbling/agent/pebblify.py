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

from pebbling.protocol.types import (
    AgentCapabilities, 
    AgentManifest, 
    AgentSkill
)
from pebbling.common.models.models import (
    SecurityCredentials, 
    AgentRegistration, 
    CAConfig, 
    DeploymentConfig
)

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.agent.pebblify")

def pebblify(
    name: Optional[str] = None,
    id: Optional[str] = None,
    version: str = "1.0.0",
    skill: Optional[AgentSkill] = None,
    capabilities: Optional[AgentCapabilities] = None,
    credentials: SecurityCredentials = None,  
    registration_config: Optional[AgentRegistration] = None,
    ca_config: Optional[CAConfig] = None,
    deployment_config: Optional[DeploymentConfig] = None,
    
) -> Callable:
    """Transform a protocol-compliant function into a Pebbling-compatible agent.
    
    """
    def decorator(agent_function: Callable) -> AgentManifest:
        # Validate that this is a protocol-compliant function
        _validate_agent_function(agent_function)
        
        _manifest = _create_manifest(
            agent_function=agent_function,
            name=name,
            description=None,
            skills=[skill] if skill else None,
            capabilities=capabilities,
            version=version,
            extra_metadata=None,
            credentials=credentials,
            registration_config=registration_config,
            ca_config=ca_config,
            deployment_config=deployment_config
        )
            
            # # Setup basic agent metadata
            # setup_agent_metadata(agent_manifest, name)
            
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
    
    if len(params) > 1:
        raise ValueError(
            "Agent function must have only 'input' and optional 'context' parameters"
        )
    
    # Check parameter names
    if params[0].name != "input":
        raise ValueError("First parameter must be named 'input'")
    


def _create_manifest(
    id: Optional[str],
    function: Callable,
    name: Optional[str],
    description: Optional[str],
    skills: Optional[List[Union[str, AgentSkill]]],
    capabilities: Optional[AgentCapabilities],
    version: str,
    extra_metadata: Optional[Dict[str, Any]],
    credentials: Optional[SecurityCredentials] = None,
    registration_config: Optional[AgentRegistration] = None,
    ca_config: Optional[CAConfig] = None,
    deployment_config: Optional[DeploymentConfig] = None
) -> AgentManifest:
    """Create dynamic agent class from function analysis."""
    
    # Since function is already validated, we can directly check parameter names
    sig = inspect.signature(function)
    param_names = list(sig.parameters.keys())
    has_context_param = 'context' in param_names
    has_execution_state = 'execution_state' in param_names
    
    # Use function name if name not provided
    name = name or function.__name__.replace('_', '-')
    description = description or inspect.getdoc(function) or f"Agent: {name}"
    
    # Create default capabilities if not provided
    if capabilities is None:
        capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True
        )
    
    # Convert skills to AgentSkill objects if needed
    skills = []
    if skills:
        for skill in skills:
            if isinstance(skill, str):
                skills.append(AgentSkill(
                    id=skill.lower().replace(' ', '-'),
                    name=skill.title(),
                    description=f"Skill: {skill}",
                    input_modes=["text"],
                    output_modes=["text"],
                    tags=[skill.lower()]
                ))
            elif isinstance(skill, AgentSkill):
                skills.append(skill)
    elif isinstance(skills, AgentSkill):
        skills = [skills]
    
    class DecoratorBase(AgentManifest):
        @property
        def id(self) -> str:
            return id
        
        @property
        def name(self) -> str:
            return name
        
        @property
        def description(self) -> str:
            return description
        
        @property
        def capabilities(self) -> AgentCapabilities:
            return capabilities
        
        @property
        def skills(self) -> List[AgentSkill]:
            return skills
        
        @property
        def version(self) -> str:
            return version
    
    # Create agent based on function type
    agent: AgentManifest
    
    if inspect.isasyncgenfunction(_function):
        class AsyncGenDecoratorAgent(DecoratorBase):
            async def run(self, input_msg: str, context=None, **kwargs):
                """Run async generator agent function."""
                try:
                    if has_execution_state:
                        # Handle execution state for pause/resume
                        execution_state = kwargs.get('execution_state')
                        gen = _function(input_msg, execution_state)
                    elif has_context_param:
                        gen = _function(input_msg, context)
                    else:
                        gen = _function(input_msg)
                    
                    async for result in gen:
                        yield result
                        
                except StopAsyncIteration:
                    pass
        
        agent = AsyncGenDecoratorAgent()
        
    elif inspect.iscoroutinefunction(agent_function):
        class CoroDecoratorAgent(DecoratorAgentBase):
            async def run(self, input_msg: str, context=None, **kwargs):
                """Run coroutine agent function."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    return await agent_function(input_msg, execution_state)
                elif has_context_param:
                    return await agent_function(input_msg, context)
                else:
                    return await agent_function(input_msg)
        
        agent = CoroDecoratorAgent()
        
    elif inspect.isgeneratorfunction(agent_function):
        class GenDecoratorAgent(DecoratorAgentBase):
            def run(self, input_msg: str, context=None, **kwargs):
                """Run generator agent function."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    yield from agent_function(input_msg, execution_state)
                elif has_context_param:
                    yield from agent_function(input_msg, context)
                else:
                    yield from agent_function(input_msg)
        
        agent = GenDecoratorAgent()
        
    else:
        class FuncDecoratorAgent(DecoratorAgentBase):
            def run(self, input_msg: str, context=None, **kwargs):
                """Run regular function agent."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    return agent_function(input_msg, execution_state)
                elif has_context_param:
                    return agent_function(input_msg, context)
                else:
                    return agent_function(input_msg)
        
        agent = FuncDecoratorAgent()
    
    # Add extra metadata if provided
    if extra_metadata:
        for key, value in extra_metadata.items():
            setattr(agent, key, value)
    
    return agent