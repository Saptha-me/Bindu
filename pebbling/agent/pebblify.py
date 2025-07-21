# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - Raahul

"""
Pebblify decorator for transforming regular agents into secure, networked Pebble agents.

This module provides the core decorator that handles:
1. Key generation and DID document creation
2. Certificate management via Sheldon
3. Secure server setup with MLTS
4. Agent registration with Hibiscus
"""

import functools
import os
import inspect
import uuid
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union
import json
from pydantic.types import SecretStr

# Import logging from pebbling utils
from pebbling.utils.logging import logger, configure_logger

# Import necessary components
from pebbling.security.did.manager import DIDManager
from pebbling.security.common.keys import generate_key_pair
from pebbling.protocol.types import (
    AgentManifest, 
    AgentCapabilities, 
    AgentSkill,
    AgentSecurity,
    AgentTrust,
    AgentIdentity
)
from pebbling.hibiscus.registry import HibiscusClient
#from pebbling.security.mlts import MLTSManager
#from pebbling.hibiscus.registry import HibiscusRegistry
#from pebbling.server.pebbling_server import create_server

# Configure logging for the module
configure_logger()

def pebblify(
    agent_name: Optional[str] = None,
    expose: bool = False,
    keys_required: Optional[bool] = True,
    keys_dir: Optional[str] = None,
    did_required: Optional[bool] = True,
    recreate_keys: Optional[bool] = True,
    agentdns_required: Optional[bool] = True,
    store_in_registry: Optional[bool] = True,
    agent_registry: Optional[Union[str, None]] = "hibiscus",
    agent_registry_url: Optional[str] = "http://localhost:19191",
    agent_registry_pat_token: Optional[SecretStr] = None,
    endpoint_type: str = "mlts",
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
    **kwargs: Any
) -> Callable:
    """
    Transform a regular agent into a secure, networked Pebble agent with DID-based security.
    
    This decorator automates the process of making an agent secure and discoverable in the
    Pebbling ecosystem. It handles key generation, DID document creation, certificate management,
    agent registration, and secure server setup with minimal configuration required.
    
    Args:
        agent_name (Optional[str]): 
            Custom name for the agent. If not provided, will be extracted from the agent object
            or generated as a UUID.
        
        expose (bool): 
            Whether to expose the agent via network with a server endpoint. When True, 
            creates a server using the specified endpoint_type. Default: False
        
        keys_required (Optional[bool]): 
            Whether to generate cryptographic keys for the agent. Required for DID and
            certificate generation. Default: True
        
        keys_dir (Optional[str]): 
            Path to store or load the agent's cryptographic keys. If None, keys will be
            generated in a 'keys' directory relative to the calling script with an 
            agent-specific filename. Default: None
        
        did_required (Optional[bool]): 
            Whether to generate a Decentralized Identifier (DID) for the agent.
            DIDs are used for identity verification and trust establishment. Default: True

        recreate_keys (Optional[bool]): 
            Whether to recreate the agent's cryptographic keys. If True, will generate
            new keys and update the agent's key file. Default: False
        
        agentdns_required (Optional[bool]): 
            Whether to register the agent with AgentDNS service for name resolution.
            Default: True
        
        store_in_registry (Optional[bool]): 
            Whether to register the agent in the specified agent registry for discovery
            by other agents. Default: True
        
        agent_registry (Optional[Union[str, None]] = "hibiscus"):
            Name of the registry service to use. Currently supported: "hibiscus".
            Default: "hibiscus"
        
        agent_registry_url (Optional[str]): 
            URL of the agent registry service. Default: "https://api.pebbling.ai"
        
        agent_registry_pat_token (Optional[SecretStr]): 
            PAT for authentication with the registry service. If None, will try to use
            environment variables. Default: None
        
        endpoint_type (str): 
            Type of endpoint to expose the agent with. Options:
            - "mlts": Mutual TLS server with certificate-based authentication
            - "http": Standard HTTP server without additional security
            - "json-rpc": JSON-RPC server with DID-based security
            Default: "mlts"
        
        cert_authority (str): 
            Certificate Authority to use for obtaining certificates.
            Options: "sheldon" (Pebbling's CA), "letsencrypt", "self-signed".
            Default: "sheldon"
        
        issue_certificate (Optional[bool]): 
            Whether to request a certificate from the specified CA. Requires keys_required
            and did_required to be True. Default: True
        
        verify_requests (Optional[bool]): 
            Whether to verify incoming requests using DID challenge-response protocol.
            Default: True
        
        port (int): 
            Port number to use for the server when expose=True. Default: 3773

        proxy_urls (Optional[List[str]]): 
            List of proxy URLs to use for requests. Default: None

        cors_origins (Optional[List[str]]): 
            List of origins to allow for CORS. Default: None
        
        extra_metadata (Optional[Dict[str, Any]]): 
            Additional metadata to include in the agent's registry entry. Default: None
        
        opentelemetry (Optional[bool]): 
            Whether to enable OpenTelemetry instrumentation for monitoring. Default: False
        
        opentelemetry_url (Optional[str]): 
            URL of the OpenTelemetry collector. Default: "http://localhost:4317"
        
        opentelemetry_service_name (Optional[str]): 
            Service name for OpenTelemetry. Default: "pebble-agent"
        
        openapi_schema (Optional[str]): 
            URL where the OpenAPI schema will be accessible. Default: "http://localhost:3773/openapi.json"
        
        openapi_schema_path (Optional[str]): 
            Path to store the OpenAPI schema file. Default: "openapi.json"
        
        openapi_schema_name (Optional[str]): 
            Name for the OpenAPI schema. Default: "pebble-agent"
        
        show_trust_values (Optional[bool]): 
            Whether to include trust verification values in logs and responses.
            Default: False
        
        debug (Optional[bool]): 
            Whether to enable debug logging. Default: False
        
        use_colors (Optional[bool]): 
            Whether to use colors in console output. Default: True

        kwargs (Any): 
            Additional keyword arguments to pass to the agent constructor.
    
    Returns:
        Callable: Decorated function that returns an agent with Pebbling capabilities
    
    Examples:
        ```python
        # Basic usage with default settings - agent not exposed
        @pebblify()
        def create_agent():
            return Agent(...)
        
        # Create an exposed agent with custom name and port
        @pebblify(
            agent_name="news_assistant",
            expose=True,
            port=8000
        )
        def create_news_agent():
            return Agent(...)
        
        # Advanced configuration with custom registry and certificates
        @pebblify(
            expose=True,
            key_path="custom/keys/my_agent.json",
            agent_registry="custom_registry",
            agent_registry_url="https://my-registry.example.com",
            endpoint_type="json-rpc",
            cert_authority="letsencrypt"
        )
        def create_secure_agent():
            return Agent(...)
        ```
    
    Note:
        When exposing an agent (expose=True), the server runs in a background thread
        and does not block the main application. The server is automatically stopped
        when the Python process exits.
    """
    def decorator(obj: Any) -> Any:
        @functools.wraps(obj)
        def wrapper(*args, **kwargs) -> AgentManifest:
            # Get the base agent from the wrapped function
            logger.debug(f"Creating agent with pebblify decorator")
            agent_manifest: AgentManifest = obj(*args, **kwargs)
            
            # Ensure agent has an ID
            agent_id = getattr(agent_manifest.agent, 'id', str(uuid.uuid4()))
            logger.debug(f"Agent ID: {agent_id}")
            
            # Access the keys_dir from the outer scope
            nonlocal keys_dir
            current_keys_dir = keys_dir
            
            # Set up keys directory if needed
            if not current_keys_dir:
                # Create keys directory relative to the calling script
                caller_file = inspect.getframeinfo(inspect.currentframe().f_back).filename
                caller_dir = os.path.dirname(os.path.abspath(caller_file))
                current_keys_dir = os.path.join(caller_dir, 'keys')
                os.makedirs(current_keys_dir, exist_ok=True)
                logger.debug(f"Created keys directory: {current_keys_dir}")
                
            # Generate keys if needed
            if keys_required:
                logger.info(f"Generating key pair in {current_keys_dir}")
                generate_key_pair(current_keys_dir, recreate=recreate_keys)
        
            # Set up DID if required
            did_manager = None
            if did_required:
                if not current_keys_dir:
                    logger.error("Keys directory not set but required for DID functionality")
                    raise ValueError("Keys are required for DID functionality")
                
                logger.info("Initializing DID Manager")
                did_config_path = os.path.join(current_keys_dir, "did.json")
                did_manager = DIDManager(
                    config_path=did_config_path,
                    keys_dir=current_keys_dir,
                    capabilities=agent_manifest.capabilities,
                    skills=agent_manifest.skills,
                    recreate=recreate_keys
                )

            # Set up the agent identity
            agent_manifest.identity = AgentIdentity(
                did=did_manager.get_did(),
                agentdns_url=did_manager.get_agentdns_url(),
                endpoint=did_manager.get_endpoint(),
                public_key=did_manager.get_public_key()
            )   

            
                
            # Register with Hibiscus registry if requested
            if store_in_registry and did_manager:
                if agent_registry == "hibiscus":
                    logger.info(f"Registering agent with Hibiscus at {agent_registry_url}")
                    hibiscus_client = HibiscusClient(
                        hibiscus_url=agent_registry_url,
                        pat_token=agent_registry_pat_token
                    )
                    import asyncio
                    try:
                        asyncio.run(hibiscus_client.register_agent(
                            did=did_manager.get_did(),
                            agent_manifest=agent_manifest,
                            did_document=did_manager.get_did_document(),
                            **kwargs
                        ))
                        logger.info(f"Successfully registered agent with DID: {did_manager.get_did()}")
                    except Exception as e:
                        logger.error(f"Failed to register agent with Hibiscus: {str(e)}")
                elif agent_registry == "custom":
                    logger.info("Using custom agent registry")
                    pass
                else:
                    logger.error(f"Unknown agent registry: {agent_registry}")
                    raise ValueError(f"Unknown agent registry: {agent_registry}")

                
            
            # If expose=True, create server and fetch certificate
            if expose:
                logger.info("Setting up server for exposed agent")
                # Create CSR for Sheldon
                if cert_authority == "sheldon":
                    logger.debug("Creating CSR for Sheldon CA")
                    csr = did_manager.create_csr(
                        common_name=f"{agent.id}.api.pebbling.ai",
                        organization="Pebbling",
                        org_unit="Agent",
                        country="US"
                    )
                    
                    # Get certificate from Sheldon
                    # Certificate will be stored in agent's key directory
                    logger.info("Requesting certificate from Sheldon CA")
                    certificate = request_certificate_from_sheldon(
                        csr=csr, 
                        did=did_manager.get_did()
                    )
                    
                # Create and configure FastAPI app
                logger.debug("Creating FastAPI app")
                app = FastAPI()
                
                # Create MLTS server with the certificate
                if endpoint_type == "mlts":
                    logger.debug("Setting up MLTS server")
                    mlts_manager = MLTSManager(
                        private_key=did_manager.get_private_key(),
                        certificate=certificate
                    )
                    
                    # Setup MLTS configuration for the server
                    mlts_config = mlts_manager.get_server_config()
                    
                # Create Adapter for the agent
                logger.debug("Creating agent adapter")
                adapter = AgentAdapter(agent)
                
                # Create and start the server (non-blocking)
                logger.info(f"Creating server on port {port}")
                server = create_server(
                    app=app,
                    agent_adapter=adapter,
                    security_config=mlts_config if endpoint_type == "mlts" else None,
                    port=port
                )
                
                # Start server in background thread
                logger.info("Starting server in background thread")
                server.start()
                
                # Attach server to agent for lifecycle management
                agent._pebble_server = server
            
            # Attach Pebble attributes to agent
            agent.pebble_did = did_manager.get_did() if did_manager else None
            agent.pebble_did_document = did_manager.get_did_document() if did_manager else None
            
            # Return the AgentManifest with enhanced agent
            logger.debug("Returning enhanced agent manifest")
            return agent_manifest
        return wrapper
    return decorator

