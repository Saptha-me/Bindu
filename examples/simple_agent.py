"""
Simple Agent Deployment Example.

This example demonstrates how to create any agent and deploy it with a single function call.
The pebbling framework handles all the complexity of DID generation, security, and server setup.
"""

import asyncio
import os
import json
from typing import Any, List, Optional, Dict, Union
from textwrap import dedent

# Import necessary pebbling components
from pebbling.core.protocol import CoreProtocolMethod
from pebbling.server.pebbling_server import pebblify
from pebbling.security import with_did
from pebbling.security.did_manager import DIDManager

# Default host for local deployment
DEFAULT_HOST = "127.0.0.1"

class SimpleAgent:
    """
    A simple agent class that can be extended by developers.
    Developers only need to implement the process_message method.
    """
    
    def __init__(self, instructions: str, name: str = "simple-agent", key_path: Optional[str] = None):
        """
        Initialize a simple agent.
        
        Args:
            instructions: The instructions/prompt for the agent
            name: Name identifier for the agent
            key_path: Path to store the DID key (if None, uses default path)
        """
        self.instructions = instructions
        self.name = name
        
        # Initialize DIDManager directly
        self.key_path = key_path or f"keys/{name.replace(' ', '_').lower()}_key.json"
        # Ensure keys directory exists
        os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
        
        # Create DIDManager and generate DID
        self.did_manager = DIDManager(self.key_path)
        self.did = self.did_manager.did
        self.did_document = self.did_manager.get_did_document(endpoint=f"https://pebbling-agent.example.com/{name}")
    
    def process_message(self, message: str) -> str:
        """
        Process a message and return a response.
        
        Override this method in your custom agent implementation.
        
        Args:
            message: The input message to process
            
        Returns:
            The agent's response
        """
        return f"Echo: {message}"


def create_simple_agent(
    instructions: str,
    name: str = "simple-agent",
    key_path: Optional[str] = None
) -> SimpleAgent:
    """
    Create a simple agent with DID-based security.
    
    Args:
        instructions: The instructions/prompt for the agent
        name: Name identifier for the agent
        key_path: Path to store the DID key (if None, uses default path)
        
    Returns:
        A SimpleAgent instance with DID capabilities
    """
    # Create agent with DID capabilities
    agent = SimpleAgent(
        instructions=instructions, 
        name=name, 
        key_path=key_path
    )
    
    print(f"Created agent with DID: {agent.did}")
    print(f"DID Document: {json.dumps(agent.did_document, indent=2)}")
    
    return agent


async def deploy_agent(
    agent: SimpleAgent,
    pebbling_port: int = 3773,
    user_port: int = 3774,
    host: str = DEFAULT_HOST,
    register_with_hibiscus: bool = False,
    hibiscus_url: str = "http://localhost:8000",
    hibiscus_api_key: str = None,
    enable_security: bool = True,
    enable_mtls: bool = True,
    description: str = None,
    capabilities: List[Dict[str, str]] = None,
    domains: List[str] = None,
    tags: List[str] = None,
    protocol_config_path: str = "./protocol_config.json",
):
    """
    Deploy an agent with pebbling's protocol framework.
    
    Args:
        agent: The SimpleAgent instance to deploy
        pebbling_port: Port for the JSON-RPC server
        user_port: Port for the REST API server
        host: Host address to bind to
        register_with_hibiscus: Whether to register with Hibiscus directory
        hibiscus_url: URL of the Hibiscus service
        hibiscus_api_key: API key for Hibiscus
        enable_security: Whether to enable DID-based security
        enable_mtls: Whether to enable mTLS with Sheldon certificates
        description: Description of the agent
        capabilities: List of capability dictionaries
        domains: List of domains the agent operates in
        tags: List of tags to categorize the agent
        protocol_config_path: Path to protocol configuration file
    """
    # Default description
    if description is None:
        description = f"A simple agent named {agent.name}"
    
    # Default capabilities
    if capabilities is None:
        capabilities = [
            {
                "name": "text-processing",
                "description": "Can process text messages"
            }
        ]
    
    # Default domains and tags
    if domains is None:
        domains = ["general"]
    if tags is None:
        tags = ["simple-agent"]
    
    # Define supported protocol methods
    supported_methods = [
        CoreProtocolMethod.CONTEXT,
        CoreProtocolMethod.ACT,
    ]
    
    # Deploy the agent with pebbling
    await pebblify(
        agent=agent,
        supported_methods=supported_methods,
        pebbling_port=pebbling_port,
        user_port=user_port,
        host=host,
        protocol_config_path=protocol_config_path,
        # Security configuration
        did_manager=agent.did_manager,
        enable_security=enable_security,
        enable_mtls=enable_mtls,
        cert_path="keys/",
        # Hibiscus registration
        register_with_hibiscus=register_with_hibiscus,
        hibiscus_url=hibiscus_url,
        hibiscus_api_key=hibiscus_api_key,
        # Agent metadata
        agent_name=agent.name,
        agent_description=description,
        agent_capabilities=capabilities,
        agent_domains=domains,
        agent_tags=tags,
        agent_metadata={
            "framework": "Pebbling Simple Agent",
            "programming_language": "Python",
            "supported_languages": ["en"]
        },
        agent_author="Pebbling Developer"
    )


