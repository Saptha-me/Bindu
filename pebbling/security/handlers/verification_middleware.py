"""
Security verification middleware for Pebbling framework.

This module provides middleware for verifying security credentials
in requests, including DID verification and mTLS certificate validation.
"""

import time
import logging
import ssl
from typing import Dict, Any, Callable, Optional

from aiohttp import web
from aiohttp.web import middleware
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from pebbling.security.config import SECURITY_ENDPOINTS

logger = logging.getLogger(__name__)


class VerificationMiddleware:
    """Middleware for verifying security credentials."""
    
    def __init__(
        self,
        challenge_response_handler,
        certificate_manager=None
    ):
        """Initialize the verification middleware.
        
        Args:
            challenge_response_handler: Handler for challenge-response verification
            certificate_manager: Certificate manager for mTLS, or None if not using mTLS
        """
        self.challenge_response_handler = challenge_response_handler
        self.certificate_manager = certificate_manager
        
    @middleware
    async def verify_security(self, request: web.Request, handler: Callable) -> web.Response:
        """Verify that the request has valid security credentials.
        
        This middleware:
        1. Skips verification for security endpoints
        2. Verifies DID authorization header
        3. Verifies mTLS connection (if configured)
        4. Verifies connection is authenticated via challenge-response
        
        Args:
            request: aiohttp request
            handler: Next handler in the middleware chain
            
        Returns:
            Response from the handler if verification passes
            
        Raises:
            web.HTTPUnauthorized: If verification fails
        """
        # Skip verification for security endpoints
        path = request.path
        if any(path.startswith(endpoint) for endpoint in SECURITY_ENDPOINTS):
            return await handler(request)
            
        # Get DID from authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("DID "):
            logger.warning("Missing or invalid Authorization header")
            return web.json_response(
                {"error": "Missing or invalid Authorization header"},
                status=401
            )
            
        did = auth_header[4:]  # Remove "DID " prefix
        
        # Check if connection is verified via challenge-response
        if not self.challenge_response_handler.is_connection_verified(did):
            logger.warning(f"Connection not verified for DID: {did}")
            return web.json_response(
                {"error": "Connection not verified. Please authenticate first."},
                status=401
            )
            
        # If using mTLS, verify the certificate
        if self.certificate_manager:
            # Get peer certificate from SSL context
            try:
                # Extract peer certificate from the connection
                transport = request.transport
                if not transport:
                    logger.error("No transport in request")
                    return web.json_response(
                        {"error": "No transport in request"},
                        status=500
                    )
                    
                ssl_object = transport.get_extra_info("ssl_object")
                if not ssl_object:
                    logger.error("No SSL object in transport")
                    return web.json_response(
                        {"error": "No SSL connection"},
                        status=401
                    )
                    
                # Get certificate in DER format
                peer_cert_bin = ssl_object.getpeercert(binary_form=True)
                if not peer_cert_bin:
                    logger.error("No peer certificate")
                    return web.json_response(
                        {"error": "No client certificate provided"},
                        status=401
                    )
                    
                # Convert DER to PEM format
                cert = load_der_x509_certificate(peer_cert_bin, default_backend())
                pem_data = cert.public_bytes(encoding=Encoding.PEM)
                peer_cert_pem = pem_data.decode('ascii')
                
                # Validate certificate against DID
                is_valid = await self.certificate_manager.validate_peer_certificate(peer_cert_pem, did)
                if not is_valid:
                    logger.warning(f"Invalid certificate for DID: {did}")
                    return web.json_response(
                        {"error": "Invalid certificate"},
                        status=401
                    )
                    
            except Exception as e:
                logger.error(f"Error validating certificate: {str(e)}")
                return web.json_response(
                    {"error": f"Certificate validation failed: {str(e)}"},
                    status=401
                )
                
        # All security checks passed
        return await handler(request)