# Helper functions
def get_agent_capabilities(agent):
    """
    Extract capabilities from agent for registration.
    
    This function checks if the agent already has capabilities defined in the proper format.
    If not, it tries to extract capability-related attributes from the agent object.
    
    Args:
        agent: The agent object
        
    Returns:
        AgentCapabilities: Object containing the agent's capabilities
    """
    from pebbling.protocol.types import AgentCapabilities, AgentExtension
    
    logger.debug("Extracting agent capabilities")
    
    # If agent is an AgentManifest with capabilities already set, return those
    if hasattr(agent, 'capabilities') and isinstance(agent.capabilities, AgentCapabilities):
        logger.debug("Using existing AgentCapabilities from agent")
        return agent.capabilities
        
    # If agent has capabilities as a property/method
    if hasattr(agent, 'capabilities') and callable(getattr(agent, 'capabilities')):
        logger.debug("Calling agent.capabilities() method")
        caps = agent.capabilities()
        # If the returned value is already an AgentCapabilities, return it
        if isinstance(caps, AgentCapabilities):
            return caps
        # Otherwise try to convert to AgentCapabilities
        elif isinstance(caps, dict):
            return AgentCapabilities(**caps)
    
    # Extract capabilities from agent attributes
    logger.debug("Extracting capabilities from agent attributes")
    streaming = getattr(agent, 'streaming', None)
    push_notifications = getattr(agent, 'push_notifications', None)
    state_transition_history = getattr(agent, 'state_transition_history', None)
    
    # Get extensions if available
    extensions = []
    if hasattr(agent, 'extensions'):
        ext_list = agent.extensions
        if isinstance(ext_list, list):
            for ext in ext_list:
                if isinstance(ext, AgentExtension):
                    extensions.append(ext)
                elif isinstance(ext, dict) and 'uri' in ext:
                    extensions.append(AgentExtension(**ext))
    
    # Create and return capabilities
    return AgentCapabilities(
        streaming=streaming,
        push_notifications=push_notifications,
        state_transition_history=state_transition_history,
        extensions=extensions if extensions else None
    )

