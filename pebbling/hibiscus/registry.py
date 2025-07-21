"""Hibiscus DID registry integration for Pebbling servers."""

from typing import Any, Dict, List, Optional, Union
from pydantic.types import SecretStr

from pebbling.protocol.types import AgentManifest, AgentCapabilities, AgentSkill
from pebbling.security.did.manager import DIDManager
from pebbling.utils.http_helper import make_api_request


class HibiscusClient:
    """Client for interacting with Hibiscus agent registry."""
    
    def __init__(
        self,
        hibiscus_url: str = "http://localhost:19191",
        pat_token: Optional[SecretStr] = None
    ):
        """Initialize Hibiscus client.
        
        Args:
            hibiscus_url: URL of Hibiscus registry
            pat_token: PAT token for authentication with Hibiscus registry
        """
        self.hibiscus_url = hibiscus_url
        self.pat_token = pat_token
        self.agents_endpoint = f"{self.hibiscus_url}/api/v1/agents/"
    
    async def register_agent(
        self,
        did: str,
        agent_manifest: Optional[AgentManifest] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Register an agent with Hibiscus registry.
        
        Args:
            did: DID of the agent
            agent_manifest: Agent manifest with capabilities and skills
            **kwargs: Additional fields to include in the registration
            
        Returns:
            Response from Hibiscus registry
        """
        try:
            # Extract data from manifest if provided
            if agent_manifest:
                payload = {
                    "name": agent_manifest.name,
                    "did": did,
                    "api_endpoint": agent_manifest.api_endpoint,
                    "version": getattr(agent_manifest, "version", "1.0.0"),
                    "description": getattr(agent_manifest, "description", "")
                }
                
                # Process capabilities
                capabilities = []
                if agent_manifest.capabilities:
                    caps_dict = agent_manifest.capabilities.model_dump(exclude_none=True)
                    for cap_name, cap_details in caps_dict.items():
                        desc = cap_details.get("description", "No description") if isinstance(cap_details, dict) else "No description"
                        capabilities.append({"name": cap_name, "description": desc})
                payload["capabilities"] = capabilities
                
                # Process skills and extract domains/tags
                skills = []
                domains = set()
                tags = set()
                
                if agent_manifest.skills:
                    for skill in agent_manifest.skills:
                        skill_dict = skill.model_dump(exclude_none=True)
                        skills.append({
                            "name": skill_dict.get("name", ""),
                            "description": skill_dict.get("description", "")
                        })
                        
                        if "domains" in skill_dict:
                            domains.update(skill_dict["domains"])
                        if "tags" in skill_dict:
                            tags.update(skill_dict["tags"])
                
                payload["skills"] = skills
                payload["domains"] = list(domains)
                payload["tags"] = list(tags)
                
                # Add metadata
                metadata = {
                    "framework": "Pebbling",
                    "programming_language": "Python"
                }
                if hasattr(agent_manifest, "metadata") and agent_manifest.metadata:
                    metadata.update(agent_manifest.metadata)
                payload["metadata"] = metadata
            else:
                # Basic payload if no manifest
                payload = {
                    "name": kwargs.get("name", f"agent-{did[-8:]}"),
                    "did": did,
                    "api_endpoint": endpoint
                }
            
            # Add DID document if provided
            if "did_document" in kwargs:
                payload["did_document"] = kwargs["did_document"]
                
                # Extract public key from DID document
                for vm in payload["did_document"].get("verificationMethod", []):
                    if "publicKeyPem" in vm:
                        payload["public_key"] = vm.get("publicKeyPem", "")
                        break
            
            # Update with any additional kwargs
            for key, value in kwargs.items():
                if key not in payload and value is not None:
                    payload[key] = value
            
            # Make API request
            logger.info(f"Registering agent '{payload.get('name')}' with Hibiscus")
            return await make_api_request(
                url=self.agents_endpoint,
                method="POST",
                payload=payload,
                api_key=self.pat_token
            )
        
        except Exception as e:
            logger.error(f"Error registering agent with Hibiscus: {e}")
            return {"success": False, "error": str(e)}
