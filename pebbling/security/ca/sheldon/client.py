# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Sheldon CA integration for Pebbling servers."""

from typing import Any, Dict, Optional
import os

from pebbling.protocol.types import AgentManifest
from pebbling.utils.http_helper import make_api_request
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
            
            # No authentication required for public certificates
            response = await make_api_request(
                url=url,
                method="GET"
            )
            
            if response["success"]:
                logger.info(f"Successfully fetched public certificate for {ca_name}")
                return response["data"]
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
                return response["data"]
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
            # Step 1: Request authentication challenge
            did = agent_manifest.identity.did if agent_manifest.identity else None
            if not did:
                return {"success": False, "error": "Agent DID is required for certificate issuance"}
            
            challenge_response = await self.request_challenge(did)
            if not challenge_response.get("challenge"):
                return challenge_response
            
            challenge = challenge_response.get("challenge")
            if not challenge:
                return {"success": False, "error": "No challenge received from CA"}
            
            # Step 2: Create JWT with challenge response
            jwt_token = generate_challenge_response_jwt(
                agent_manifest=agent_manifest,
                challenge=challenge,
                expiry_minutes=5  # Short-lived for security
            )
            
            # Step 3: Prepare form data for certificate issuance
            if not csr_file_path:
                # Try to generate CSR path from security config
                if hasattr(agent_manifest, 'security') and hasattr(agent_manifest.security, 'pki_dir'):
                    csr_file_path = os.path.join(agent_manifest.security.pki_dir, CSR_FILENAME)
                else:
                    return {"success": False, "error": "CSR file path is required for certificate issuance"}
            
            # Check if CSR file exists
            if not os.path.exists(csr_file_path):
                return {"success": False, "error": f"CSR file not found: {csr_file_path}"}
            
            # Step 4: Submit certificate request with form data
            url = f"{self.sheldon_url}/{ISSUE_CERTIFICATE_ENDPOINT}"
            
            # Prepare form data
            try:
                with open(csr_file_path, 'rb') as csr_file:
                    files = {
                        'csr': ('agent_csr.pem', csr_file.read(), 'application/x-pem-file')
                    }
                    
                    form_data = {
                        'agent_did': did
                    }
                    
                    # Add any additional form fields from kwargs
                    form_data.update(kwargs)
                    
                    # Include JWT in Authorization header
                    headers = {
                        "Authorization": f"Bearer {jwt_token}",
                        "accept": "application/json"
                    }
                    
                    # Use different approach for multipart form data
                    import aiohttp
                    import aiofiles
                    
                    async with aiohttp.ClientSession() as session:
                        # Read CSR file content
                        async with aiofiles.open(csr_file_path, 'r') as f:
                            csr_content = await f.read()
                        
                        # Create multipart form data
                        data = aiohttp.FormData()
                        data.add_field('csr', csr_content, filename='agent_csr.pem', content_type='application/x-pem-file')
                        data.add_field('agent_did', did)
                        
                        # Add additional form fields
                        for key, value in kwargs.items():
                            data.add_field(key, str(value))
                        
                        async with session.post(url, data=data, headers=headers) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"Successfully issued certificate for agent: {agent_manifest.name}")
                                return {"success": True, "data": result}
                            else:
                                error_text = await response.text()
                                logger.error(f"Failed to issue certificate: {response.status} - {error_text}")
                                return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                                
            except FileNotFoundError:
                return {"success": False, "error": f"CSR file not found: {csr_file_path}"}
            except Exception as e:
                return {"success": False, "error": f"Failed to read CSR file: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error issuing certificate: {e}")
            return {"success": False, "error": str(e)}
