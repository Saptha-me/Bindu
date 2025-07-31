# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Hibiscus DID registry integration for Pebbling servers."""

import json
from typing import Any, Dict, Optional

from pydantic.types import SecretStr

from pebbling.protocol.types import AgentManifest
from pebbling.utils.http_helper import make_api_request
from pebbling.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("pebbling.hibiscus")


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
        self.agents_endpoint = f"{self.hibiscus_url}/agents/"
    
    async def register_agent(
        self,
        did: Optional[str] = None,
        endpoint: Optional[str] = None,
        agent_manifest: Optional[AgentManifest] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Register an agent with Hibiscus registry.
        
        Args:
            did: DID of the agent
            endpoint: API endpoint of the agent
            agent_manifest: Agent manifest with capabilities and skills
            **kwargs: Additional fields to include in the registration
            
        Returns:
            Response from Hibiscus registry
        """
        try:
            # Extract data from manifest if provided
            agent_name = agent_manifest.name if agent_manifest else kwargs.get("name")
            if agent_manifest:
                payload = {
                    "name": agent_name,
                    "description": getattr(agent_manifest, "description", ""),
                    "version": getattr(agent_manifest, "version", "1.0.0"),
                    "author_name": "Your Name",
                    "did": agent_manifest.identity.did,
                    "public_key": agent_manifest.identity.public_key,
                    "did_document": agent_manifest.identity.did_document,
                }
                
                # Process capabilities
                capabilities = []
                if agent_manifest and hasattr(agent_manifest, 'capabilities'):
                    if hasattr(agent_manifest.capabilities, 'model_dump'):
                        try:
                            # Get capabilities from pydantic model
                            caps_dict = agent_manifest.capabilities.model_dump(exclude_none=True)
                            for cap_name, cap_details in caps_dict.items():
                                desc = ("No description" if not isinstance(cap_details, dict) 
                                       else cap_details.get("description", "No description"))
                                capabilities.append({"name": cap_name, "description": desc})
                        except Exception as e:
                            logger.error(f"Error processing capabilities: {e}")
                    payload["capabilities"] = capabilities
                
                # Process skills and extract domains/tags
                skills = []
                domains = set()
                tags = set()
                
                if agent_manifest and hasattr(agent_manifest, 'skills'):
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

                # Add Dependencies
                if hasattr(agent_manifest, "instance") and hasattr(agent_manifest.instance, "model"):
                    model = agent_manifest.instance.model
                    dependency = {
                        "type": "model",
                        "name": getattr(model, "name", model.__class__.__name__),
                        "version": getattr(model, "version", "latest"),
                    }
                    payload["dependencies"] = [dependency]  # Array of dependencies
                else:
                    payload["dependencies"] = []  # Empty array instead of missing field
                
                # Fix DID document - ensure publicKeyPem is properly set
                if "did_document" in payload and payload["did_document"]:
                    for method in payload["did_document"].get("verificationMethod", []):
                        if method.get("publicKeyPem") is None and "public_key" in payload:
                            method["publicKeyPem"] = payload["public_key"]
                
                # Add metadata
                metadata = {
                    "framework": "Pebbling",
                    "programming_language": "Python"
                }
                if hasattr(agent_manifest, "metadata") and agent_manifest.metadata:
                    metadata.update(agent_manifest.metadata)
                payload["metadata"] = metadata
            else:
                # Ensure did and endpoint are provided if no manifest
                if not did or not endpoint:
                    logger.error("Missing required parameters (did or endpoint) for agent registration")
                    return None
                    
                # Basic payload if no manifest
                payload = {
                    "name": kwargs.get("name", f"agent-{did[-8:] if did else 'unknown'}"),
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
            
            # Make the API call
            headers = {"Authorization": f"Bearer {self.pat_token}"}
            try:
                logger.debug(f"Sending registration to Hibiscus: {self.agents_endpoint}")
                response = await make_api_request(
                    url=self.agents_endpoint,
                    api_key=self.pat_token,
                    method="POST",
                    payload=payload,
                    headers=headers
                )
                
                if response["success"]:
                    logger.info(f"Successfully registered agent with Hibiscus: {agent_name}")
                    return response["data"]
                else:
                    error_msg = response.get("error", "Unknown error")
                    if response.get("status_code") == 422:
                        logger.error(f"Validation error (422) from Hibiscus API: {error_msg}")
                        logger.debug("Payload that caused the error: " + json.dumps(payload, indent=2, default=str))
                    else:
                        logger.error(f"Failed to register agent: {error_msg}")
                    raise Exception(f"Failed to register agent: {error_msg}")
            except Exception as e:
                logger.error(f"Error during agent registration: {str(e)}")
                raise
        
        except Exception as e:
            logger.error(f"Error registering agent with Hibiscus: {e}")
            return {"success": False, "error": str(e)}
