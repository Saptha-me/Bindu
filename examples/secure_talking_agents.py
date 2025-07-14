"""
Example demonstrating two agents communicating securely with mTLS.

This example shows how to:
1. Start two agents with mTLS enabled
2. Exchange DIDs and certificates securely
3. Verify connections with token-based validation
4. Communicate using secure JSON-RPC over mTLS
"""

import os
import sys
import time
import uuid
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp
from loguru import logger

# Add project root to path for importing pebbling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pebbling.server.pebbling_mtls_server import pebblify_secure
from pebbling.server.mtls_server_utils import (
    secure_agent_request,
    send_jsonrpc_request_secure,
    verify_agent_connection
)
from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.security.did_manager import DIDManager


# JSON-RPC handlers for Agent Alice
async def alice_hello(name: str, **kwargs) -> Dict[str, Any]:
    """Handler for 'hello' method in Alice agent."""
    logger.info(f"[Alice] Received hello from {name}")
    return {"message": f"Hello {name}, I'm Alice! The time is {datetime.utcnow().isoformat()}"}


async def alice_conversation(message: str, **kwargs) -> Dict[str, Any]:
    """Handler for 'conversation' method in Alice agent."""
    logger.info(f"[Alice] Received message: {message}")
    responses = [
        "That's interesting, tell me more about it.",
        "I understand your point, but have you considered the alternatives?",
        "Let's explore this topic further.",
        "I appreciate your perspective on this matter.",
        "This conversation is providing valuable insights."
    ]
    import random
    return {"response": random.choice(responses)}


# JSON-RPC handlers for Agent Bob
async def bob_hello(name: str, **kwargs) -> Dict[str, Any]:
    """Handler for 'hello' method in Bob agent."""
    logger.info(f"[Bob] Received hello from {name}")
    return {"message": f"Hello {name}, I'm Bob! The time is {datetime.utcnow().isoformat()}"}


async def bob_conversation(message: str, **kwargs) -> Dict[str, Any]:
    """Handler for 'conversation' method in Bob agent."""
    logger.info(f"[Bob] Received message: {message}")
    responses = [
        "That's a compelling argument.",
        "I hadn't thought about it that way before.",
        "Your insights are very helpful for my understanding.",
        "This secure communication channel is working well.",
        "Let's continue this discussion securely."
    ]
    import random
    return {"response": random.choice(responses)}


async def run_alice_agent(
    sheldon_ca_url: str,
    host: str = "localhost",
    port: int = 8000,
    bob_url: str = "https://localhost:8001"
) -> None:
    """Run the Alice agent with mTLS enabled.
    
    Args:
        sheldon_ca_url: URL of the Sheldon CA
        host: Host to bind to
        port: Port to bind to
        bob_url: URL of the Bob agent
    """
    # Define Alice's handlers
    alice_handlers = {
        "hello": alice_hello,
        "conversation": alice_conversation
    }
    
    # Initialize Alice with mTLS security
    logger.info("[Alice] Starting with mTLS security...")
    app, did_manager, cert_manager = await pebblify_secure(
        "alice",
        alice_handlers,
        sheldon_ca_url=sheldon_ca_url,
        host=host,
        port=port,
        enable_mtls=True,
        auto_renew_certificates=True
    )
    
    logger.info(f"[Alice] Started with DID: {did_manager.did}")
    
    # Allow time for both agents to start
    await asyncio.sleep(2)
    
    # Attempt to connect to Bob and verify connection
    logger.info(f"[Alice] Establishing secure connection with Bob at {bob_url}")
    success, result = await verify_agent_connection(bob_url, cert_manager, did_manager)
    
    if not success:
        logger.error(f"[Alice] Failed to establish secure connection with Bob: {result.get('error', 'Unknown error')}")
        return
        
    logger.info(f"[Alice] Successfully established secure connection with Bob (DID: {result.get('did', 'unknown')})")
    
    # Send a hello request to Bob
    logger.info("[Alice] Sending hello request to Bob")
    hello_result = await send_jsonrpc_request_secure(
        f"{bob_url}/jsonrpc",
        "hello",
        {"name": "Alice"},
        cert_manager,
        did_manager
    )
    
    if "error" in hello_result:
        logger.error(f"[Alice] Hello request failed: {hello_result['error']}")
    else:
        logger.info(f"[Alice] Received from Bob: {hello_result.get('result', {}).get('message', 'No message')}")
    
    # Start conversation with Bob
    for i in range(5):
        try:
            # Send a message to Bob
            message = f"Message #{i+1} from Alice at {datetime.utcnow().isoformat()}"
            logger.info(f"[Alice] Sending to Bob: {message}")
            
            convo_result = await send_jsonrpc_request_secure(
                f"{bob_url}/jsonrpc",
                "conversation",
                {"message": message},
                cert_manager,
                did_manager
            )
            
            if "error" in convo_result:
                logger.error(f"[Alice] Conversation request failed: {convo_result['error']}")
            else:
                response = convo_result.get("result", {}).get("response", "No response")
                logger.info(f"[Alice] Received from Bob: {response}")
                
            # Wait before next message
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"[Alice] Error in conversation: {str(e)}")
    
    logger.info("[Alice] Conversation completed")


