"""
Certificate lifecycle management for mTLS.

This module handles the core certificate lifecycle operations including
requesting, storing, and renewing certificates from a Certificate Authority.
"""

import os
import logging
import datetime
from typing import Dict, Any, Optional, Tuple

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.sheldon_client import SheldonCAClient
from pebbling.security.mtls.utils import extract_certificate_info
from pebbling.security.config import DEFAULT_CERTIFICATE_VALIDITY
from pebbling.security.mtls.exceptions import (
    CertificateError,
    CertificateRequestError
)

logger = logging.getLogger(__name__)


class CertLifecycleManager:
    """Manages the core lifecycle of mTLS certificates.
    
    This class handles:
    1. Requesting certificates from the CA
    2. Storing and loading certificates
    3. Certificate renewal checks
    """
    
    def __init__(
        self,
        did_manager: DIDManager,
        ca_client: SheldonCAClient,
        cert_dir: str
    ):
        """Initialize the certificate lifecycle manager.
        
        Args:
            did_manager: DID manager for identity operations
            ca_client: Client for communicating with the CA
            cert_dir: Directory for storing certificates and keys
        """
        self.did_manager = did_manager
        self.ca_client = ca_client
        self.cert_dir = cert_dir
        
        # Create certificate directory if it doesn't exist
        os.makedirs(self.cert_dir, exist_ok=True)
        
        # File paths
        self.did = did_manager.did
        self.cert_path = os.path.join(self.cert_dir, f"{self.did}.crt")
        self.key_path = os.path.join(self.cert_dir, f"{self.did}.key")
        self.ca_cert_path = os.path.join(self.cert_dir, "ca.crt")
        
        # Certificate info cache
        self._cert_info = None
            
    async def ensure_ca_certificate(self) -> None:
        """Ensure we have the CA certificate.
        
        Fetches the CA certificate if it doesn't exist.
        
        Returns:
            None
            
        Raises:
            CertificateError: If getting the CA certificate fails
        """
        if os.path.exists(self.ca_cert_path):
            logger.debug(f"Using existing CA certificate at {self.ca_cert_path}")
            return
            
        try:
            logger.info("Fetching CA certificate")
            ca_result = await self.ca_client.get_ca_certificate()
            
            if not ca_result.get("certificate"):
                raise CertificateError("CA did not return a certificate")
                
            with open(self.ca_cert_path, "w") as f:
                f.write(ca_result["certificate"])
                
            logger.info(f"Saved CA certificate to {self.ca_cert_path}")
            
        except Exception as e:
            error_msg = f"Failed to get CA certificate: {str(e)}"
            logger.error(error_msg)
            raise CertificateError(error_msg) from e
            
    def has_valid_certificate(self) -> bool:
        """Check if we have a valid certificate.
        
        Returns:
            True if we have a valid certificate, False otherwise
        """
        # Check if certificate and key files exist
        if not (os.path.exists(self.cert_path) and os.path.exists(self.key_path)):
            logger.info(f"Certificate or key file missing for {self.did}")
            return False
            
        try:
            # Read certificate
            with open(self.cert_path, "r") as f:
                cert_pem = f.read()
                
            # Extract certificate info
            cert_info = extract_certificate_info(cert_pem)
            
            # Check if certificate is expired
            not_after = datetime.datetime.fromisoformat(cert_info["validity"]["not_after"])
            if datetime.datetime.utcnow() >= not_after:
                logger.warning(f"Certificate for {self.did} has expired")
                return False
                
            # Check if certificate is valid for this DID
            if not cert_info["subject"]["common_name"] == self.did:
                logger.warning(f"Certificate subject does not match DID: {self.did}")
                return False
                
            # Cache certificate info
            self._cert_info = cert_info
            
            # All checks passed
            return True
            
        except Exception as e:
            logger.warning(f"Error checking certificate validity: {str(e)}")
            return False
            
    async def request_certificate(self) -> Dict[str, Any]:
        """Request a certificate from the Sheldon CA.
        
        Returns:
            Dict with certificate information
            
        Raises:
            CertificateRequestError: If the request fails
        """
        try:
            # Get the public key from the DID document
            did_document = self.did_manager.get_did_document()
            public_key = did_document["verificationMethod"][0]["publicKeyPem"]
            
            # Request certificate from CA
            result = await self.ca_client.issue_certificate(self.did, public_key)
            
            if not result.get("certificate"):
                raise CertificateRequestError("CA did not return a certificate")
                
            # Save certificate
            with open(self.cert_path, "w") as f:
                f.write(result["certificate"])
                
            # Save private key (should already be managed by DID manager)
            # For simplicity, we're just copying it here
            private_key = self.did_manager.load_private_key()
            with open(self.key_path, "w") as f:
                f.write(private_key)
                
            # Update certificate info cache
            with open(self.cert_path, "r") as f:
                cert_pem = f.read()
            self._cert_info = extract_certificate_info(cert_pem)
            
            logger.info(f"Successfully obtained and saved certificate for {self.did}")
            
            return self._cert_info
            
        except Exception as e:
            error_msg = f"Failed to request certificate: {str(e)}"
            logger.error(error_msg)
            raise CertificateRequestError(error_msg) from e
    
    def should_renew_certificate(self) -> bool:
        """Check if the certificate should be renewed.
        
        Returns:
            True if renewal is needed, False otherwise
        """
        try:
            # Read certificate
            with open(self.cert_path, "r") as f:
                cert_pem = f.read()
                
            # Extract certificate info
            cert_info = extract_certificate_info(cert_pem)
            
            # Parse expiration date
            not_after = datetime.datetime.fromisoformat(cert_info["validity"]["not_after"])
            
            # Renew if less than 25% of validity period remains
            total_validity = (not_after - datetime.datetime.fromisoformat(cert_info["validity"]["not_before"])).total_seconds()
            remaining = (not_after - datetime.datetime.utcnow()).total_seconds()
            
            return remaining < (total_validity * 0.25)
            
        except Exception as e:
            logger.error(f"Error checking if certificate needs renewal: {str(e)}")
            # If we can't check, assume renewal is needed
            return True
            
    def get_certificate_info(self) -> Dict[str, Any]:
        """Get information about the current certificate.
        
        Returns:
            Dict with certificate information
        """
        if self._cert_info is None:
            # Read certificate
            with open(self.cert_path, "r") as f:
                cert_pem = f.read()
                
            # Extract certificate info
            self._cert_info = extract_certificate_info(cert_pem)
            
        return self._cert_info
