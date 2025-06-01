"""Security middleware for pebbling server."""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, TypedDict
import uuid
import secrets

from loguru import logger
from pebbling.security.did_manager import DIDManager


class ChallengeData(TypedDict):
    """Type definition for challenge data."""
    agent_id: str
    challenge: str
    timestamp: float
    verified: bool


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
        self.challenges: Dict[str, ChallengeData] = {}
        
        logger.debug(f"Initialized SecurityMiddleware for agent {agent_id}")

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
        
        try:    
            self.agent_did_documents[agent_id] = did_document
            logger.debug(f"Successfully registered DID document for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to register DID document for agent {agent_id}: {e}")

    def is_agent_verified(self, agent_id: str) -> bool:
        """Check if an agent has completed the verification process.
        
        Args:
            agent_id: ID of the agent to check
            
        Returns:
            True if agent is verified, False otherwise
        """
        # Agent must have a registered DID document
        if agent_id not in self.agent_did_documents:
            logger.debug(f"Agent {agent_id} not verified: No DID document registered")
            return False
        
        # Agent must have completed a successful challenge verification
        # Look for completed challenges for this agent
        for challenge_id, challenge in self.challenges.items():
            if challenge.get("agent_id") == agent_id and challenge.get("verified", False):
                logger.debug(f"Agent {agent_id} verified with challenge {challenge_id}")
                return True
        
        logger.debug(f"Agent {agent_id} not verified: No successful challenge found")
        return False

    async def get_verification_method(self, agent_id: str) -> Optional[str]:
        """Get verification method from an agent's DID document.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Verification method URI or None if not found
        """
        try:
            if agent_id not in self.agent_did_documents:
                logger.warning(f"No DID document found for agent {agent_id}")
                return None
                
            did_document = self.agent_did_documents[agent_id]
            if "verificationMethod" not in did_document or not did_document["verificationMethod"]:
                logger.warning(f"No verification methods found in DID document for agent {agent_id}")
                return None
                
            # Use the first verification method by default
            method_id = did_document["verificationMethod"][0]["id"]
            logger.debug(f"Using verification method {method_id} for agent {agent_id}")
            return method_id
        except Exception as e:
            logger.error(f"Error getting verification method for agent {agent_id}: {e}")
            return None

    async def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a message using the agent's DID.
        
        Args:
            message: Message to sign
            
        Returns:
            Message with added signature
        """
        try:
            # Create a copy to avoid modifying the original
            signed_message = message.copy()
            
            # Sign the message
            logger.debug(f"Signing message for agent {self.agent_id}")
            signature = await self.did_manager.sign_message(message)
            
            # Add signature and DID information to the message
            verification_method = f"{self.did_manager.get_did()}#keys-1"
            signed_message["signature"] = {
                "type": "Ed25519Signature2018",
                "verificationMethod": verification_method,
                "signature": signature
            }
            
            # Add the agent's DID to the message
            signed_message["did"] = self.did_manager.get_did()
            
            logger.debug(f"Successfully signed message with verification method {verification_method}")
            return signed_message
        except Exception as e:
            logger.error(f"Error signing message: {e}")
            # Return original message if signing fails
            return message

    async def verify_message(self, message: Dict[str, Any]) -> bool:
        """Verify a signed message.
        
        Args:
            message: Signed message to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Validate message format
            if "signature" not in message or "did" not in message:
                logger.warning("Message is missing signature or DID information")
                return False
                
            # Extract signature and DID information
            signature_info = message["signature"]
            sender_did = message["did"]
            logger.debug(f"Verifying message from DID: {sender_did}")
            
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
            is_valid = await self.did_manager.verify_message(
                message_to_verify,
                signature_info["signature"],
                verification_method
            )
            
            if is_valid:
                logger.debug(f"Successfully verified message from agent {sender_id}")
            else:
                logger.warning(f"Signature verification failed for message from agent {sender_id}")
                
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying message: {e}")
            return False

    async def handle_exchange_did(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DID document exchange.
        
        Args:
            params: Request parameters with DID document
            
        Returns:
            Response with this agent's DID document
        """
        try:
            logger.info("Processing DID exchange request")
            # Extract sender information
            sender_id = params.get("source_agent_id")
            sender_did_document = params.get("did_document")
            
            if not sender_id or not sender_did_document:
                logger.warning("Invalid DID exchange request: missing required parameters")
                return {
                    "status": "error",
                    "message": "Missing source_agent_id or did_document in request"
                }
                
            # Register the sender's DID document
            await self.register_agent_did(sender_id, sender_did_document)
            
            # Return this agent's DID document
            logger.info(f"Completed DID exchange with agent {sender_id}")
            return {
                "status": "success",
                "agent_id": self.agent_id,
                "did": self.did_manager.get_did(),
                "did_document": self.did_manager.get_did_document()
            }
        except Exception as e:
            logger.error(f"Error in DID exchange: {e}")
            return {
                "status": "error",
                "message": f"Internal error in DID exchange: {str(e)}"
            }
        
    async def _verify_challenge_response(self, sender_id: str, challenge_id: str, signature: str) -> Dict[str, Any]:
        """Verify a challenge response from an agent.
        
        Args:
            sender_id: ID of the agent responding to challenge
            challenge_id: ID of the challenge
            signature: Signature of the challenge
            
        Returns:
            Response with verification result
        """
        # Verify the challenge exists
        if challenge_id not in self.challenges:
            logger.warning(f"Challenge {challenge_id} not found or expired")
            return {
                "status": "error",
                "message": "Challenge not found or expired"
            }
            
        challenge = self.challenges[challenge_id]
        
        # Verify the challenge belongs to this agent
        if challenge["agent_id"] != sender_id:
            logger.warning(f"Challenge {challenge_id} was issued to {challenge['agent_id']}, not {sender_id}")
            return {
                "status": "error", 
                "message": "Challenge was issued to a different agent"
            }
            
        # Verify the signature
        verification_method = await self.get_verification_method(sender_id)
        if not verification_method:
            logger.warning(f"No verification method found for agent {sender_id}")
            return {
                "status": "error",
                "message": "No verification method found for agent"
            }
            
        is_valid = await self.did_manager.verify_message(
            {"challenge": challenge["challenge"]},
            signature,
            verification_method
        )
        
        if is_valid:
            # Mark the challenge as verified
            self.challenges[challenge_id]["verified"] = True
            logger.info(f"Successfully verified identity for agent {sender_id}")
            
            return {
                "status": "success",
                "message": "Identity verified successfully"
            }
        else:
            logger.warning(f"Signature verification failed for agent {sender_id}")
            return {
                "status": "error",
                "message": "Signature verification failed"
            }
    
    async def _issue_new_challenge(self, sender_id: str, provided_challenge: Optional[str] = None) -> Dict[str, Any]:
        """Issue a new challenge for an agent to verify their identity.
        
        Args:
            sender_id: ID of the agent requesting verification
            provided_challenge: Optional challenge provided by the agent
            
        Returns:
            Response with challenge information
        """
        # If agent provided their own challenge, use it, otherwise generate one
        challenge = provided_challenge or secrets.token_hex(32)
        challenge_id = str(uuid.uuid4())
        
        logger.debug(f"Issuing new challenge {challenge_id} for agent {sender_id}")
        
        # Store the challenge
        self.challenges[challenge_id] = {
            "agent_id": sender_id,
            "challenge": challenge,
            "timestamp": asyncio.get_event_loop().time(),
            "verified": False
        }
        
        # Sign the challenge with our key
        signature = await self.did_manager.sign_message({"challenge": challenge})
        verification_method = f"{self.did_manager.get_did()}#keys-1"
        
        logger.info(f"Challenge {challenge_id} issued for agent {sender_id}")
        return {
            "status": "success",
            "challenge_id": challenge_id,
            "challenge": challenge,
            "signature": signature,
            "verification_method": verification_method
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
        try:
            sender_id = params.get("source_agent_id")
            
            if not sender_id:
                logger.warning("Missing source_agent_id in verification request")
                return {
                    "status": "error",
                    "message": "Missing source_agent_id in request"
                }
                
            logger.info(f"Processing identity verification request from agent {sender_id}")
                
            # Case 1: Agent is responding to our challenge
            if "signature" in params and "challenge_id" in params:
                logger.debug(f"Agent {sender_id} is responding to challenge")
                challenge_id = params.get("challenge_id")
                signature = params.get("signature")
                return await self._verify_challenge_response(sender_id, challenge_id, signature)
            
            # Case 2: Agent is requesting verification (we issue a challenge)
            else:
                logger.debug(f"Agent {sender_id} is requesting a challenge")
                challenge = params.get("challenge")
                return await self._issue_new_challenge(sender_id, challenge)
                
        except Exception as e:
            logger.error(f"Error in identity verification: {e}")
            return {
                "status": "error",
                "message": f"Internal error in identity verification: {str(e)}"
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
        try:
            method = request.get("method")
            params = request.get("params", {})
            
            logger.debug(f"Handling secure request for method: {method}")
            
            # Handle security methods directly in security middleware
            if method == "exchange_did":
                return await self.handle_exchange_did(params)
            elif method == "verify_identity":
                return await self.handle_verify_identity(params)
                
            # For other methods, let the protocol handler handle it
            logger.debug(f"Delegating method {method} to protocol handler")
            return await handler_func()
        except Exception as e:
            logger.error(f"Error in secure request handler: {e}")
            return {
                "status": "error",
                "message": f"Internal security error: {str(e)}"
            }
