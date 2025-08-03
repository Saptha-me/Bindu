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
Certificate management for Sheldon CA.

This module handles certificate operations including fetching public certificates
and issuing agent certificates through the Sheldon CA infrastructure.
"""

import os
from typing import Dict, Any
import asyncio

from pebbling.protocol.types import AgentManifest
from pebbling.security.ca.sheldon.client import SheldonClient
from pebbling.utils.logging import get_logger
from pebbling.utils.constants import (
    CERTIFICATE_FILENAME,
    ROOT_CERTIFICATE_FILENAME,
)
from pebbling.utils.cert_helper import (
    save_certificate_to_file,
    get_cert_directory,
)

logger = get_logger("pebbling.security.ca.sheldon.certificates")


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
            
            if not root_cert_response.get("data").get("certificate"):
                logger.error(f"Failed to fetch root certificate: {root_cert_response.get('error')}")
                return {
                    "success": False, 
                    "error": f"Root certificate fetch failed: {root_cert_response.get('error')}"
                }
            
            root_certificate = root_cert_response.get("data").get("certificate")
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