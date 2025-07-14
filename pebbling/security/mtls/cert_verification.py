"""
Certificate verification for mTLS.

This module handles certificate verification operations including
verifying certificates with a CA, managing verification tokens,
and validating peer certificates.
"""

import os
import logging
import datetime
from typing import Dict, Any, Optional, Tuple

from pebbling.security.mtls.sheldon_client import SheldonCAClient
from pebbling.security.mtls.token_manager import TokenManager
from pebbling.security.mtls.utils import (
    get_certificate_fingerprint,
    extract_certificate_info
)
from pebbling.security.mtls.exceptions import (
    CertificateVerificationError,
    TokenError,
    TokenExpiredError
)

logger = logging.getLogger(__name__)


class CertVerificationManager:
    """Manages the verification of mTLS certificates.
    
    This class handles:
    1. Verifying certificates with the CA
    2. Managing verification tokens
    3. Validating peer certificates
    """
    
    def __init__(
        self,
        ca_client: SheldonCAClient,
        token_manager: TokenManager,
        cert_dir: str
    ):
        """Initialize the certificate verification manager.
        
        Args:
            ca_client: Client for communicating with the CA
            token_manager: Manager for verification tokens
            cert_dir: Directory for storing certificates and keys
        """
        self.ca_client = ca_client
        self.token_manager = token_manager
        self.cert_dir = cert_dir
            
    async def verify_certificate(self, certificate_path: str) -> Dict[str, Any]:
        """Verify a certificate with the Sheldon CA.
        
        Args:
            certificate_path: Path to the certificate to verify
                              
        Returns:
            Dict with verification result
            
        Raises:
            CertificateVerificationError: If verification fails
        """
        try:
            # Read certificate
            with open(certificate_path, "r") as f:
                cert_pem = f.read()
                
            # Calculate fingerprint for token management
            fingerprint = get_certificate_fingerprint(cert_pem)
            
            # Check if we have a valid token
            try:
                token, expiring_soon = self.token_manager.get_token(fingerprint)
                
                # If token is valid and not expiring soon, return success
                if not expiring_soon:
                    logger.debug(f"Using cached verification token for {fingerprint}")
                    return {
                        "valid": True,
                        "token": token,
                        "fingerprint": fingerprint
                    }
                    
                # Otherwise, proceed with verification to get a new token
                logger.info(f"Token for {fingerprint} is expiring soon, refreshing")
                
            except (TokenError, TokenExpiredError):
                # No token or expired token, need to verify with CA
                logger.info(f"No valid token for {fingerprint}, verifying with CA")
            
            # Verify with CA
            result = await self.ca_client.verify_certificate(cert_pem)
            
            if not result.get("valid", False):
                error_msg = f"Certificate verification failed: {result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                raise CertificateVerificationError(error_msg)
                
            # Store token
            token = result.get("token")
            if token:
                # Parse token expiration if provided, otherwise use default
                expires_at = None
                if "expires_at" in result:
                    try:
                        expires_at = datetime.datetime.fromisoformat(result["expires_at"])
                    except (ValueError, TypeError):
                        logger.warning("Invalid expires_at format in token, using default validity")
                
                # Store the token
                self.token_manager.store_token(
                    fingerprint,
                    token,
                    expires_at
                )
                
                logger.info(f"Stored verification token for {fingerprint}")
            
            # Add fingerprint to result
            result["fingerprint"] = fingerprint
            
            return result
            
        except CertificateVerificationError:
            # Re-raise verification errors
            raise
        except Exception as e:
            error_msg = f"Error during certificate verification: {str(e)}"
            logger.error(error_msg)
            raise CertificateVerificationError(error_msg) from e
    
    async def validate_peer_certificate(
        self, 
        peer_certificate: str, 
        peer_did: str
    ) -> bool:
        """Validate a peer's certificate.
        
        Args:
            peer_certificate: PEM-encoded certificate of the peer
            peer_did: DID of the peer
            
        Returns:
            True if the certificate is valid for the peer, False otherwise
        """
        try:
            # Extract certificate information
            cert_info = extract_certificate_info(peer_certificate)
            
            # Check if certificate matches the peer's DID
            if cert_info["subject"]["common_name"] != peer_did:
                logger.warning(f"Certificate subject '{cert_info['subject']['common_name']}' "
                             f"does not match peer DID '{peer_did}'")
                return False
                
            # Verify certificate with the CA
            # First save to a temporary file
            temp_cert_path = os.path.join(self.cert_dir, f"temp_{cert_info['fingerprint']}.crt")
            with open(temp_cert_path, "w") as f:
                f.write(peer_certificate)
                
            try:
                # Verify with CA
                result = await self.verify_certificate(temp_cert_path)
                return result.get("valid", False)
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_cert_path):
                    os.remove(temp_cert_path)
                    
        except Exception as e:
            logger.error(f"Error validating peer certificate: {str(e)}")
            return False
