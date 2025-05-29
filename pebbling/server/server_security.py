"""Security middleware for pebbling server."""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import uuid
import secrets

from pebbling.security.did_manager import DIDManager

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Security middleware for pebbling server that handles DID-based security."""

    def __init__(
        self, 
        did_manager: DIDManager,
        agent_id: str,
    ):
        """Initialize the security middleware.

        Args:
            did_manager: DID manager for signing and verification
            agent_id: ID of the agent
        """
        self.did_manager = did_manager
        self.agent_id = agent_id
        
        # Store other agents' DID documents for verification
        self.agent_did_documents: Dict[str, Dict[str, Any]] = {}
        
        # Store active verification challenges
        self.challenges: Dict[str, Dict[str, Any]] = {}

    async def register_agent_did(self, agent_id: str, did_document: Dict[str, Any]) -> None:
        """Register another agent's DID document for future verification.

        Args:
            agent_id: ID of the agent
            did_document: DID document of the agent
        """
        if agent_id in self.agent_did_documents:
            logger.info(f"Updating DID document for agent {agent_id}")
        else:
            logger.info(f"Registering new DID document for agent {agent_id}")
            
        self.agent_did_documents[agent_id] = did_document

    async def get_verification_method(self, agent_id: str) -> Optional[str]:
        """Get verification method from an agent's DID document.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Verification method URI or None if not found
        """
        if agent_id not in self.agent_did_documents:
            logger.warning(f"No DID document found for agent {agent_id}")
            return None
            
        did_document = self.agent_did_documents[agent_id]
        if "verificationMethod" not in did_document or not did_document["verificationMethod"]:
            logger.warning(f"No verification methods found in DID document for agent {agent_id}")
            return None
            
        # Use the first verification method by default
        return did_document["verificationMethod"][0]["id"]

    async def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a message using the agent's DID.
        
        Args:
            message: Message to sign
            
        Returns:
            Message with added signature
        """
        # Create a copy to avoid modifying the original
        signed_message = message.copy()
        
        # Sign the message
        signature = await self.did_manager.sign_message(message)
        
        # Add signature and DID information to the message
        signed_message["signature"] = {
            "type": "Ed25519Signature2018",
            "verificationMethod": f"{self.did_manager.get_did()}#keys-1",
            "signature": signature
        }
        
        # Add the agent's DID to the message
        signed_message["did"] = self.did_manager.get_did()
        
        return signed_message

    async def verify_message(self, message: Dict[str, Any]) -> bool:
        """Verify a signed message.
        
        Args:
            message: Signed message to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        if "signature" not in message or "did" not in message:
            logger.warning("Message is missing signature or DID information")
            return False
            
        # Extract signature and DID information
        signature_info = message["signature"]
        sender_did = message["did"]
        
        # Get the sender's agent ID from the message
        sender_id = message.get("source_agent_id")
        if not sender_id:
            logger.warning("Message is missing source_agent_id")
            return False
            
        # Get verification method
        verification_method = signature_info.get("verificationMethod")
        if not verification_method:
            logger.warning("Message signature is missing verification method")
            return False
            
        # Create a copy of the message without the signature for verification
        message_to_verify = message.copy()
        del message_to_verify["signature"]
        
        # Verify the signature
        return await self.did_manager.verify_message(
            message_to_verify,
            signature_info["signature"],
            verification_method
        )

    async def handle_exchange_did(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DID document exchange.
        
        Args:
            params: Request parameters with DID document
            
        Returns:
            Response with this agent's DID document
        """
        # Extract sender information
        sender_id = params.get("source_agent_id")
        sender_did_document = params.get("did_document")
        
        if not sender_id or not sender_did_document:
            return {
                "status": "error",
                "message": "Missing source_agent_id or did_document in request"
            }
            
        # Register the sender's DID document
        await self.register_agent_did(sender_id, sender_did_document)
        
        # Return this agent's DID document
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "did": self.did_manager.get_did(),
            "did_document": self.did_manager.get_did_document()
        }
        
    async def handle_verify_identity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle identity verification request.
        
        This method implements a challenge-response protocol:
        1. If a challenge is provided, sign it and return the signature
        2. If no challenge is provided, generate one for the requester to sign
        
        Args:
            params: Request parameters
            
        Returns:
            Response with challenge or signature
        """
        sender_id = params.get("source_agent_id")
        
        if not sender_id:
            return {
                "status": "error",
                "message": "Missing source_agent_id in request"
            }
            
        # Case 1: Agent is responding to our challenge
        if "signature" in params and "challenge_id" in params:
            challenge_id = params.get("challenge_id")
            signature = params.get("signature")
            
            # Verify the challenge exists
            if challenge_id not in self.challenges:
                return {
                    "status": "error",
                    "message": "Challenge not found or expired"
                }
                
            challenge = self.challenges[challenge_id]
            
            # Verify the challenge belongs to this agent
            if challenge["agent_id"] != sender_id:
                return {
                    "status": "error", 
                    "message": "Challenge was issued to a different agent"
                }
                
            # Verify the signature
            verification_method = await self.get_verification_method(sender_id)
            if not verification_method:
                return {
                    "status": "error",
                    "message": "No verification method found for agent"
                }
                
            is_valid = await self.did_manager.verify_message(
                {"challenge": challenge["challenge"]},
                signature,
                verification_method
            )
            
            # Remove the challenge after verification
            del self.challenges[challenge_id]
            
            if is_valid:
                return {
                    "status": "success",
                    "message": "Identity verified successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Signature verification failed"
                }
        
        # Case 2: Agent is requesting verification (we issue a challenge)
        else:
            # If agent provided their own challenge, use it, otherwise generate one
            challenge = params.get("challenge")
            if not challenge:
                challenge = secrets.token_hex(32)
                
            challenge_id = str(uuid.uuid4())
            
            # Store the challenge
            self.challenges[challenge_id] = {
                "agent_id": sender_id,
                "challenge": challenge,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Sign the challenge with our key
            signature = await self.did_manager.sign_message({"challenge": challenge})
            
            return {
                "status": "success",
                "challenge_id": challenge_id,
                "challenge": challenge,
                "signature": signature,
                "verification_method": f"{self.did_manager.get_did()}#keys-1"
            }

    async def secure_request_handler(
        self, 
        request: Dict[str, Any],
        handler_func: Callable
    ) -> Dict[str, Any]:
        """Process a request through security middleware.
        
        Args:
            request: The JSON-RPC request
            handler_func: The function to handle the request after security checks
            
        Returns:
            The response from the handler
        """
        method = request.get("method")
        params = request.get("params", {})
        
        # Handle security methods directly in security middleware
        if method == "exchange_did":
            return await self.handle_exchange_did(params)
        elif method == "verify_identity":
            return await self.handle_verify_identity(params)
            
        # For other methods, let the protocol handler handle it
        return await handler_func()