def get_agent_skills(agent):
    """
    Extract skills from agent for registration.
    
    This function checks if the agent already has skills defined in the proper format.
    If not, it tries to extract skill-related attributes from the agent object.
    
    Args:
        agent: The agent object
        
    Returns:
        list[AgentSkill]: List of skills the agent supports
    """
    from pebbling.protocol.types import AgentSkill
    
    logger.debug("Extracting agent skills")
    
    # If agent is an AgentManifest with skills already set, return those
    if hasattr(agent, 'skills'):
        skills = agent.skills
        if isinstance(skills, list):
            # If skills is already a list of AgentSkill objects
            if all(isinstance(skill, AgentSkill) for skill in skills):
                logger.debug(f"Using existing {len(skills)} skills from agent")
                return skills
            # If skills is a list of dicts, try to convert them
            elif all(isinstance(skill, dict) for skill in skills):
                logger.debug(f"Converting {len(skills)} skill dictionaries to AgentSkill objects")
                return [AgentSkill(**skill) for skill in skills if 'id' in skill and 'name' in skill]
    
    # If agent has skills as a property/method
    if hasattr(agent, 'skills') and callable(getattr(agent, 'skills')):
        logger.debug("Calling agent.skills() method")
        skill_list = agent.skills()
        if isinstance(skill_list, list):
            # If already AgentSkill objects
            if all(isinstance(skill, AgentSkill) for skill in skill_list):
                return skill_list
            # If dicts with required fields
            elif all(isinstance(skill, dict) for skill in skill_list):
                return [AgentSkill(**skill) for skill in skill_list if 'id' in skill and 'name' in skill]
    
    # If we can't extract skills, return a single basic skill based on agent properties
    logger.debug("Creating default skill from agent properties")
    if hasattr(agent, 'name') and hasattr(agent, 'description'):
        name = agent.name
        description = agent.description
        
        # Extract input/output modes from content types if available
        input_modes = None
        output_modes = None
        
        if hasattr(agent, 'input_content_types') and agent.input_content_types:
            input_modes = ["text"]  # Default to text
            if any("image" in content_type for content_type in agent.input_content_types):
                input_modes.append("image")
            if any("audio" in content_type for content_type in agent.input_content_types):
                input_modes.append("audio")
                
        if hasattr(agent, 'output_content_types') and agent.output_content_types:
            output_modes = ["text"]  # Default to text
            if any("image" in content_type for content_type in agent.output_content_types):
                output_modes.append("image")
            if any("audio" in content_type for content_type in agent.output_content_types):
                output_modes.append("audio")
        
        # Create a default skill from agent properties
        default_skill = AgentSkill(
            id=getattr(agent, 'id', str(uuid.uuid4())),
            name=name,
            description=description,
            input_modes=input_modes,
            output_modes=output_modes,
            tags=["ai", "agent"],  # Default tags
        )
        
        return [default_skill]
    
    # If we can't create a skill, return empty list
    logger.warning("Could not extract or create skills for agent")
    return []

def request_certificate_from_sheldon(csr, did):
    """Request certificate from Sheldon CA service."""
    logger.info(f"Requesting certificate from Sheldon for DID: {did}")
    # Implementation for certificate request
    pass