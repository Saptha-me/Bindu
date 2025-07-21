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
from typing import Any, Optional, Callable, Union, List, Dict

from fastapi import FastAPI

# Import necessary components
from pebbling.security.did.manager import DIDManager
from pebbling.security.common.keys import generate_key_pair
#from pebbling.security.mlts import MLTSManager
#from pebbling.hibiscus.registry import HibiscusRegistry
#from pebbling.server.pebbling_server import create_server

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
    agent_registry_url: Optional[str] = "https://api.pebbling.ai",
    agent_registry_personal_access_token: Optional[str] = None,
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
        
        agent_registry (Optional[Union[str, None]]): 
            Name of the registry service to use. Currently supported: "hibiscus".
            Default: "hibiscus"
        
        agent_registry_url (Optional[str]): 
            URL of the agent registry service. Default: "https://api.pebbling.ai"
        
        agent_registry_personal_access_token (Optional[str]): 
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
        def wrapper(*args, **kwargs):
            # Get the base agent from the wrapped function
            agent = obj(*args, **kwargs)

            # Ensure agent has an ID
            agent.id = getattr(agent, 'id', str(uuid.uuid4()))
            
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
                
            # Generate keys if needed
            if keys_required:
                generate_key_pair(current_keys_dir, recreate=recreate_keys)
                setattr(agent, "keys_dir", current_keys_dir)

            # Get Agent Capabilities
            capabilities = get_agent_capabilities(agent)

            # Get Agent Skills
            skills = get_agent_skills(agent)
        
            # Set up DID if required
            did_manager = None
            if did_required:
                if not current_keys_dir:
                    raise ValueError("Keys are required for DID functionality")
                
                did_config_path = os.path.join(current_keys_dir, "did.json")
                did_manager = DIDManager(
                    config_path=did_config_path,
                    keys_dir=current_keys_dir,
                    capabilities=capabilities,
                    skills=skills,
                    recreate=recreate_keys
                )
                
            # Register with Hibiscus registry if requested
            if store_in_registry and did_manager:
                HibiscusClient().register_agent(
                    did=did_manager.get_did(),
                    capabilities=capabilities,
                    skills=skills,
                    endpoint=f"https://{agent.id}.api.pebbling.ai"
                )
            
            # If expose=True, create server and fetch certificate
            if expose:
                # Create CSR for Sheldon
                if cert_authority == "sheldon":
                    csr = did_manager.create_csr(
                        common_name=f"{agent.id}.api.pebbling.ai",
                        organization="Pebbling",
                        org_unit="Agent",
                        country="US"
                    )
                    
                    # Get certificate from Sheldon
                    # Certificate will be stored in agent's key directory
                    certificate = request_certificate_from_sheldon(
                        csr=csr, 
                        did=did_manager.get_did()
                    )
                    
                # Create and configure FastAPI app
                app = FastAPI()
                
                # Create MLTS server with the certificate
                if endpoint_type == "mlts":
                    mlts_manager = MLTSManager(
                        private_key=did_manager.get_private_key(),
                        certificate=certificate
                    )
                    
                    # Setup MLTS configuration for the server
                    mlts_config = mlts_manager.get_server_config()
                    
                # Create Adapter for the agent
                adapter = AgentAdapter(agent)
                
                # Create and start the server (non-blocking)
                server = create_server(
                    app=app,
                    agent_adapter=adapter,
                    security_config=mlts_config if endpoint_type == "mlts" else None,
                    port=port
                )
                
                # Start server in background thread
                server.start()
                
                # Attach server to agent for lifecycle management
                agent._pebble_server = server
            
            # Attach Pebble attributes to agent
            agent.pebble_did = did_manager.get_did() if did_manager else None
            agent.pebble_did_document = did_manager.get_did_document() if did_manager else None
            
            # Return the enhanced agent
            return agent
        return wrapper
    return decorator

# Helper functions
def get_agent_capabilities(agent):
    """Extract capabilities from agent for registration."""
    # Implementation depends on agent type
    pass

def get_agent_skills(agent):
    """Extract skills from agent for registration."""
    # Implementation depends on agent type
    pass

def request_certificate_from_sheldon(csr, did):
    """Request certificate from Sheldon CA service."""
    # Implementation for certificate request
    pass