# Convenience function for one-line agent creation and deployment
async def run_simple_agent(
    instructions: str,
    name: str = "simple-agent",
    key_path: Optional[str] = None,
    pebbling_port: int = 3773,
    user_port: int = 3774,
    host: str = DEFAULT_HOST,
    register_with_hibiscus: bool = False,
    hibiscus_url: str = "http://localhost:8000",
    hibiscus_api_key: str = None,
    enable_security: bool = True,
    enable_mtls: bool = True,
    description: str = None,
    capabilities: List[Dict[str, str]] = None,
    domains: List[str] = None,
    tags: List[str] = None,
    protocol_config_path: str = "./protocol_config.json",
):
    """
    Create and deploy a simple agent in one function call.
    
    Args:
        instructions: The instructions/prompt for the agent
        name: Name identifier for the agent
        key_path: Path to store the DID key
        pebbling_port: Port for the JSON-RPC server
        user_port: Port for the REST API server
        host: Host address to bind to
        register_with_hibiscus: Whether to register with Hibiscus directory
        hibiscus_url: URL of the Hibiscus service
        hibiscus_api_key: API key for Hibiscus
        enable_security: Whether to enable DID-based security
        enable_mtls: Whether to enable mTLS with Sheldon certificates
        description: Description of the agent
        capabilities: List of capability dictionaries
        domains: List of domains the agent operates in
        tags: List of tags to categorize the agent
        protocol_config_path: Path to protocol configuration file
    """
    # Create the agent
    agent = create_simple_agent(
        instructions=instructions,
        name=name,
        key_path=key_path
    )
    
    print(f"Agent created: {agent.name}")
    print(f"Agent DID: {agent.did}")
    
    # Deploy the agent
    await deploy_agent(
        agent=agent,
        pebbling_port=pebbling_port,
        user_port=user_port,
        host=host,
        register_with_hibiscus=register_with_hibiscus,
        hibiscus_url=hibiscus_url,
        hibiscus_api_key=hibiscus_api_key,
        enable_security=enable_security,
        enable_mtls=enable_mtls,
        description=description,
        capabilities=capabilities,
        domains=domains,
        tags=tags,
        protocol_config_path=protocol_config_path,
    )


# Example usage
if __name__ == "__main__":
    # Define agent instructions
    instructions = dedent(
        """\
        You are a helpful assistant that provides concise and accurate responses.
        Always be polite and respectful in your interactions.
        """
    )
    
    # Run the agent with a single function call
    asyncio.run(
        run_simple_agent(
            instructions=instructions,
            name="helpful-assistant",
            register_with_hibiscus=False,  # Set to True to register with Hibiscus
        )
    )
