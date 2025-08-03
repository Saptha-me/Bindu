"""Sheldon CA integration for Pebbling servers."""

from typing import Any, Dict, Optional
import os

from pebbling.protocol.types import AgentManifest
from pebbling.utils.http_helper import make_api_request, make_multipart_request
from pebbling.utils.logging import get_logger
from pebbling.security.common.keys import generate_challenge_response_jwt
from pebbling.utils.constants import (
    PUBLIC_CERTIFICATE_ENDPOINT,
    ISSUE_CERTIFICATE_ENDPOINT,
    CHALLENGE_ENDPOINT,
    CSR_FILENAME
)

# Initialize logger for this module
logger = get_logger("pebbling.sheldon.client")


class SheldonClient:
    """Client for interacting with Sheldon CA with secure authentication."""
    
    def __init__(
        self,
        sheldon_url: str = "http://localhost:19190",
    ):
        """Initialize Sheldon client.
        
        Args:
            sheldon_url: URL of Sheldon CA
        """
        self.sheldon_url = sheldon_url

    async def fetch_public_certificate(
        self,
        ca_name: str = "root"
    ) -> Dict[str, Any]:
        """Fetch public certificate from CA (no authentication required).
        
        Args:
            ca_name: Certificate authority name
            
        Returns:
            Public certificate data
        """
        try:
            url = f"{self.sheldon_url}/{PUBLIC_CERTIFICATE_ENDPOINT}"
            
            response = await make_api_request(url=url, method="GET")
            
            if response["success"]:
                logger.info(f"Successfully fetched public certificate for {ca_name}")
            else:
                logger.error(f"Failed to fetch public certificate: {response['error']}")
                
            return response
                
        except Exception as e:
            logger.error(f"Error fetching public certificate: {e}")
            return {"success": False, "error": str(e)}

    async def request_challenge(
        self,
        did: str
    ) -> Dict[str, Any]:
        """Request authentication challenge from CA.
        
        Args:
            did: Agent's DID
            
        Returns:
            Challenge data including challenge string and expiry
        """
        try:
            url = f"{self.sheldon_url}/{CHALLENGE_ENDPOINT}"
            payload = {"did": did}
            
            response = await make_api_request(
                url=url,
                method="POST",
                payload=payload
            )
            
            if response["success"]:
                logger.info(f"Successfully requested challenge for DID: {did}")
            else:
                logger.error(f"Failed to request challenge: {response['error']}")
                
            return response
                
        except Exception as e:
            logger.error(f"Error requesting challenge: {e}")
            return {"success": False, "error": str(e)}
    
    async def issue_certificate(
        self,
        agent_manifest: AgentManifest,
        csr_file_path: Optional[str] = None,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Issue a certificate for an agent using secure authentication.
        
        This method implements secure two-step authentication:
        1. Request challenge from CA
        2. Sign challenge with private key to create JWT
        3. Submit CSR file with JWT authentication
        
        Args:
            agent_manifest: Agent manifest with DID and identity info
            csr_file_path: Path to Certificate Signing Request (CSR) file
            **kwargs: Additional parameters
            
        Returns:
            Response from Sheldon CA
        """
        try:
            # Step 1: Validate DID
            did = agent_manifest.identity.did if agent_manifest.identity else None
            if not did:
                return {"success": False, "error": "Agent DID is required for certificate issuance"}
            
            # Step 2: Request authentication challenge
            challenge_response = await self.request_challenge(did)
            if not challenge_response.get("success"):
                return challenge_response
            
            challenge_data = challenge_response.get("data", {})
            challenge = challenge_data.get("challenge")
            if not challenge:
                return {"success": False, "error": "No challenge received from CA"}
            
            # Step 3: Create JWT with challenge response
            jwt_token = generate_challenge_response_jwt(
                agent_manifest=agent_manifest,
                challenge=challenge,
                expiry_minutes=5  # Short-lived for security
            )
            
            # Step 4: Prepare CSR file path
            if not csr_file_path:
                if hasattr(agent_manifest, 'security') and hasattr(agent_manifest.security, 'pki_dir'):
                    csr_file_path = os.path.join(agent_manifest.security.pki_dir, CSR_FILENAME)
                else:
                    return {"success": False, "error": "CSR file path is required for certificate issuance"}
            
            # Step 5: Validate CSR file exists
            if not os.path.exists(csr_file_path):
                return {"success": False, "error": f"CSR file not found: {csr_file_path}"}
            
            # Step 6: Submit certificate request with multipart form data
            url = f"{self.sheldon_url}/{ISSUE_CERTIFICATE_ENDPOINT}"
            
            # Prepare files and form data
            files = {
                'csr': csr_file_path  # Will be handled by make_multipart_request
            }
            
            form_data = {
                'agent_did': did,
                **{k: str(v) for k, v in kwargs.items()}  # Convert all values to strings
            }
            
            headers = {
                "Authorization": f"Bearer {jwt_token}"
            }
            
            response = await make_multipart_request(
                url=url,
                files=files,
                form_data=form_data,
                headers=headers
            )
            
            if response["success"]:
                logger.info(f"Successfully issued certificate for agent: {agent_manifest.name}")
            else:
                logger.error(f"Failed to issue certificate: {response['error']}")
                
            return response
                
        except Exception as e:
            logger.error(f"Error issuing certificate: {e}")
            return {"success": False, "error": str(e)}
