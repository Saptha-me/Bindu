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

from pydantic.types import SecretStr

from pebbling.agent.agent_adapter import AgentAdapter, create_agent_adapter, PebblingContext, PebblingMessage
from pebbling.agent.metadata.setup_metadata import setup_agent_metadata
from pebbling.agent.runner import register_agent_adapter
from pebbling.hibiscus.agent_registry import register_with_registry
from pebbling.protocol.types import AgentCapabilities, AgentManifest, AgentSkill
from pebbling.security.setup_security import setup_security
from pebbling.security.ca.sheldon import issue_certificate

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.agent.pebblify")


class SecurityConfig:
    """Configuration for security features."""
    
    def __init__(
        self,
        did_required: bool = True,
        keys_required: bool = True,
        keys_dir: Optional[str] = None,
        recreate_keys: bool = False,
        issue_certificate: bool = True,
        cert_authority: str = "sheldon",
        verify_requests: bool = True
    ):
        self.did_required = did_required
        self.keys_required = keys_required
        self.keys_dir = keys_dir
        self.recreate_keys = recreate_keys
        self.issue_certificate = issue_certificate
        self.cert_authority = cert_authority
        self.verify_requests = verify_requests


class RegistryConfig:
    """Configuration for agent registry integration."""
    
    def __init__(
        self,
        store_in_hibiscus: bool = True,
        registry_url: str = "http://localhost:19191",
        pat_token: Optional[SecretStr] = None,
        registry_type: str = "hibiscus"
    ):
        self.store_in_hibiscus = store_in_hibiscus
        self.registry_url = registry_url
        self.pat_token = pat_token
        self.registry_type = registry_type


class DeploymentConfig:
    """Configuration for deployment and server setup."""
    
    def __init__(
        self,
        expose: bool = False,
        port: int = 3773,
        endpoint_type: str = "json-rpc",
        proxy_urls: Optional[List[str]] = None,
        cors_origins: Optional[List[str]] = None,
        openapi_schema: Optional[str] = None
    ):
        self.expose = expose
        self.port = port
        self.endpoint_type = endpoint_type
        self.proxy_urls = proxy_urls
        self.cors_origins = cors_origins
        self.openapi_schema = openapi_schema


