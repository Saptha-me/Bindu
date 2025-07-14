"""
DID Exchange handlers for Pebbling security middleware.

This module provides handlers for DID document exchange between agents.
"""

import logging
from typing import Dict, Any, Optional

from aiohttp import web

from pebbling.security.did_manager import DIDManager
from pebbling.security.mtls.certificate_manager import CertificateManager

logger = logging.getLogger(__name__)


class DIDExchangeHandler:
    """Handles DID document exchange between agents."""
    
    def __init__(
        self,
        did_manager: DIDManager,
        certificate_manager: Optional[CertificateManager] = None,
        did_documents_cache: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """Initialize the DID exchange handler.
        
        Args:
            did_manager: DID manager for identity operations
            certificate_manager: Certificate manager for mTLS, or None if not using mTLS
            did_documents_cache: Optional shared cache for DID documents
        """
        self.did_manager = did_manager
        self.certificate_manager = certificate_manager
        self.did_documents_cache = did_documents_cache if did_documents_cache is not None else {}
        
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
    
    def get_peer_did_document(self, peer_did: str) -> Optional[Dict[str, Any]]:
        """Get a peer's DID document from cache.
        
        Args:
            peer_did: The DID of the peer
            
        Returns:
            The DID document if available, None otherwise
        """
        # Check if we have it in cache
        if peer_did in self.did_documents_cache:
            return self.did_documents_cache[peer_did]
            
        # We don't have it
        logger.warning(f"No DID document available for {peer_did}. Exchange DIDs first.")
        return None
