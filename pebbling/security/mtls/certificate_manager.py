"""
Certificate manager for handling mTLS certificate lifecycle.

This module provides a facade that integrates the specialized certificate
management components for a unified interface to mTLS certificate operations.
"""

import os
import ssl
import logging
import datetime
from typing import Dict, Any, Optional, Tuple

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.sheldon_client import SheldonCAClient
from pebbling.security.mtls.token_manager import TokenManager
from pebbling.security.config import (
    DEFAULT_CERT_DIRECTORY,
    DEFAULT_TOKEN_VALIDITY,
    DEFAULT_CERTIFICATE_VALIDITY
)

# Import the specialized managers
from pebbling.security.mtls.cert_lifecycle import CertLifecycleManager
from pebbling.security.mtls.cert_verification import CertVerificationManager
from pebbling.security.mtls.ssl_context import SSLContextManager
from pebbling.security.mtls.cert_renewal import CertRenewalManager

logger = logging.getLogger(__name__)


class CertificateManager:
    """Facade for the certificate management subsystem.
    
    This class integrates the specialized certificate managers:
    1. CertLifecycleManager - For certificate lifecycle operations
    2. CertVerificationManager - For certificate verification operations
    3. SSLContextManager - For SSL context creation
    4. CertRenewalManager - For automatic certificate renewal
    """
    
    def __init__(
        self,
        did_manager: DIDManager,
        sheldon_ca_url: str,
        cert_dir: str = DEFAULT_CERT_DIRECTORY,
        auto_renewal: bool = True,
        token_validity: datetime.timedelta = DEFAULT_TOKEN_VALIDITY
    ):
        """Initialize the certificate manager.
        
        Args:
            did_manager: DID manager for identity operations
            sheldon_ca_url: URL of the Sheldon CA service
            cert_dir: Directory for storing certificates and keys
            auto_renewal: Whether to automatically renew certificates
            token_validity: Validity period for verification tokens
        """
        self.did_manager = did_manager
        self.cert_dir = cert_dir
        self.ca_client = SheldonCAClient(sheldon_ca_url)
        self.auto_renewal = auto_renewal
        
        # Create certificate directory if it doesn't exist
        os.makedirs(self.cert_dir, exist_ok=True)
        
        # File paths
        self.did = did_manager.did
        self.cert_path = os.path.join(self.cert_dir, f"{self.did}.crt")
        self.key_path = os.path.join(self.cert_dir, f"{self.did}.key")
        self.ca_cert_path = os.path.join(self.cert_dir, "ca.crt")
        self.token_file = os.path.join(self.cert_dir, "tokens.json")
        
        # Initialize token manager
        self.token_manager = TokenManager(
            token_file=self.token_file,
            token_validity=token_validity
        )
        
        # Initialize specialized managers
        self.lifecycle_manager = CertLifecycleManager(
            did_manager=self.did_manager,
            ca_client=self.ca_client,
            cert_dir=self.cert_dir
        )
        
        self.verification_manager = CertVerificationManager(
            ca_client=self.ca_client,
            token_manager=self.token_manager,
            cert_dir=self.cert_dir
        )
        
        self.ssl_manager = SSLContextManager(
            cert_path=self.cert_path,
            key_path=self.key_path,
            ca_cert_path=self.ca_cert_path
        )
        
        self.renewal_manager = CertRenewalManager(
            lifecycle_manager=self.lifecycle_manager,
            verification_manager=self.verification_manager,
            auto_renewal=self.auto_renewal
        )
        
        # Cache for certificate information
        self._cert_info = None
        self._cert_fingerprint = None
        
    async def initialize(self) -> None:
        """Initialize the certificate manager.
        
        This method:
        1. Gets the CA certificate
        2. Requests a certificate if needed
        3. Verifies the certificate with the CA
        
        Returns:
            None
        """
        try:
            # Get CA certificate first
            await self.lifecycle_manager.ensure_ca_certificate()
            
            # Check if we need a certificate
            if not self.lifecycle_manager.has_valid_certificate():
                await self.lifecycle_manager.request_certificate()
            
            # Verify our certificate with the CA
            await self.verification_manager.verify_certificate(self.cert_path)
            
            # Start renewal task if enabled
            if self.auto_renewal:
                await self.renewal_manager.start_renewal_task()
            
            logger.info(f"Certificate manager initialized for DID: {self.did}")
            
        except Exception as e:
            error_msg = f"Failed to initialize certificate manager: {str(e)}"
            logger.error(error_msg)
            raise
            
    # --- Delegate methods for lifecycle operations ---
    
    def _has_valid_certificate(self) -> bool:
        """Check if we have a valid certificate."""
        return self.lifecycle_manager.has_valid_certificate()
        
    async def request_certificate(self) -> Dict[str, Any]:
        """Request a certificate from the Sheldon CA."""
        result = await self.lifecycle_manager.request_certificate()
        self._cert_info = result  # Update cache
        self._cert_fingerprint = result["fingerprint"] if "fingerprint" in result else None
        return result
    
    # --- Delegate methods for verification operations ---
    
    async def verify_certificate(self, certificate_path: Optional[str] = None) -> Dict[str, Any]:
        """Verify a certificate with the Sheldon CA."""
        cert_path = certificate_path or self.cert_path
        return await self.verification_manager.verify_certificate(cert_path)
            
    async def validate_peer_certificate(self, peer_certificate: str, peer_did: str) -> bool:
        """Validate a peer's certificate."""
        return await self.verification_manager.validate_peer_certificate(
            peer_certificate, 
            peer_did
        )
    
    # --- Delegate methods for SSL context operations ---
    
    def create_ssl_context(self, server_side: bool = False) -> ssl.SSLContext:
        """Create an SSL context for mTLS connections."""
        return self.ssl_manager.create_ssl_context(server_side)
    
    # --- Delegate methods for certificate information ---
    
    def get_certificate_info(self) -> Dict[str, Any]:
        """Get information about the current certificate."""
        if self._cert_info is None:
            self._cert_info = self.lifecycle_manager.get_certificate_info()
            self._cert_fingerprint = self._cert_info["fingerprint"]
        return self._cert_info
        
    def get_fingerprint(self) -> str:
        """Get the fingerprint of the current certificate."""
        if self._cert_fingerprint is None:
            self.get_certificate_info()  # This will set self._cert_fingerprint
        return self._cert_fingerprint