"""
Challenge-response handlers for Pebbling security middleware.

This module provides handlers for challenge-response authentication
between agents using cryptographic signatures.
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional

from aiohttp import web

from pebbling.security.did_manager import DIDManager
from pebbling.security.config import DEFAULT_CHALLENGE_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class ChallengeResponseHandler:
    """Handles challenge-response authentication between agents."""
    
    def __init__(
        self,
        did_manager: DIDManager,
        challenge_timeout: int = DEFAULT_CHALLENGE_TIMEOUT_SECONDS,
        did_exchange_handler=None
    ):
        """Initialize the challenge-response handler.
        
        Args:
            did_manager: DID manager for identity operations
            challenge_timeout: Timeout for challenge-response authentication in seconds
            did_exchange_handler: Handler for DID exchange operations (for document lookups)
        """
        self.did_manager = did_manager
        self.challenge_timeout = challenge_timeout
        self.did_exchange_handler = did_exchange_handler
        
        # Active challenges storage: {challenge_id: {"challenge": str, "expires": timestamp}}
        self.challenges: Dict[str, Dict[str, Any]] = {}
        
        # Verified connections storage: {did: {"verified": bool, "last_verified": timestamp}}
        self.verified_connections: Dict[str, Dict[str, Any]] = {}
        
    def _clean_expired_challenges(self) -> None:
        """Clean up expired challenges."""
        current_time = time.time()
        expired_challenges = [
            challenge_id for challenge_id, challenge in self.challenges.items()
            if challenge["expires"] < current_time
        ]
        
        for challenge_id in expired_challenges:
            del self.challenges[challenge_id]
            
    async def handle_challenge(self, request: web.Request) -> web.Response:
        """Handle challenge request for authentication.
        
        This endpoint allows agents to request a challenge for authentication.
        
        Args:
            request: aiohttp request with agent DID
            
        Returns:
            Response with a challenge string
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
                
            # Extract peer DID
            peer_did = data["did"]
            
            # Clean expired challenges
            self._clean_expired_challenges()
            
            # Generate a new challenge
            challenge_id = str(uuid.uuid4())
            challenge_text = f"auth-challenge-{challenge_id}-{time.time()}"
            expires = time.time() + self.challenge_timeout
            
            # Store the challenge
            self.challenges[challenge_id] = {
                "challenge": challenge_text,
                "expires": expires,
                "peer_did": peer_did
            }
            
            # Prepare response
            response_data = {
                "challenge_id": challenge_id,
                "challenge": challenge_text,
                "expires": expires
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Error generating challenge: {str(e)}")
            return web.json_response(
                {"error": f"Challenge generation failed: {str(e)}"},
                status=500
            )
            
    async def handle_challenge_response(self, request: web.Request) -> web.Response:
        """Handle challenge-response for authentication.
        
        This endpoint allows agents to respond to a challenge with a signature
        to authenticate themselves.
        
        Args:
            request: aiohttp request with challenge_id and signature
            
        Returns:
            Response indicating whether authentication was successful
        """
        try:
            # Parse request body
            data = await request.json()
            
            # Validate request data
            required_fields = ["challenge_id", "signature", "did"]
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": f"Missing required field: {field}"},
                        status=400
                    )
                    
            challenge_id = data["challenge_id"]
            signature = data["signature"]
            peer_did = data["did"]
            
            # Check if we have this challenge
            if challenge_id not in self.challenges:
                return web.json_response(
                    {"error": "Challenge not found or expired"},
                    status=400
                )
                
            # Get the challenge data
            challenge = self.challenges[challenge_id]
            
            # Check if challenge is expired
            if challenge["expires"] < time.time():
                del self.challenges[challenge_id]
                return web.json_response(
                    {"error": "Challenge expired"},
                    status=401
                )
                
            # Check if challenge was issued for this DID
            if challenge["peer_did"] != peer_did:
                return web.json_response(
                    {"error": "Challenge was not issued for this DID"},
                    status=401
                )
                
            # Verify signature using the DID document's verification method
            logger.info(f"Verifying signature from {peer_did} for challenge {challenge_id}")
            
            try:
                # Get the peer's DID document (should be available from DID exchange)
                # If we don't have it yet, request it
                peer_did_document = None
                if self.did_exchange_handler:
                    peer_did_document = self.did_exchange_handler.get_peer_did_document(peer_did)
                
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
                
            # Authentication successful, mark connection as verified
            current_time = time.time()
            self.verified_connections[peer_did] = {
                "verified": True,
                "last_verified": current_time
            }
            
            # Clean up the challenge
            del self.challenges[challenge_id]
            
            return web.json_response({
                "authenticated": True,
                "did": peer_did,
                "timestamp": current_time
            })
            
        except Exception as e:
            logger.error(f"Error handling challenge response: {str(e)}")
            return web.json_response(
                {"error": f"Challenge response failed: {str(e)}"},
                status=500
            )
    
    def is_connection_verified(self, peer_did: str, max_age: Optional[float] = None) -> bool:
        """Check if a connection with a peer is verified.
        
        Args:
            peer_did: The DID of the peer
            max_age: Maximum age of the verification in seconds (optional)
            
        Returns:
            True if the connection is verified and not expired, False otherwise
        """
        if peer_did not in self.verified_connections:
            return False
            
        connection = self.verified_connections[peer_did]
        
        # Check if connection is verified
        if not connection.get("verified", False):
            return False
            
        # Check if verification has expired (if max_age is specified)
        if max_age is not None:
            last_verified = connection.get("last_verified", 0)
            if time.time() - last_verified > max_age:
                return False
                
        return True
