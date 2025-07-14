"""
Utility functions for mTLS operations.

This module provides common utility functions used across the mTLS
implementation, such as SSL context creation, certificate fingerprinting,
and other helper functions.
"""

import ssl
import hashlib
import logging
from typing import Optional, Dict, Any, List
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from pebbling.security.config import DEFAULT_TLS_VERSION, DEFAULT_CIPHER_SUITES
from pebbling.security.mtls.exceptions import SSLContextError

logger = logging.getLogger(__name__)


def create_ssl_context(
    cert_path: str, 
    key_path: str, 
    ca_cert_path: str, 
    server_side: bool = False,
    tls_version: str = DEFAULT_TLS_VERSION,
    cipher_suites: Optional[List[str]] = None
) -> ssl.SSLContext:
    """Create an SSL context for mTLS.
    
    Args:
        cert_path: Path to the certificate file
        key_path: Path to the private key file
        ca_cert_path: Path to the CA certificate file
        server_side: Whether this is for a server (True) or client (False)
        tls_version: TLS version to use
        cipher_suites: List of cipher suites to enable
        
    Returns:
        Configured SSL context
        
    Raises:
        SSLContextError: If creating the SSL context fails
    """
    try:
        # Set purpose based on whether we're server or client
        purpose = ssl.Purpose.SERVER_AUTH if not server_side else ssl.Purpose.CLIENT_AUTH
        
        # Create the SSL context with appropriate protocol version
        if tls_version == "TLSv1.3" and hasattr(ssl, "TLSVersion"):
            context = ssl.create_default_context(purpose=purpose)
            context.minimum_version = ssl.TLSVersion.TLSv1_3
        else:
            # Fallback if TLSv1.3 is not available
            context = ssl.create_default_context(purpose=purpose)
            
        # Load CA certificate to verify peers
        context.load_verify_locations(ca_cert_path)
        
        # Load our certificate and key
        context.load_cert_chain(cert_path, key_path)
        
        # Set verification mode
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Enable post-handshake authentication for TLS 1.3
        if hasattr(ssl, "POST_HANDSHAKE_AUTH"):  # Python 3.8+
            context.post_handshake_auth = True
            
        # Set preferred cipher suites if specified
        if cipher_suites:
            try:
                context.set_ciphers(":".join(cipher_suites))
            except ssl.SSLError:
                logger.warning("Failed to set custom cipher suites, using defaults")
        elif DEFAULT_CIPHER_SUITES:
            try:
                context.set_ciphers(":".join(DEFAULT_CIPHER_SUITES))
            except ssl.SSLError:
                logger.warning("Failed to set default cipher suites, using system defaults")
                
        # Additional security options
        if hasattr(context, "options"):
            # Disable outdated protocols
            context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            # Disable compression to prevent CRIME attack
            context.options |= ssl.OP_NO_COMPRESSION
            
        return context
        
    except Exception as e:
        error_msg = f"Error creating SSL context: {str(e)}"
        logger.error(error_msg)
        raise SSLContextError(error_msg) from e


def get_certificate_fingerprint(cert_pem: str) -> str:
    """Calculate the SHA-256 fingerprint of a certificate.
    
    Args:
        cert_pem: PEM-encoded certificate
        
    Returns:
        SHA-256 fingerprint of the certificate as a hex string
        
    Raises:
        ValueError: If the certificate is invalid
    """
    try:
        # Load certificate from PEM string
        cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
        
        # Calculate SHA-256 fingerprint
        fingerprint = cert.fingerprint(hashes.SHA256())
        
        # Convert to hex string
        return fingerprint.hex()
        
    except Exception as e:
        error_msg = f"Error calculating certificate fingerprint: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def extract_certificate_info(cert_pem: str) -> Dict[str, Any]:
    """Extract information from a certificate.
    
    Args:
        cert_pem: PEM-encoded certificate
        
    Returns:
        Dict with certificate information
        
    Raises:
        ValueError: If the certificate is invalid
    """
    try:
        # Load certificate from PEM string
        cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
        
        # Extract subject information
        subject = cert.subject
        issuer = cert.issuer
        
        # Extract common name from subject
        common_name = None
        for attr in subject.get_attributes_for_oid(NameOID.COMMON_NAME):
            common_name = attr.value
            break
            
        # Extract validity period
        not_valid_before = cert.not_valid_before
        not_valid_after = cert.not_valid_after
        
        # Calculate fingerprint
        fingerprint = get_certificate_fingerprint(cert_pem)
        
        # Get serial number
        serial_number = cert.serial_number
        
        return {
            "subject": {
                "common_name": common_name,
                # Add other subject attributes as needed
            },
            "issuer": {
                "common_name": next((attr.value for attr in issuer.get_attributes_for_oid(NameOID.COMMON_NAME)), None),
                # Add other issuer attributes as needed
            },
            "validity": {
                "not_before": not_valid_before.isoformat(),
                "not_after": not_valid_after.isoformat(),
            },
            "fingerprint": fingerprint,
            "serial_number": str(serial_number)
        }
        
    except Exception as e:
        error_msg = f"Error extracting certificate information: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def verify_certificate_did_binding(cert_pem: str, did: str) -> bool:
    """Verify that a certificate is bound to a specific DID.
    
    Args:
        cert_pem: PEM-encoded certificate
        did: DID to verify against
        
    Returns:
        True if the certificate is bound to the DID, False otherwise
    """
    try:
        # Extract certificate info
        cert_info = extract_certificate_info(cert_pem)
        
        # Check if DID is in subject common name
        if cert_info["subject"]["common_name"] == did:
            return True
            
        # TODO: Add additional checks based on how DIDs are embedded in certificates
        # For example, check Subject Alternative Name extensions
        
        return False
        
    except Exception as e:
        logger.error(f"Error verifying certificate-DID binding: {str(e)}")
        return False
