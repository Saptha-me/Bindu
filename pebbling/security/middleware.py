"""
Security middleware for Pebbling framework.

This module provides middleware for handling security-related routes and
authentication, including DID exchange, certificate verification, and
challenge-response authentication with mTLS support.
"""

import time
import uuid
import logging
import json
from typing import Dict, Any, Callable, Optional, List, Tuple
from datetime import datetime, timedelta

from aiohttp import web
from aiohttp.web import middleware

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.security.config import (
    SECURITY_ENDPOINTS,
    DEFAULT_CHALLENGE_TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Middleware for handling security-related routes and authentication.
    
    This middleware provides:
    1. DID exchange between agents
    2. Certificate verification for mTLS
    3. Challenge-response authentication
    4. Connection verification
    """
    
    def __init__(
        self,
        did_manager: DIDManager,
        certificate_manager: Optional[CertificateManager] = None,
        challenge_timeout: int = DEFAULT_CHALLENGE_TIMEOUT_SECONDS
    ):
        """Initialize the security middleware.
        
        Args:
            did_manager: DID manager for identity operations
            certificate_manager: Certificate manager for mTLS, or None if not using mTLS
            challenge_timeout: Timeout for challenge-response authentication in seconds
        """
        self.did_manager = did_manager
        self.certificate_manager = certificate_manager
        self.challenge_timeout = challenge_timeout
        
        # Active challenges storage: {challenge_id: {"challenge": str, "expires": timestamp}}
        self.challenges: Dict[str, Dict[str, Any]] = {}
        
        # Verified connections storage: {did: {"verified": bool, "last_verified": timestamp}}
        self.verified_connections: Dict[str, Dict[str, Any]] = {}
        
        # DID document cache: {did: did_document}
        self.did_documents_cache: Dict[str, Dict[str, Any]] = {}
        
    def setup_routes(self, app: web.Application) -> None:
        """Set up security-related routes in the application.
        
        Args:
            app: aiohttp web application
            
        Returns:
            None
        """
        # DID exchange endpoint
        app.router.add_post(
            SECURITY_ENDPOINTS["exchange_did"],
            self.handle_did_exchange
        )
        
        # Verify connection endpoint
        app.router.add_post(
            SECURITY_ENDPOINTS["verify_connection"],
            self.handle_verify_connection
        )
        
        # Challenge-response endpoints
        app.router.add_post(
            SECURITY_ENDPOINTS["challenge"],
            self.handle_challenge_request
        )
        app.router.add_post(
            SECURITY_ENDPOINTS["challenge_response"],
            self.handle_challenge_response
        )
        
        # Certificate status endpoint (if using mTLS)
        if self.certificate_manager:
            app.router.add_get(
                SECURITY_ENDPOINTS["certificate_status"],
                self.handle_certificate_status
            )
            
        logger.info("Security middleware routes set up")
        
    @middleware
    async def verify_security(
        self,
        request: web.Request,
        handler: Callable
    ) -> web.Response:
        """Middleware for verifying security requirements.
        
        This middleware:
        1. Checks if the route requires security verification
        2. Verifies the DID and certificate (if using mTLS)
        3. Allows the request if verification passes
        
        Args:
            request: aiohttp request
            handler: Request handler function
            
        Returns:
            Handler response if verification passes, error response otherwise
        """
        # Skip verification for security endpoints
        path = request.path
        if any(path.endswith(endpoint) for endpoint in SECURITY_ENDPOINTS.values()):
            return await handler(request)
            
        # Check if the request has authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return web.json_response(
                {"error": "Missing authorization header"},
                status=401
            )
            
        try:
            # Parse authorization header
            auth_parts = auth_header.split()
            if len(auth_parts) != 2 or auth_parts[0] != "DID":
                return web.json_response(
                    {"error": "Invalid authorization header format"},
                    status=401
                )
                
            # Get the DID from the header
            did = auth_parts[1]
            
            # Check if connection is verified
            if did not in self.verified_connections or not self.verified_connections[did].get("verified", False):
                return web.json_response(
                    {"error": "Connection not verified"},
                    status=401
                )
                
            # Check if verification is expired (24 hours)
            last_verified = self.verified_connections[did].get("last_verified", 0)
            if time.time() - last_verified > 86400:  # 24 hours
                # Clear the verification
                self.verified_connections[did]["verified"] = False
                return web.json_response(
                    {"error": "Connection verification expired"},
                    status=401
                )
                
            # Verify mTLS certificate binding if applicable
            if self.certificate_manager and request.transport:
                # Check if we can access the TLS connection
                ssl_object = request.transport.get_extra_info("ssl_object")
                if ssl_object:
                    # Get peer certificate
                    peer_cert_bin = ssl_object.getpeercert(binary_form=True)
                    if not peer_cert_bin:
                        return web.json_response(
                            {"error": "No peer certificate provided"},
                            status=401
                        )
                        
                    # Properly convert DER format to PEM format using cryptography library
                    try:
                        from cryptography.x509 import load_der_x509_certificate
                        from cryptography.hazmat.backends import default_backend
                        from cryptography.hazmat.primitives import serialization
                        
                        cert = load_der_x509_certificate(peer_cert_bin, default_backend())
                        pem_data = cert.public_bytes(encoding=serialization.Encoding.PEM)
                        peer_cert_pem = pem_data.decode('ascii')
                        
                        logger.debug(f"Successfully converted peer certificate from DER to PEM")
                    except Exception as e:
                        logger.error(f"Failed to convert certificate from DER to PEM: {str(e)}")
                        return web.json_response(
                            {"error": "Invalid certificate format"},
                            status=401
                        )
                    
                    # Verify certificate matches the DID
                    try:
                        is_valid = await self.certificate_manager.validate_peer_certificate(
                            peer_cert_pem,
                            did
                        )
                        
                        logger.debug(f"Certificate validation result for {did}: {is_valid}")
                        
                        if not is_valid:
                            logger.warning(f"Certificate validation failed for DID: {did}")
                    except Exception as e:
                        logger.error(f"Certificate validation error: {str(e)}")
                        return web.json_response(
                            {"error": "Certificate validation error"},
                            status=500
                        )
                    
                    if not is_valid:
                        return web.json_response(
                            {"error": "Certificate does not match DID"},
                            status=401
                        )
                        
            # All checks passed, proceed with the request
            return await handler(request)
            
        except Exception as e:
            logger.error(f"Error in security middleware: {str(e)}")
            return web.json_response(
                {"error": "Security verification failed"},
                status=500
            )
            
    async def handle_did_exchange(self, request: web.Request) -> web.Response:
        """Handle DID exchange between agents.
        
        This endpoint allows agents to exchange DID documents and establish
        initial trust.
        
        Args:
            request: aiohttp request with DID document
            
        Returns:
            Response with this agent's DID document
        """
        try:
            # Parse request body
            data = await request.json()
            
            # Validate request data
            if "did_document" not in data:
                return web.json_response(
                    {"error": "Missing DID document"},
                    status=400
                )
                
            # Extract sender DID from the document
            sender_did_document = data["did_document"]
            sender_did = sender_did_document.get("id")
            
            if not sender_did:
                return web.json_response(
                    {"error": "Invalid DID document, missing id field"},
                    status=400
                )
                
            # TODO: Validate the DID document structure and signature
            # This would involve more detailed verification
            
            # Get our DID document
            our_did_document = self.did_manager.get_did_document()
            
            # Store the sender's DID document in our cache for later verification
            self.did_documents_cache[sender_did] = sender_did_document
            logger.info(f"Received and cached DID document from {sender_did}")
            
            # Prepare response with our DID document
            response_data = {
                "did": self.did_manager.did,
                "did_document": our_did_document
            }
            
            # If we're using mTLS, include certificate information
            if self.certificate_manager:
                cert_info = self.certificate_manager.get_certificate_info()
                response_data["certificate_info"] = {
                    "fingerprint": cert_info["fingerprint"],
                    "subject": cert_info["subject"],
                    "validity": cert_info["validity"]
                }
                
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Error handling DID exchange: {str(e)}")
            return web.json_response(
                {"error": f"DID exchange failed: {str(e)}"},
                status=500
            )
            
    async def handle_verify_connection(self, request: web.Request) -> web.Response:
        """Handle connection verification.
        
        This endpoint verifies the connection between agents based on:
        1. DID verification
        2. Certificate verification (if using mTLS)
        
        Args:
            request: aiohttp request with verification data
            
        Returns:
            Response with verification result
        """
        try:
            # Parse request body
            data = await request.json()
            
            # Validate request data
            if "did" not in data:
                return web.json_response(
                    {"error": "Missing DID"},
                    status=400
                )
                
            peer_did = data["did"]
            
            # Verify DID
            # In a real implementation, you would verify that you have previously
            # received a DID document from this DID and validate it
            
            # If we're using mTLS, verify certificate information
            if self.certificate_manager and "certificate" in data:
                peer_certificate = data["certificate"]
                
                # Validate peer certificate
                is_valid = await self.certificate_manager.validate_peer_certificate(
                    peer_certificate,
                    peer_did
                )
                
                if not is_valid:
                    return web.json_response(
                        {"error": "Certificate validation failed"},
                        status=401
                    )
                    
            # Mark connection as verified
            self.verified_connections[peer_did] = {
                "verified": True,
                "last_verified": time.time()
            }
            
            logger.info(f"Connection verified for {peer_did}")
            
            # Return success response
            return web.json_response({
                "verified": True,
                "did": self.did_manager.did,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error verifying connection: {str(e)}")
            return web.json_response(
                {"error": f"Connection verification failed: {str(e)}"},
                status=500
            )
            
    async def handle_challenge_request(self, request: web.Request) -> web.Response:
        """Handle challenge request for challenge-response authentication.
        
        This endpoint generates a random challenge for the requestor to sign,
        which proves ownership of the private key corresponding to their DID.
        
        Args:
            request: aiohttp request with challenge parameters
            
        Returns:
            Response with challenge
        """
        try:
            # Parse request body
            data = await request.json()
            
            # Validate request data
            if "did" not in data:
                return web.json_response(
                    {"error": "Missing DID"},
                    status=400
                )
                
            peer_did = data["did"]
            
            # Generate a random challenge
            challenge_id = str(uuid.uuid4())
            challenge = {
                "id": challenge_id,
                "challenge": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "expires": time.time() + self.challenge_timeout,
                "did": peer_did
            }
            
            # Store the challenge
            self.challenges[challenge_id] = challenge
            
            # Schedule cleanup of expired challenges
            self._clean_expired_challenges()
            
            # Return the challenge
            return web.json_response({
                "challenge_id": challenge_id,
                "challenge": challenge["challenge"],
                "expires_in": self.challenge_timeout
            })
            
        except Exception as e:
            logger.error(f"Error generating challenge: {str(e)}")
            return web.json_response(
                {"error": f"Challenge generation failed: {str(e)}"},
                status=500
            )
            
    async def handle_challenge_response(self, request: web.Request) -> web.Response:
        """Handle challenge response for challenge-response authentication.
        
        This endpoint verifies the signed challenge response, which proves
        ownership of the private key corresponding to the DID.
        
        Args:
            request: aiohttp request with challenge response
            
        Returns:
            Response with verification result
        """
        try:
            # Parse request body
            data = await request.json()
            
            # Validate request data
            required_fields = ["challenge_id", "did", "signature"]
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": f"Missing required field: {field}"},
                        status=400
                    )
                    
            challenge_id = data["challenge_id"]
            peer_did = data["did"]
            signature = data["signature"]
            
            # Check if challenge exists
            if challenge_id not in self.challenges:
                return web.json_response(
                    {"error": "Challenge not found or expired"},
                    status=400
                )
                
            challenge = self.challenges[challenge_id]
            
            # Check if challenge is expired
            if time.time() > challenge["expires"]:
                # Remove expired challenge
                del self.challenges[challenge_id]
                return web.json_response(
                    {"error": "Challenge expired"},
                    status=400
                )
                
            # Check if the DID matches
            if challenge["did"] != peer_did:
                return web.json_response(
                    {"error": "DID mismatch"},
                    status=401
                )
                
            # Verify signature using the DID document's verification method
            logger.info(f"Verifying signature from {peer_did} for challenge {challenge_id}")
            
            try:
                # Get the peer's DID document (should be available from DID exchange)
                # If we don't have it yet, request it
                peer_did_document = await self._get_peer_did_document(peer_did)
                if not peer_did_document:
                    return web.json_response(
                        {"error": "Peer DID document not available. Please exchange DIDs first."},
                        status=400
                    )
                
                # Find the verification method to use
                verification_method = None
                for vm in peer_did_document.get("verificationMethod", []):
                    # Use the first one by default, or preferably one marked for authentication
                    verification_method = vm
                    # If this verification method is in the authentication array, use it
                    auth_methods = peer_did_document.get("authentication", [])
                    if isinstance(auth_methods, list) and (vm["id"] in auth_methods or vm.get("id") in auth_methods):
                        break
                
                if not verification_method:
                    logger.error(f"No verification method found in DID document for {peer_did}")
                    return web.json_response(
                        {"error": "No verification method found in DID document"},
                        status=400
                    )
                    
                # Construct the challenge message exactly as it was presented to the peer
                challenge_message = challenge["challenge"]
                
                # Verify the signature using the DID document's verification method
                is_valid_signature = await self.did_manager.verify_message(
                    challenge_message,
                    signature,
                    verification_method
                )
                
                if is_valid_signature:
                    logger.info(f"Signature verification successful for {peer_did}")
                else:
                    logger.warning(f"Signature verification failed for {peer_did}")
                    
            except Exception as e:
                logger.error(f"Error during signature verification: {str(e)}")
                is_valid_signature = False
            
            if not is_valid_signature:
                return web.json_response(
                    {"error": "Invalid signature"},
                    status=401
                )
                
            # Remove the challenge
            del self.challenges[challenge_id]
            
            # Mark connection as verified
            self.verified_connections[peer_did] = {
                "verified": True,
                "last_verified": time.time()
            }
            
            logger.info(f"Challenge-response verification successful for {peer_did}")
            
            # Return success response
            return web.json_response({
                "verified": True,
                "did": self.did_manager.did,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error verifying challenge response: {str(e)}")
            return web.json_response(
                {"error": f"Challenge verification failed: {str(e)}"},
                status=500
            )
            
    async def handle_certificate_status(self, request: web.Request) -> web.Response:
        """Handle certificate status request.
        
        This endpoint provides information about the agent's certificate
        status, including verification token validity.
        
        Args:
            request: aiohttp request
            
        Returns:
            Response with certificate status
        """
        try:
            # Check if we're using mTLS
            if not self.certificate_manager:
                return web.json_response(
                    {"error": "mTLS not enabled"},
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
            
    async def _get_peer_did_document(self, peer_did: str) -> Optional[Dict[str, Any]]:
        """Get a peer's DID document from cache or attempt to fetch it.
        
        Args:
            peer_did: The DID of the peer
            
        Returns:
            The DID document if available, None otherwise
        """
        # Check if we have it in cache
        if peer_did in self.did_documents_cache:
            return self.did_documents_cache[peer_did]
            
        # We don't have it, so we can't verify
        # In a complete implementation, we would attempt to fetch the DID document
        # from the peer or from a DID resolution service
        logger.warning(f"No DID document available for {peer_did}. Exchange DIDs first.")
        return None
    
    def _clean_expired_challenges(self) -> None:
        """Clean up expired challenges."""
        current_time = time.time()
        expired_challenges = [
            challenge_id for challenge_id, challenge in self.challenges.items()
            if challenge["expires"] < current_time
        ]
        
        for challenge_id in expired_challenges:
            del self.challenges[challenge_id]
            
        if expired_challenges:
            logger.debug(f"Cleaned up {len(expired_challenges)} expired challenges")
            
    def apply(self, app: web.Application) -> None:
        """Apply the middleware to an aiohttp application.
        
        Args:
            app: aiohttp web application
            
        Returns:
            None
        """
        # Set up routes
        self.setup_routes(app)
        
        # Apply middleware
        app.middlewares.append(self.verify_security)
        
        logger.info("Security middleware applied to application")
