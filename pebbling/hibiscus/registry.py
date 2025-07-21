"""Hibiscus DID registry integration for Pebbling servers."""

from typing import Any, Dict, List, Optional
from loguru import logger

from pebbling.security.did.manager import DIDManager
from pebbling.security.hibiscus import HibiscusRegistrar


async def register_agent_with_hibiscus_registry(
    did_manager: Optional[DIDManager],
    agent: Any,
    agent_id: str,
    hibiscus_api_key: Optional[str],
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    agent_capabilities: Optional[List[Dict[str, str]]] = None,
    agent_domains: Optional[List[str]] = None,
    agent_tags: Optional[List[str]] = None,
    agent_metadata: Optional[Dict[str, Any]] = None,
    endpoint: str = "http://localhost:3773",
    author_name: Optional[str] = None,
    version: str = "1.0.0"
) -> bool:
    """Register an agent with the Hibiscus DID registry.
    
    Args:
        did_manager: DID manager for agent identity
        agent: Agent object
        agent_id: Agent ID
        hibiscus_url: URL of Hibiscus registry
        hibiscus_api_key: API key for Hibiscus registry
        agent_name: Name of the agent
        agent_description: Description of the agent
        agent_capabilities: List of agent capabilities
        agent_domains: List of domains the agent operates in
        agent_tags: List of tags for the agent
        agent_metadata: Additional metadata
        endpoint: Service endpoint for the agent
        author_name: Name of the agent author
        version: Version string
        
    Returns:
        True if registration was successful, False otherwise
    """
    if did_manager is None:
        logger.warning("Cannot register with Hibiscus: no DID manager found")
        return False
    
    try:
        # Use agent name from parameter or try to get it from agent, or use agent_id
        if agent_name is None:
            agent_name = getattr(agent, 'name', agent_id)
        
        # If we're running on localhost but the endpoint in DID document is different, use that
        for service in did_manager.did_document.get("service", []):
            if service.get("type") == "PebbleAgentCard":
                endpoint = service.get("serviceEndpoint", endpoint)
                break
        
        logger.info(f"Registering agent '{agent_name}' with Hibiscus at {hibiscus_url}")
        
        # Initialize Hibiscus registrar
        registrar = HibiscusRegistrar(
            hibiscus_url=hibiscus_url,
            api_key=hibiscus_api_key
        )
        
        # Register the agent
        registration_result = await registrar.register_agent(
            agent_name=agent_name,
            did=did_manager.get_did(),
            did_document=did_manager.get_did_document(),
            description=agent_description or "",
            capabilities=agent_capabilities,
            domains=agent_domains,
            tags=agent_tags,
            metadata=agent_metadata,
            endpoint=endpoint,
            author_name=author_name,
            version=version
        )
        
        if registration_result.get("success"):
            logger.info(f"Successfully registered agent with Hibiscus: {agent_name}")
            return True
        else:
            logger.error(f"Failed to register with Hibiscus: {registration_result.get('error')}")
            return False
                
    except Exception as e:
        logger.error(f"Error during Hibiscus registration: {e}")
        return False