def pebblify(
    name: Optional[str] = None,
    description: Optional[str] = None,
    skills: Optional[List[Union[str, AgentSkill]]] = None,
    domains: Optional[List[str]] = None,
    capabilities: Optional[AgentCapabilities] = None,
    version: str = "1.0.0",
    user_id: str = "default-user",
    
    # Legacy parameters for backward compatibility
    expose: bool = False,
    keys_required: Optional[bool] = True,
    keys_dir: Optional[str] = None,
    did_required: Optional[bool] = True,
    recreate_keys: Optional[bool] = False,
    agentdns_required: Optional[bool] = True,
    store_in_registry: Optional[bool] = True,
    agent_registry: Optional[Union[str, None]] = "hibiscus",
    agent_registry_url: Optional[str] = "http://localhost:19191",
    agent_registry_pat_token: Optional[SecretStr] = None,
    endpoint_type: str = "json-rpc",
    cert_authority: str = "sheldon", 
    issue_certificate: Optional[bool] = True,
    verify_requests: Optional[bool] = True,
    port: int = 3773,
    proxy_urls: Optional[List[str]] = None,
    cors_origins: Optional[List[str]] = None,
    opentelemetry: Optional[bool] = False,
    opentelemetry_url: Optional[str] = "http://localhost:4317",
    opentelemetry_service_name: Optional[str] = "pebble-agent",
    openapi_schema: Optional[str] = "http://localhost:3773/openapi.json",
    openapi_schema_path: Optional[str] = "openapi.json",
    openapi_schema_name: Optional[str] = "pebble-agent",
    show_trust_values: Optional[bool] = False,
    debug: Optional[bool] = False,
    use_colors: Optional[bool] = True,
    extra_metadata: Optional[Dict[str, Any]] = None,
    
    # New config objects (preferred)
    security: Optional[SecurityConfig] = None,
    registry: Optional[RegistryConfig] = None,
    deployment: Optional[DeploymentConfig] = None,
    
    **kwargs: Any
) -> Callable:
    """Transform a protocol-compliant function into a Pebbling-compatible agent.
    
    This decorator handles agent setup, security configuration, registry integration,
    and protocol compatibility. It configures DID-based security, manages keys,
    and enables agent discovery through registry services.
    
    The decorated function should accept PebblingMessage and optionally PebblingContext,
    and return/yield PebblingMessage objects.
    
    Args:
        name: Agent name. If not provided, uses function name.
        description: Agent description. If not provided, uses function docstring.
        skills: List of skills (strings or AgentSkill objects).
        domains: List of domain tags.
        capabilities: Agent capabilities configuration.
        version: Agent version.
        user_id: User ID for the agent.
        
        # Configuration objects (preferred)
        security: Security configuration object.
        registry: Registry configuration object.
        deployment: Deployment configuration object.
        
        # Legacy parameters maintained for backward compatibility
        expose: Whether to expose the agent as a web service.
        keys_required: Whether cryptographic keys are required for security.
        keys_dir: Directory to store keys. If None, uses default location.
        did_required: Whether DID identity is required for the agent.
        recreate_keys: Whether to recreate keys if they already exist.
        store_in_registry: Whether to register the agent with Hibiscus registry.
        
    Returns:
        A decorated function that implements the Pebbling agent protocol.
        
    Example:
        @pebblify(
            name="News Reporter",
            description="Reports news with flair",
            skills=["news-reporting", "storytelling"],
            security=SecurityConfig(did_required=True),
            registry=RegistryConfig(store_in_hibiscus=True),
            deployment=DeploymentConfig(expose=True, port=3773)
        )
        async def news_reporter(
            input: PebblingMessage, 
            context: PebblingContext
        ) -> AsyncGenerator[PebblingMessage, None]:
            text = input.get_text()
            # Use any framework internally
            agent = Agent(model=OpenAIChat(id="gpt-4o"))
            result = await agent.arun(text)
            yield PebblingMessage.from_text(result.content)
    """
    def decorator(agent_function: Callable) -> AgentManifest:
        # Validate that this is a protocol-compliant function
        _validate_agent_function(agent_function)
        
        @functools.wraps(agent_function)
        def wrapper(*args, **kwargs) -> AgentManifest:
            logger.debug("Creating agent with pebblify decorator")
            
            # Create agent manifest from function metadata
            agent_manifest = _create_agent_manifest(
                agent_function=agent_function,
                name=name,
                description=description,
                skills=skills,
                domains=domains,
                capabilities=capabilities,
                version=version,
                user_id=user_id,
                extra_metadata=extra_metadata
            )
            
            # Setup basic agent metadata
            setup_agent_metadata(agent_manifest, name)
            
            # Merge config objects with legacy parameters
            security_config = security or SecurityConfig(
                did_required=did_required,
                keys_required=keys_required,
                keys_dir=keys_dir,
                recreate_keys=recreate_keys,
                issue_certificate=issue_certificate,
                cert_authority=cert_authority,
                verify_requests=verify_requests
            )
            
            registry_config = registry or RegistryConfig(
                store_in_hibiscus=store_in_registry,
                registry_url=agent_registry_url,
                pat_token=agent_registry_pat_token,
                registry_type=agent_registry
            )
            
            deployment_config = deployment or DeploymentConfig(
                expose=expose,
                port=port,
                endpoint_type=endpoint_type,
                proxy_urls=proxy_urls,
                cors_origins=cors_origins,
                openapi_schema=openapi_schema
            )
            
            # Setup security if requested
            if security_config.did_required or security_config.keys_required:
                logger.info(
                    f"Setting up security for agent '{agent_manifest.name}' "
                    f"(did_required={security_config.did_required}, keys_required={security_config.keys_required})"
                )
                agent_manifest = setup_security(
                    agent_manifest=agent_manifest,
                    name=agent_manifest.name,
                    keys_required=security_config.keys_required,
                    keys_dir=security_config.keys_dir,
                    did_required=security_config.did_required,
                    recreate_keys=security_config.recreate_keys
                )
            else:
                logger.info(f"Skipping security setup for agent '{agent_manifest.name}'")
            
            # Create agent adapter
            adapter = create_agent_adapter(agent_function, agent_manifest)
            
            # Register adapter with runner if agent has DID
            if hasattr(agent_manifest, 'did') and agent_manifest.did:
                register_agent_adapter(agent_manifest.did, adapter)
                logger.debug(f"Registered agent adapter with runner for DID: {agent_manifest.did}")
            
            # Register with registry if requested
            if (registry_config.store_in_hibiscus and 
                hasattr(agent_manifest, 'did') and agent_manifest.did):
                logger.info(
                    f"Registering agent '{agent_manifest.name}' with registry '{registry_config.registry_type}' "
                    f"at {registry_config.registry_url}"
                )
                agent_manifest = register_with_registry(
                    agent_manifest=agent_manifest,
                    agent_registry=registry_config.registry_type,
                    agent_registry_url=registry_config.registry_url,
                    agent_registry_pat_token=registry_config.pat_token,
                    **kwargs
                )
                logger.debug(f"Registry registration completed for agent '{agent_manifest.name}'")
            else:
                if not registry_config.store_in_hibiscus:
                    logger.info(f"Registry registration not requested for agent '{agent_manifest.name}'")
                elif not hasattr(agent_manifest, 'did') or not agent_manifest.did:
                    logger.warning(f"Cannot register agent '{agent_manifest.name}' without a DID")
            
            # Issue certificate if requested
            if security_config.issue_certificate and hasattr(agent_manifest, 'did'):
                logger.info("Generating CSR for agent")
                # Note: generate_csr function needs to be imported if used
                # generate_csr(keys_dir=security_config.keys_dir, agent_name=agent_manifest.did)
            
            return agent_manifest
            
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