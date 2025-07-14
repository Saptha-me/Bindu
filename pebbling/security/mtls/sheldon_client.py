"""
Client for interacting with the Sheldon CA service.

This module provides a client for requesting and verifying certificates
from the Sheldon Certificate Authority service, which is used to establish
mTLS connections between Pebbling agents.
"""

import logging
from typing import Dict, Any, Optional

import aiohttp

from pebbling.security.config import SHELDON_CA_ENDPOINTS
from pebbling.security.mtls.exceptions import (
    SheldonCAError,
    CertificateRequestError,
    CertificateVerificationError
)

logger = logging.getLogger(__name__)


class SheldonCAClient:
    """Client for the Sheldon Certificate Authority service.
    
    This client handles:
    1. Requesting certificates from the CA
    2. Verifying certificates with the CA
    3. Retrieving the CA's public certificate
    """
    
    def __init__(self, base_url: str):
        """Initialize the Sheldon CA client.
        
        Args:
            base_url: Base URL of the Sheldon CA service
        """
        self.base_url = base_url.rstrip("/")
        
    async def issue_certificate(self, did: str, public_key: str) -> Dict[str, Any]:
        """Request a certificate from the Sheldon CA.
        
        Args:
            did: DID of the requesting agent
            public_key: PEM-encoded public key
            
        Returns:
            Dict containing the issued certificate or error
            
        Raises:
            CertificateRequestError: If the request fails
        """
        logger.info(f"Requesting certificate from Sheldon CA for DID: {did}")
        
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{self.base_url}{SHELDON_CA_ENDPOINTS['issue_certificate']}"
                async with session.post(
                    endpoint,
                    json={
                        "did": did,
                        "public_key": public_key
                    },
                    ssl=False  # Initial connection doesn't have mTLS yet
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_msg = f"CA request failed: {response.status}, {result}"
                        logger.error(error_msg)
                        raise CertificateRequestError(error_msg)
                        
                    logger.info(f"Successfully received certificate for {did}")
                    return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"Error requesting certificate from CA: {str(e)}"
            logger.error(error_msg)
            raise CertificateRequestError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error when requesting certificate: {str(e)}"
            logger.error(error_msg)
            raise SheldonCAError(error_msg) from e
            
    async def verify_certificate(self, certificate: str) -> Dict[str, Any]:
        """Verify a certificate with the Sheldon CA.
        
        Args:
            certificate: PEM-encoded certificate
            
        Returns:
            Dict with verification result including token and expiration
            
        Raises:
            CertificateVerificationError: If verification fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{self.base_url}{SHELDON_CA_ENDPOINTS['verify_certificate']}"
                async with session.post(
                    endpoint,
                    json={"certificate": certificate},
                    ssl=False  # No mTLS for verification
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_msg = f"Certificate verification failed: {response.status}"
                        logger.error(error_msg)
                        raise CertificateVerificationError(error_msg)
                        
                    return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"Error verifying certificate: {str(e)}"
            logger.error(error_msg)
            raise CertificateVerificationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during certificate verification: {str(e)}"
            logger.error(error_msg)
            raise SheldonCAError(error_msg) from e
            
    async def get_ca_certificate(self) -> Dict[str, Any]:
        """Get the CA's public certificate.
        
        Returns:
            Dict containing the CA certificate
            
        Raises:
            SheldonCAError: If fetching the CA certificate fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{self.base_url}{SHELDON_CA_ENDPOINTS['public_certificate']}"
                async with session.get(
                    endpoint,
                    ssl=False  # No mTLS for getting CA cert
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_msg = f"Failed to get CA certificate: {response.status}"
                        logger.error(error_msg)
                        raise SheldonCAError(error_msg)
                        
                    return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"Error getting CA certificate: {str(e)}"
            logger.error(error_msg)
            raise SheldonCAError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error when getting CA certificate: {str(e)}"
            logger.error(error_msg)
            raise SheldonCAError(error_msg) from e