async def run_bob_agent(
    sheldon_ca_url: str,
    host: str = "localhost",
    port: int = 8001,
    alice_url: str = "https://localhost:8000"
) -> None:
    """Run the Bob agent with mTLS enabled.
    
    Args:
        sheldon_ca_url: URL of the Sheldon CA
        host: Host to bind to
        port: Port to bind to
        alice_url: URL of the Alice agent
    """
    # Define Bob's handlers
    bob_handlers = {
        "hello": bob_hello,
        "conversation": bob_conversation
    }
    
    # Initialize Bob with mTLS security
    logger.info("[Bob] Starting with mTLS security...")
    app, did_manager, cert_manager = await pebblify_secure(
        "bob",
        bob_handlers,
        sheldon_ca_url=sheldon_ca_url,
        host=host,
        port=port,
        enable_mtls=True,
        auto_renew_certificates=True
    )
    
    logger.info(f"[Bob] Started with DID: {did_manager.did}")
    
    # Allow time for both agents to start
    await asyncio.sleep(3)
    
    # Send a hello request to Alice
    logger.info(f"[Bob] Establishing secure connection with Alice at {alice_url}")
    success, result = await verify_agent_connection(alice_url, cert_manager, did_manager)
    
    if not success:
        logger.error(f"[Bob] Failed to establish secure connection with Alice: {result.get('error', 'Unknown error')}")
        return
        
    logger.info(f"[Bob] Successfully established secure connection with Alice (DID: {result.get('did', 'unknown')})")
    
    # Send a hello request to Alice
    logger.info("[Bob] Sending hello request to Alice")
    hello_result = await send_jsonrpc_request_secure(
        f"{alice_url}/jsonrpc",
        "hello",
        {"name": "Bob"},
        cert_manager,
        did_manager
    )
    
    if "error" in hello_result:
        logger.error(f"[Bob] Hello request failed: {hello_result['error']}")
    else:
        logger.info(f"[Bob] Received from Alice: {hello_result.get('result', {}).get('message', 'No message')}")
    
    # Bob will listen for Alice's messages (handled by the JSON-RPC server)
    logger.info("[Bob] Listening for incoming messages from Alice...")
    
    # Keep agent running
    while True:
        await asyncio.sleep(1)


async def run_verification_demo(
    sheldon_ca_url: str,
    alice_cert_manager: CertificateManager,
    alice_did_manager: DIDManager,
    bob_url: str = "https://localhost:8001"
) -> None:
    """Demonstrate 24-hour token verification flow.
    
    Args:
        sheldon_ca_url: URL of the Sheldon CA
        alice_cert_manager: Alice's certificate manager
        alice_did_manager: Alice's DID manager
        bob_url: URL of the Bob agent
    """
    logger.info("\n===== TOKEN VERIFICATION DEMO =====")
    
    # First, get Alice's certificate fingerprint
    cert_info = alice_cert_manager.get_certificate_info()
    fingerprint = cert_info["fingerprint"]
    
    # Check if we have a valid token
    token_valid = False
    try:
        token, is_expiring_soon = alice_cert_manager.token_manager.get_token(fingerprint)
        token_valid = True
        logger.info(f"Alice has a valid verification token for her certificate")
        
        # Token data
        token_data = alice_cert_manager.token_manager.tokens[fingerprint]
        expires_at = datetime.fromtimestamp(token_data["expires_at"])
        now = datetime.now()
        remaining = (expires_at - now).total_seconds()
        
        logger.info(f"Token expires at {expires_at.isoformat()}, {remaining:.1f} seconds remaining")
        
        if is_expiring_soon:
            logger.info(f"Token is expiring soon, will be refreshed on next verification")
    except Exception:
        logger.info(f"Alice has no valid token for her certificate")
    
    # Verify connection with Bob, which should verify the certificate
    logger.info(f"Alice is verifying connection with Bob")
    success, result = await verify_agent_connection(bob_url, alice_cert_manager, alice_did_manager)
    
    if success:
        logger.info(f"Connection verification successful")
        
        # Check token status again
        try:
            token, is_expiring_soon = alice_cert_manager.token_manager.get_token(fingerprint)
            logger.info(f"After verification, Alice now has a valid token that expires in "
                      f"{alice_cert_manager.token_manager.tokens[fingerprint]['expires_at'] - time.time():.1f} seconds")
        except Exception as e:
            logger.error(f"Failed to get token after verification: {str(e)}")
    else:
        logger.error(f"Connection verification failed: {result.get('error', 'Unknown error')}")
    
    logger.info("===== END OF TOKEN VERIFICATION DEMO =====\n")


async def main():
    parser = argparse.ArgumentParser(description="Secure Talking Agents Example with mTLS")
    parser.add_argument("--sheldon-ca", type=str, default="http://localhost:5000", 
                      help="URL of the Sheldon CA service")
    parser.add_argument("--mode", type=str, choices=["alice", "bob", "both"], default="both",
                      help="Which agent(s) to run")
    parser.add_argument("--alice-host", type=str, default="localhost",
                      help="Host for Alice agent")
    parser.add_argument("--alice-port", type=int, default=8000,
                      help="Port for Alice agent")
    parser.add_argument("--bob-host", type=str, default="localhost",
                      help="Host for Bob agent")
    parser.add_argument("--bob-port", type=int, default=8001,
                      help="Port for Bob agent")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # URLs for agents
    alice_url = f"https://{args.alice_host}:{args.alice_port}"
    bob_url = f"https://{args.bob_host}:{args.bob_port}"
    
    if args.mode == "alice" or args.mode == "both":
        alice_task = asyncio.create_task(run_alice_agent(
            args.sheldon_ca,
            args.alice_host,
            args.alice_port,
            bob_url
        ))
    else:
        alice_task = None
    
    if args.mode == "bob" or args.mode == "both":
        bob_task = asyncio.create_task(run_bob_agent(
            args.sheldon_ca,
            args.bob_host,
            args.bob_port,
            alice_url
        ))
    else:
        bob_task = None
    
    # Run the tasks
    if alice_task and bob_task:
        await asyncio.gather(alice_task, bob_task)
    elif alice_task:
        await alice_task
    elif bob_task:
        await bob_task


if __name__ == "__main__":
    asyncio.run(main())
