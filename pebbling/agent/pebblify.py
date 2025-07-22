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
1. Key generation and DID document creation
2. Certificate management via Sheldon
3. Secure server setup with MLTS
4. Agent registration with Hibiscus
"""

import functools
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic.types import SecretStr

from pebbling.agent.metadata.setup_metadata import setup_agent_metadata
from pebbling.hibiscus.agent_registry import register_with_registry
from pebbling.protocol.types import AgentManifest
from pebbling.security.setup_security import setup_security
from pebbling.security.ca.sheldon import issue_certificate

# Import logging from pebbling utils
from pebbling.utils.logging import get_logger

# Configure logging for the module
logger = get_logger("pebbling.agent.pebblify")

def pebblify(
    name: Optional[str] = None,
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
    **kwargs: Any
) -> Callable:
    """Transform a function into a Pebbling-compatible agent.
    
    This decorator handles agent setup, security configuration, registry integration,
    and protocol compatibility. It configures DID-based security, manages keys,
    and enables agent discovery through registry services.
    
    Args:
        name: Optional name for the agent. If not provided, the function name is used.
        expose: Whether to expose the agent as a web service.
        keys_required: Whether cryptographic keys are required for security.
        keys_dir: Directory to store keys. If None, uses default location.
        did_required: Whether DID identity is required for the agent.
        recreate_keys: Whether to recreate keys if they already exist.
        agentdns_required: Whether AgentDNS integration is required.
        store_in_registry: Whether to register the agent with Hibiscus registry.
        
    Returns:
        A decorated function that implements the Pebbling agent protocol.
    """
    def decorator(obj: Any) -> Any:
        @functools.wraps(obj)
        def wrapper(*args, **kwargs) -> AgentManifest:
            logger.debug("Creating agent with pebblify decorator")
            agent_manifest = obj(*args, **kwargs)
            
            # Extract basic agent information
            setup_agent_metadata(agent_manifest, name)
            
            # Setup security if requested
            if did_required or keys_required:
                logger.info(
                    f"Setting up security for agent '{agent_manifest.name}' "
                    f"(did_required={did_required}, keys_required={keys_required})"
                )
                agent_manifest = setup_security(
                    agent_manifest=agent_manifest,
                    name=agent_manifest.name,
                    keys_required=keys_required,
                    keys_dir=keys_dir,
                    did_required=did_required,
                    recreate_keys=recreate_keys
                )
            else:
                logger.info(f"Skipping security setup for agent '{agent_manifest.name}'")
                logger.debug(
                    f"Security setup skipped for agent '{agent_manifest.name}' "
                    f"(did_required={did_required}, keys_required={keys_required})"
                )
                
            # Register with registry if requested
            if store_in_registry and hasattr(agent_manifest, 'did') and agent_manifest.did:
                logger.info(
                    f"Registering agent '{agent_manifest.name}' with registry '{agent_registry}' "
                    f"at {agent_registry_url}"
                )
                agent_manifest = register_with_registry(
                    agent_manifest=agent_manifest,
                    agent_registry=agent_registry,
                    agent_registry_url=agent_registry_url,
                    agent_registry_pat_token=agent_registry_pat_token,
                    **kwargs
                )
                logger.debug(f"Registry registration completed for agent '{agent_manifest.name}'")
            else:
                if not store_in_registry:
                    logger.info(f"Registry registration not requested for agent '{agent_manifest.name}'")
                elif not hasattr(agent_manifest, 'did') or not agent_manifest.did:
                    logger.warning(f"Cannot register agent '{agent_manifest.name}' without a DID")
                
            # Issue certificate if requested
            if issue_certificate and callable(issue_certificate):
                logger.info("Generating CSR for agent")
                generate_csr(keys_dir=keys_dir, agent_name=agent_manifest.did)
                
            return agent_manifest
            
        return wrapper
    return decorator