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
Certificate fetching module for fetching Pebbling agents with Sheldon CA.
"""

import asyncio
import os
from typing import Any, Dict
from pydantic.types import SecretStr

from pebbling.security.ca.sheldon.client import SheldonClient
from pebbling.protocol.types import AgentManifest
from pebbling.utils.logging import get_logger
from pebbling.utils.constants import (
    CERTIFICATE_DIR,
    CERTIFICATE_FILENAME,
    ROOT_CERTIFICATE_FILENAME,
    CERT_FILE_EXTENSION
)

logger = get_logger("pebbling.security.ca.sheldon.certificates")


def save_certificate_to_file(cert_content: str, file_path: str) -> bool:
    """Save certificate content to file.
    
    Args:
        cert_content: Certificate content (PEM format)
        file_path: Full path to save the certificate
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write certificate to file
        with open(file_path, 'w') as f:
            f.write(cert_content)
        
        logger.info(f"Certificate saved to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save certificate to {file_path}: {e}")
        return False


def get_cert_directory(agent_manifest: AgentManifest) -> str:
    """Get certificate directory from agent manifest or use default.
    
    Args:
        agent_manifest: Agent manifest with security configuration
        
    Returns:
        Path to certificate directory
    """
    # Check if agent manifest has cert_dir specified
    if (hasattr(agent_manifest, 'security') and 
        hasattr(agent_manifest.security, 'cert_dir') and 
        agent_manifest.security.cert_dir):
        return agent_manifest.security.cert_dir
    
    # Check alternative location in security config
    if (hasattr(agent_manifest, 'security_config') and 
        hasattr(agent_manifest.security_config, 'cert_dir') and 
        agent_manifest.security_config.cert_dir):
        return agent_manifest.security_config.cert_dir
    
    # Use default examples/certs directory
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "examples",
        CERTIFICATE_DIR
    )


def fetch_certificate(
    agent_manifest: AgentManifest,
    ca_url: str,
    ca_type: str = "sheldon",
    save_to_disk: bool = True,
    **kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Fetch certificates for mTLS connection setup.
    
    This function performs two operations:
    1. Fetch root/public certificate for trust chain verification
    2. Issue agent certificate using CSR for client authentication
    3. Optionally save certificates to disk for mTLS usage
    
    Args:
        agent_manifest: Agent manifest with DID and security config
        ca_url: URL of the Certificate Authority
        ca_type: Type of CA (default: "sheldon")
        save_to_disk: Whether to save certificates to disk (default: True)
        **kwargs: Additional parameters for certificate issuance
        
    Returns:
        Dict containing both root_certificate, agent_certificate, and file paths
    """
    if ca_type == "sheldon":
        logger.info(f"Fetching certificates from Sheldon CA at {ca_url}")
        sheldon_client: SheldonClient = SheldonClient(sheldon_url=ca_url)
        
        try:
            # Step 1: Fetch root/public certificate (no authentication required)
            logger.info("Fetching root certificate for trust chain verification")
            root_cert_response = asyncio.run(sheldon_client.fetch_public_certificate(
                ca_name="root"
            ))
            
            if not root_cert_response.get("certificate"):
                logger.error(f"Failed to fetch root certificate: {root_cert_response.get('error')}")
                return {
                    "success": False, 
                    "error": f"Root certificate fetch failed: {root_cert_response.get('error')}"
                }
            
            root_certificate = root_cert_response.get("certificate")
            logger.info("Successfully fetched root certificate")
            
            # Step 2: Issue agent certificate (requires authentication)
            logger.info(f"Issuing agent certificate for DID: {agent_manifest.identity.did if agent_manifest.identity else 'unknown'}")
            agent_cert_response = asyncio.run(sheldon_client.issue_certificate(
                agent_manifest=agent_manifest,
                **kwargs
            ))
            
            if not agent_cert_response.get("success"):
                logger.error(f"Failed to issue agent certificate: {agent_cert_response.get('error')}")
                return {
                    "success": False,
                    "error": f"Agent certificate issuance failed: {agent_cert_response.get('error')}"
                }
            
            agent_certificate = agent_cert_response.get("data").get("certificate")
            logger.info("Successfully issued agent certificate")
            
            # Step 3: Save certificates to disk if requested
            cert_files = {}
            if save_to_disk:
                cert_dir = get_cert_directory(agent_manifest)
                logger.info(f"Saving certificates to directory: {cert_dir}")
                
                # Save root certificate
                root_cert_path = os.path.join(cert_dir, ROOT_CERTIFICATE_FILENAME)
                if save_certificate_to_file(root_certificate, root_cert_path):
                    cert_files["root_cert_path"] = root_cert_path
                
                # Save agent certificate
                agent_cert_path = os.path.join(cert_dir, CERTIFICATE_FILENAME)
                if save_certificate_to_file(agent_certificate, agent_cert_path):
                    cert_files["agent_cert_path"] = agent_cert_path
            
            # Return both certificates and file paths for mTLS setup
            result_data = {
                "root_certificate": root_certificate,
                "agent_certificate": agent_certificate,
                "ca_url": ca_url,
                "ca_type": ca_type
            }
            
            # Add file paths if certificates were saved
            if cert_files:
                result_data.update(cert_files)
            
            return {
                "success": True,
                "data": result_data
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch certificates from Sheldon CA: {str(e)}")
            return {
                "success": False,
                "error": f"Certificate operations failed: {str(e)}"
            }
            
    elif ca_type == "custom":
        logger.info("Using custom CA")
        raise ValueError("Custom CA not implemented yet")
    else:
        logger.error(f"Unknown CA type: {ca_type}")
        raise ValueError(f"Unknown CA type: {ca_type}")