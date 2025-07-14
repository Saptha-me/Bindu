"""
Security middleware for Pebbling framework.

This module provides a facade that integrates specialized security handlers
for DID exchange, certificate operations, and challenge-response authentication,
creating a comprehensive security middleware for the Pebbling framework.
"""

import logging
from typing import Dict, Any, Callable, Optional, List

from aiohttp import web

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.security.config import (
    SECURITY_ENDPOINTS,
    DEFAULT_CHALLENGE_TIMEOUT_SECONDS
)

# Import specialized handlers
from pebbling.security.handlers.did_exchange import DIDExchangeHandler
from pebbling.security.handlers.challenge_response import ChallengeResponseHandler
from pebbling.security.handlers.certificate_handlers import CertificateHandler
from pebbling.security.handlers.verification_middleware import VerificationMiddleware

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Facade for the security middleware components.
    
    This class integrates specialized security handlers:
    1. DIDExchangeHandler - For DID document exchange
    2. ChallengeResponseHandler - For challenge-response authentication
    3. CertificateHandler - For certificate operations
    4. VerificationMiddleware - For request security verification
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
        
        # DID documents cache - shared between handlers
        self.did_documents_cache: Dict[str, Dict[str, Any]] = {}
        
        # Initialize specialized handlers
        self.did_exchange_handler = DIDExchangeHandler(
            did_manager=did_manager,
            certificate_manager=certificate_manager,
            did_documents_cache=self.did_documents_cache
        )
        
        self.challenge_response_handler = ChallengeResponseHandler(
            did_manager=did_manager,
            challenge_timeout=challenge_timeout,
            did_exchange_handler=self.did_exchange_handler
        )
        
        if certificate_manager:
            self.certificate_handler = CertificateHandler(
                did_manager=did_manager,
                certificate_manager=certificate_manager
            )
        else:
            self.certificate_handler = None
            
        self.verification_middleware = VerificationMiddleware(
            challenge_response_handler=self.challenge_response_handler,
            certificate_manager=certificate_manager
        )
        
    def setup_routes(self, app: web.Application) -> None:
        """Set up security-related routes in the application.
        
        Args:
            app: aiohttp web application
        """
        # DID exchange route
        app.router.add_post("/security/did_exchange", self.did_exchange_handler.handle_did_exchange)
        
        # Challenge-response routes
        app.router.add_post("/security/challenge", self.challenge_response_handler.handle_challenge)
        app.router.add_post("/security/challenge_response", self.challenge_response_handler.handle_challenge_response)
        
        # Certificate routes (if using mTLS)
        if self.certificate_handler:
            app.router.add_get("/security/certificate/status", self.certificate_handler.handle_certificate_status)
            app.router.add_get("/security/verify_connection", self.certificate_handler.handle_verify_connection)
            
        # Add security verification middleware
        app.middlewares.append(self.verification_middleware.verify_security)
        
    # --- Delegate methods for backward compatibility ---
    
    async def verify_security(self, request: web.Request, handler: Callable) -> web.Response:
        """Verify that the request has valid security credentials."""
        return await self.verification_middleware.verify_security(request, handler)
        
    async def handle_did_exchange(self, request: web.Request) -> web.Response:
        """Handle DID exchange between agents."""
        return await self.did_exchange_handler.handle_did_exchange(request)
        
    async def handle_challenge(self, request: web.Request) -> web.Response:
        """Handle challenge request for authentication."""
        return await self.challenge_response_handler.handle_challenge(request)
        
    async def handle_challenge_response(self, request: web.Request) -> web.Response:
        """Handle challenge-response for authentication."""
        return await self.challenge_response_handler.handle_challenge_response(request)
        
    async def handle_certificate_status(self, request: web.Request) -> web.Response:
        """Handle certificate status request."""
        if self.certificate_handler:
            return await self.certificate_handler.handle_certificate_status(request)
        return web.json_response({"error": "mTLS not configured"}, status=400)
        
    async def handle_verify_connection(self, request: web.Request) -> web.Response:
        """Handle connection verification."""
        if self.certificate_handler:
            return await self.certificate_handler.handle_verify_connection(request)
        return web.json_response({"error": "mTLS not configured"}, status=400)
        
    async def _get_peer_did_document(self, peer_did: str) -> Optional[Dict[str, Any]]:
        """Get a peer's DID document from cache."""
        return self.did_exchange_handler.get_peer_did_document(peer_did)