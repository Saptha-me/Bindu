"""
Certificate handlers for Pebbling security middleware.

This module provides handlers for certificate-related operations,
including certificate status and verification.
"""

import time
import logging
from typing import Dict, Any, Optional

from aiohttp import web

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.certificate_manager import CertificateManager

logger = logging.getLogger(__name__)


class CertificateHandler:
    """Handles certificate-related operations."""
    
    def __init__(
        self,
        did_manager: DIDManager,
        certificate_manager: CertificateManager
    ):
        """Initialize the certificate handler.
        
        Args:
            did_manager: DID manager for identity operations
            certificate_manager: Certificate manager for mTLS operations
        """
        self.did_manager = did_manager
        self.certificate_manager = certificate_manager
        
    async def handle_certificate_status(self, request: web.Request) -> web.Response:
        """Handle certificate status request.
        
        This endpoint allows agents to check the status of their certificate
        and verification token.
        
        Args:
            request: aiohttp request
            
        Returns:
            Response with certificate and token status
        """
        try:
            if not self.certificate_manager:
                return web.json_response(
                    {"error": "mTLS not configured"},
                    status=400
                )
                
            # Get certificate information
            cert_info = self.certificate_manager.get_certificate_info()
            fingerprint = cert_info["fingerprint"]
            
            # Check token status
            token_valid = False
            token_expires_in = 0
            
            try:
                token, is_expiring_soon = self.certificate_manager.token_manager.get_token(fingerprint)
                token_valid = True
                
                # Calculate remaining time
                token_data = self.certificate_manager.token_manager.tokens[fingerprint]
                token_expires_in = max(0, token_data["expires_at"] - time.time())
                
            except Exception:
                pass
                
            # Prepare response
            response = {
                "certificate": {
                    "fingerprint": fingerprint,
                    "subject": cert_info["subject"],
                    "issuer": cert_info["issuer"],
                    "validity": cert_info["validity"],
                    "did": self.did_manager.did
                },
                "token_status": {
                    "valid": token_valid,
                    "expires_in_seconds": token_expires_in
                }
            }
            
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"Error getting certificate status: {str(e)}")
            return web.json_response(
                {"error": f"Failed to get certificate status: {str(e)}"},
                status=500
            )
    
    async def handle_verify_connection(self, request: web.Request) -> web.Response:
        """Handle connection verification.
        
        This endpoint allows agents to verify their mTLS connection.
        
        Args:
            request: aiohttp request
            
        Returns:
            Response indicating whether the connection is verified
        """
        try:
            if not self.certificate_manager:
                return web.json_response(
                    {"error": "mTLS not configured"},
                    status=400
                )
                
            # For this endpoint, we rely on the mTLS middleware to extract the client
            # certificate and verify it. If the request gets here, it means the certificate
            # was valid. We just need to return the verification result.
            
            # Get peer DID from request header or query parameter
            peer_did = request.headers.get("X-DID") or request.query.get("did")
            
            if not peer_did:
                return web.json_response(
                    {"error": "Missing DID in request"},
                    status=400
                )
                
            # Return connection verification result
            return web.json_response({
                "verified": True,
                "did": peer_did,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"Error verifying connection: {str(e)}")
            return web.json_response(
                {"error": f"Connection verification failed: {str(e)}"},
                status=500
            )
