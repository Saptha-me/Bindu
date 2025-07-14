"""Hibiscus DID registry integration for pebbling agents."""

import json
import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

class HibiscusRegistrar:
    """Client for registering agents with Hibiscus DID registry."""
    
    def __init__(
        self, 
        hibiscus_url: str = "http://localhost:19191", 
        api_key: Optional[str] = None
    ):
        """Initialize the Hibiscus registrar.
        
        Args:
            hibiscus_url: URL of the Hibiscus registry
            api_key: Optional API key for authentication
        """
        self.hibiscus_url = hibiscus_url
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    async def register_agent(
        self,
        agent_name: str,
        did: str,
        did_document: Dict[str, Any],
        description: str = "",
        capabilities: Optional[list] = None,
        domains: Optional[list] = None,
        tags: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        author_name: Optional[str] = None,
        version: str = "1.0.0"
    ) -> Dict[str, Any]:
        """Register an agent with the Hibiscus registry.
        
        Args:
            agent_name: Name of the agent
            did: The agent's DID string
            did_document: The agent's DID document
            description: Optional description of the agent
            capabilities: Optional list of agent capabilities
            domains: Optional list of domains the agent operates in
            tags: Optional list of tags for the agent
            metadata: Optional metadata for the agent
            endpoint: Optional API endpoint for the agent
            author_name: Optional author name
            version: Optional version string
            
        Returns:
            The response from the Hibiscus registry
        """
        # Extract public key from DID document
        public_key = None
        public_key_pem = None
        
        # First check for RSA keys (our new format)
        for method in did_document.get("verificationMethod", []):
            if method.get("type") == "RsaVerificationKey2018":
                public_key_pem = method.get("publicKeyPem", "")
                break
            elif method.get("type") == "Ed25519VerificationKey2020":
                public_key = method.get("publicKeyBase58", "")
                break
        
        # Prepare payload
        payload = {
            "name": agent_name,
            "description": description,
            "did": did,
            "did_document": did_document
        }
        
        # Add optional fields if provided
        if capabilities:
            payload["capabilities"] = capabilities
        if domains:
            payload["domains"] = domains
        if tags:
            payload["tags"] = tags
        if metadata:
            payload["metadata"] = metadata
        if endpoint:
            payload["api_endpoint"] = endpoint
        if author_name:
            payload["author_name"] = author_name
        if version:
            payload["version"] = version
        
        # Add the public key to the payload - use PEM format if available, otherwise Base58
        # Both go in the "public_key" field to maintain API contract
        if public_key_pem:
            payload["public_key"] = public_key_pem
        elif public_key:
            payload["public_key"] = public_key
        
        # Make the API request
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.hibiscus_url}/agents/"
                async with session.post(url, headers=self.headers, json=payload) as response:
                    response_data = await response.json()
                    if response.status != 201:
                        logger.error(f"Failed to register agent with Hibiscus: {response_data}")
                        return {"success": False, "error": response_data}
                    return {"success": True, "data": response_data}
        except Exception as e:
            logger.error(f"Exception registering agent with Hibiscus: {e}")
            return {"success": False, "error": str(e)}
            
    async def verify_registration(self, did: str) -> Dict[str, Any]:
        """Verify if a DID is registered with Hibiscus.
        
        Args:
            did: The DID to verify
            
        Returns:
            A dictionary with the verification result
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.hibiscus_url}/agents/did/{did}"
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"success": True, "registered": True, "data": data}
                    elif response.status == 404:
                        return {"success": True, "registered": False}
                    else:
                        error = await response.text()
                        return {"success": False, "error": error}
        except Exception as e:
            logger.error(f"Exception verifying registration with Hibiscus: {e}")
            return {"success": False, "error": str(e)}
