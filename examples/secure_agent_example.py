#!/usr/bin/env python3
"""Example demonstrating secure agent-to-agent communication with mTLS."""

import asyncio
import os
import json
from typing import Dict, Any, Optional

from pebbling.core.agent import Agent
from pebbling.server.pebbling_server import pebblify
from pebbling.security.did_manager import DIDManager
from pebbling.security.cert_manager import CertificateManager
from pebbling.security.mtls_middleware import MTLSMiddleware
from pebbling.server.server_utils import create_secure_client_session, send_secure_request
from loguru import logger


class SecureAgent(Agent):
    """A simple agent with secure communication capabilities."""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        did_path: Optional[str] = None,
        cert_path: Optional[str] = None,
    ):
        """Initialize the secure agent.
        
        Args:
            agent_id: ID for the agent
            agent_name: Name for the agent
            did_path: Path to store/load DID documents
            cert_path: Path to store/load certificates
        """
        super().__init__(agent_id)
        self.agent_name = agent_name
        
        # Set default paths if not provided
        if did_path is None:
            did_path = f"data/dids/{agent_id}"
        if cert_path is None:
            cert_path = f"data/certs/{agent_id}"
            
        # Create directories if they don't exist
        os.makedirs(did_path, exist_ok=True)
        os.makedirs(cert_path, exist_ok=True)
        
        # Initialize DID manager
        self.did_manager = DIDManager(did_path=did_path)
        
        # Initialize certificate manager
        self.cert_manager = CertificateManager(
            did_manager=self.did_manager,
            cert_path=cert_path
        )
        
        # Initialize mTLS middleware
        self.mtls_middleware = MTLSMiddleware(
            did_manager=self.did_manager,
            cert_manager=self.cert_manager
        )
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message received from another agent.
        
        Args:
            message: The message to process
            
        Returns:
            Response message
        """
        logger.info(f"Agent {self.agent_name} processing message: {message}")
        
        # Simple echo response for demonstration
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "did": self.did_manager.get_did(),
            "message": f"Securely received your message: {message.get('content', '')}"
        }
        
    async def send_secure_message(
        self,
        target_url: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a secure message to another agent.
        
        Args:
            target_url: URL of the target agent
            message: Message content to send
            
        Returns:
            Response from the target agent
        """
        logger.info(f"Agent {self.agent_name} sending secure message to {target_url}")
        
        try:
            # Get client SSL context for mTLS
            ssl_context = self.mtls_middleware.get_client_ssl_context()
            
            # Create secure session
            async with create_secure_client_session(ssl_context) as session:
                # Prepare message
                data = {
                    "source_agent_id": self.agent_id,
                    "did": self.did_manager.get_did(),
                    "content": message
                }
                
                # Send message securely
                response = await send_secure_request(
                    session=session,
                    url=f"{target_url}/process",
                    json_data=data
                )
                
                return response
                
        except Exception as e:
            logger.error(f"Error sending secure message: {e}")
            return {"status": "error", "message": str(e)}


async def run_secure_agent(
    agent_id: str,
    agent_name: str,
    port: int,
    host: str = "localhost"
) -> SecureAgent:
    """Run a secure agent with mTLS enabled.
    
    Args:
        agent_id: ID for the agent
        agent_name: Name for the agent
        port: Port for the agent server
        host: Host for the agent server
        
    Returns:
        The agent instance
    """
    # Create the agent
    agent = SecureAgent(agent_id=agent_id, agent_name=agent_name)
    
    # Start the server with mTLS enabled
    await pebblify(
        agent=agent,
        agent_id=agent_id,
        port=port,
        host=host,
        enable_security=True,
        enable_mtls=True,
        register_with_hibiscus=True,
        agent_name=agent_name,
        agent_description=f"Secure agent with mTLS - {agent_name}"
    )
    
    return agent


async def demo_secure_communication():
    """Demonstrate secure communication between two agents."""
    logger.info("Starting secure communication demonstration")
    
    # Start Agent A
    agent_a = await run_secure_agent(
        agent_id="agent_a",
        agent_name="Agent A",
        port=3773,
        host="localhost"
    )
    
    # Start Agent B
    agent_b = await run_secure_agent(
        agent_id="agent_b",
        agent_name="Agent B",
        port=3774,
        host="localhost"
    )
    
    # Allow time for servers to start
    await asyncio.sleep(2)
    
    # Agent A sends message to Agent B
    response = await agent_a.send_secure_message(
        target_url="https://localhost:3774",
        message="Hello from Agent A!"
    )
    
    logger.info(f"Response from Agent B: {response}")
    
    # Agent B sends message to Agent A
    response = await agent_b.send_secure_message(
        target_url="https://localhost:3773",
        message="Hello from Agent B!"
    )
    
    logger.info(f"Response from Agent A: {response}")


if __name__ == "__main__":
    asyncio.run(demo_secure_communication())
