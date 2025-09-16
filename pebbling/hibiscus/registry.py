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
from typing import Any, Dict

from pydantic.types import SecretStr

from pebbling.common.models import AgentManifest
from pebbling.utils.http_helper import make_api_request
from pebbling.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("pebbling.hibiscus")


class HibiscusClient:
    """Client for interacting with Hibiscus agent registry."""
    
    def __init__(
        self,
        pat_token: SecretStr,
        email: str,
        hibiscus_url: str = "http://localhost:19191",
    ):
        """Initialize Hibiscus client.
        
        Args:
            hibiscus_url: URL of Hibiscus registry
            pat_token: API key for authentication with Hibiscus registry
            email: Email address associated with the API key
        """
        self.hibiscus_url = hibiscus_url
        self.pat_token = pat_token
        self.email = email
        self.agents_endpoint = f"{self.hibiscus_url}/agents"
        self.auth_challenge_endpoint = f"{self.hibiscus_url}/auth/api-challenge"
        self.auth_token_endpoint = f"{self.hibiscus_url}/auth/api-token"
    
    async def request_api_challenge(self) -> Dict[str, Any]:
        """Request an authentication challenge using API key.
            
        Returns:
            Challenge response containing challenge string and expiration
        """
        payload = {
            "api_key": str(self.pat_token.get_secret_value()),
            "email": self.email
        }
        
        try:
            response = await make_api_request(
                url=self.auth_challenge_endpoint,
                method="POST",
                payload=payload
            )
            
            if response["success"]:
                return response["data"]
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Failed to request API challenge: {error_msg}")
                raise Exception(f"Failed to request API challenge: {error_msg}")
        except Exception as e:
            logger.error(f"Error requesting API challenge: {str(e)}")
            raise
    
    async def get_api_token(self, challenge: str) -> str:
        """Get JWT access token using API key and challenge.
        
        Args:
            challenge: Challenge string from previous request
            
        Returns:
            JWT access token
        """
        payload = {
            "api_key": str(self.pat_token.get_secret_value()),
            "email": self.email,
            "challenge": challenge
        }
        
        try:
            response = await make_api_request(
                url=self.auth_token_endpoint,
                method="POST",
                payload=payload
            )
            
            if response["success"]:
                return response["data"]["access_token"]
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Failed to get API token: {error_msg}")
                raise Exception(f"Failed to get API token: {error_msg}")
        except Exception as e:
            logger.error(f"Error getting API token: {str(e)}")
            raise
    
    async def authenticate(self) -> str:
        """Perform full authentication flow to get JWT token.
            
        Returns:
            JWT access token
        """
        try:
            # Step 1: Request challenge
            challenge_response = await self.request_api_challenge()
            challenge = challenge_response["challenge"]
            
            # Step 2: Get token using challenge
            access_token = await self.get_api_token(challenge)
            
            logger.info(f"Successfully authenticated for email: {self.email}")
            return access_token
        except Exception as e:
            logger.error(f"Authentication failed for email {self.email}: {str(e)}")
            raise
    
    async def register_agent(
        self,
        agent_manifest: AgentManifest,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register an agent with Hibiscus registry.
        
        Args:
            agent_manifest: Agent manifest with capabilities and skills
            **kwargs: Additional fields to include in the registration
            
        Returns:
            Response from Hibiscus registry
        """
        # First authenticate to get JWT token
        access_token = await self.authenticate()
        try:
            # Extract data from manifest - access properties correctly
            payload = {
                "name": agent_manifest.name,
                "description": agent_manifest.description,
                "version": agent_manifest.version,
                "did": agent_manifest.identity.did if agent_manifest.identity else None,
                "public_key": agent_manifest.identity.public_key if agent_manifest.identity else None,
                "did_document": agent_manifest.identity.did_document if agent_manifest.identity else None,
            }
            
            # Process capabilities - convert to AgentCapabilities format
            capabilities = {
                "push_notifications": None,
                "state_transition_history": None,
                "streaming": None
            }
            
            if agent_manifest and hasattr(agent_manifest, 'capabilities'):
                if hasattr(agent_manifest.capabilities, 'model_dump'):
                    try:
                        # Get capabilities from pydantic model and map to expected format
                        caps_dict = agent_manifest.capabilities.model_dump(exclude_none=True)
                        # Map common capability names to expected fields
                        if "push_notifications" in caps_dict:
                            capabilities["push_notifications"] = bool(caps_dict["push_notifications"])
                        if "state_transition_history" in caps_dict:
                            capabilities["state_transition_history"] = bool(caps_dict["state_transition_history"])
                        if "streaming" in caps_dict:
                            capabilities["streaming"] = bool(caps_dict["streaming"])
                    except Exception as e:
                        logger.error(f"Error processing capabilities: {e}")
            
            payload["capabilities"] = capabilities
            
            # Process skills - convert to AgentSkill format
            skills = []
            
            if agent_manifest and hasattr(agent_manifest, 'skill'):
                try:
                    skill_dict = agent_manifest.skill.model_dump(exclude_none=True)
                    
                    # Create AgentSkill object with required fields
                    skill = {
                        "id": skill_dict.get("id", skill_dict.get("name", "default").lower().replace(" ", "_")),
                        "name": skill_dict.get("name", ""),
                        "description": skill_dict.get("description", ""),
                        "tags": skill_dict.get("tags", ["general"]),  # Required field, default to "general"
                        "examples": skill_dict.get("examples", [])  # Optional field
                    }
                    
                    # Ensure tags are lowercase and within limits (1-16 items)
                    if skill["tags"]:
                        skill["tags"] = [tag.lower() for tag in skill["tags"][:16]]
                    else:
                        skill["tags"] = ["general"]
                    
                    skills.append(skill)
                    
                except Exception as e:
                    logger.error(f"Error processing skill: {e}")
                    # Add default skill if processing fails
                    skills.append({
                        "id": "default",
                        "name": "General Purpose",
                        "description": "General purpose agent capability",
                        "tags": ["general"],
                        "examples": []
                    })
            else:
                # Add default skill if no skill is provided
                skills.append({
                    "id": "default",
                    "name": "General Purpose", 
                    "description": "General purpose agent capability",
                    "tags": ["general"],
                    "examples": []
                })
            
            payload["skills"] = skills
            
            # Add optional fields if available
            if hasattr(agent_manifest, "documentation") and agent_manifest.documentation:
                payload["documentation"] = agent_manifest.documentation
            
            if hasattr(agent_manifest, "api_endpoint") and agent_manifest.api_endpoint:
                payload["api_endpoint"] = str(agent_manifest.api_endpoint)
                
            if hasattr(agent_manifest, "image_url") and agent_manifest.image_url:
                payload["image_url"] = str(agent_manifest.image_url)
                
            if hasattr(agent_manifest, "website_url") and agent_manifest.website_url:
                payload["website_url"] = str(agent_manifest.website_url)
                
            if hasattr(agent_manifest, "contact_email") and agent_manifest.contact_email:
                payload["contact_email"] = agent_manifest.contact_email
            
            # Extract public key from DID document if available
            if (agent_manifest and agent_manifest.identity and 
                hasattr(agent_manifest.identity, "did_document") and 
                agent_manifest.identity.did_document):
                
                payload["did_document"] = agent_manifest.identity.did_document
                
                # Extract public key from DID document verification methods
                for vm in payload["did_document"].get("verificationMethod", []):
                    if "publicKeyPem" in vm:
                        payload["public_key"] = vm.get("publicKeyPem", "")
                        break
            
            # Update with any additional kwargs
            for key, value in kwargs.items():
                if key not in payload and value is not None:
                    payload[key] = value
            
            # Make the API call with JWT token
            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                logger.debug(f"Sending registration to Hibiscus: {self.agents_endpoint}")
                response = await make_api_request(
                    url=self.agents_endpoint,
                    method="POST",
                    payload=payload,
                    headers=headers
                )
                
                if response["success"]:
                    logger.info(f"Successfully registered agent with Hibiscus: {agent_manifest.name}")
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
