"""
Custom Agent Adapter Example.

This example demonstrates how to create a custom agent adapter that integrates
with the Pebbling framework, providing one-line agent deployment capabilities.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Union
from textwrap import dedent

# Pebbling imports
from pebbling.agent.base_adapter import BaseAdapter, BaseAgentRunner, BaseProtocolHandler
from pebbling.core.protocol import CoreProtocolMethod
from pebbling.security import with_did
from pebbling.server.pebbling_server import pebblify
from pebbling.server.schemas.model import (
    AgentResponse,
    AudioArtifact,
    ImageArtifact,
    VideoArtifact,
)

# Default host for local deployment
DEFAULT_HOST = "127.0.0.1"


class CustomAgent:
    """
    A custom agent class that can be extended by developers.
    Developers only need to implement the process_message method.
    """
    
    def __init__(self, instructions: str, name: str = "custom-agent"):
        """
        Initialize a custom agent.
        
        Args:
            instructions: The instructions/prompt for the agent
            name: Name identifier for the agent
        """
        self.instructions = instructions
        self.name = name
        self.session_store = {}  # Simple in-memory session store
        self.context_store = {}  # Simple in-memory context store
        
        # These will be populated by the @with_did decorator
        self.pebble_did = None
        self.pebble_did_document = None
        self.pebble_did_manager = None
    
    def process_message(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a message and return a response.
        
        Override this method in your custom agent implementation.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier for conversation continuity
            
        Returns:
            The agent's response
        """
        # Simple echo implementation - override this in your agent
        if session_id and session_id in self.session_store:
            history = self.session_store[session_id]
            history.append(f"User: {message}")
            response = f"Echo: {message} (Session: {session_id})"
            history.append(f"Agent: {response}")
            return response
        else:
            # Create new session if none exists
            if session_id:
                self.session_store[session_id] = []
                self.session_store[session_id].append(f"User: {message}")
                response = f"Echo: {message} (New session: {session_id})"
                self.session_store[session_id].append(f"Agent: {response}")
                return response
            else:
                return f"Echo: {message}"


class CustomAgentAdapter(BaseAdapter):
    """
    Adapter for integrating custom agents with the Pebbling protocol.
    """
    
    def __init__(self, agent: CustomAgent, agent_id: Optional[str] = None):
        """
        Initialize with a custom agent.
        
        Args:
            agent: The custom agent to adapt
            agent_id: Optional agent identifier
        """
        super().__init__(agent_id)
        self.agent = agent
    
    def create_agent_runner(self) -> "CustomAgentRunner":
        """Create an agent runner for the REST API."""
        return CustomAgentRunner(self.agent, self.agent_id)
    
    def create_protocol_handler(self) -> "CustomProtocolHandler":
        """Create a protocol handler for JSON-RPC endpoints."""
        return CustomProtocolHandler(self.agent, self.agent_id)


class CustomAgentRunner(BaseAgentRunner):
    """
    Runner for custom agents that implements the REST API endpoints.
    """
    
    def __init__(self, agent: CustomAgent, agent_id: Optional[str] = None):
        """
        Initialize with a custom agent.
        
        Args:
            agent: The custom agent to run
            agent_id: Optional agent identifier
        """
        super().__init__(agent_id)
        self.agent = agent
    
    def run(self, input_text: str, **kwargs) -> str:
        """
        Run the agent with the given input text.
        
        Args:
            input_text: The input text to process
            kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        session_id = kwargs.get("session_id")
        return self.agent.process_message(input_text, session_id)
    
    def get_status(self) -> str:
        """
        Get the current status of the agent.
        
        Returns:
            Status string
        """
        return "healthy"


class CustomProtocolHandler(BaseProtocolHandler):
    """
    Protocol handler for custom agents that implements the JSON-RPC methods.
    """
    
    def __init__(self, agent: CustomAgent, agent_id: Optional[str] = None):
        """
        Initialize with a custom agent.
        
        Args:
            agent: The custom agent to handle protocols for
            agent_id: Optional agent identifier
        """
        super().__init__(agent_id)
        self.agent = agent
        self.original_context = {}  # For context restoration
    
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the Context method.
        
        Args:
            params: Parameters for the context operation
            
        Returns:
            Dict with operation result
        """
        operation = params.get("operation")
        key = params.get("key")
        value = params.get("value", None)
        user_id = params.get("user_id", "default")
        
        # Create user context if it doesn't exist
        if user_id not in self.agent.context_store:
            self.agent.context_store[user_id] = {}
        
        if operation == "add" or operation == "update":
            if key and value is not None:
                self.agent.context_store[user_id][key] = value
                return {"success": True, "message": f"{operation} context success"}
            else:
                return {"success": False, "message": "Missing key or value"}
        elif operation == "delete":
            if key in self.agent.context_store[user_id]:
                del self.agent.context_store[user_id][key]
                return {"success": True, "message": "delete context success"}
            else:
                return {"success": False, "message": f"Key {key} not found"}
        else:
            return {"success": False, "message": f"Unknown operation {operation}"}
    
    async def handle_act(
        self,
        source_agent_id: str,
        message: str,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a text request and generate a response.
        
        Args:
            source_agent_id: The source agent identifier
            message: The text message to process
            session_id: Session identifier for conversation continuity
            
        Returns:
            AgentResponse with the agent's reply
        """
        # Generate or use the provided session ID
        session_id = session_id or str(uuid.uuid4())
        
        # Process the message with the agent
        response_text = self.agent.process_message(message, session_id)
        
        # Return the response in the Pebbling protocol format
        return AgentResponse(
            source_agent_id=self.agent_id,
            target_agent_id=source_agent_id,
            session_id=session_id,
            message=response_text,
        )
    
    async def handle_listen(
        self,
        source_agent_id: str,
        message: str,
        audio: AudioArtifact,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process audio input with optional text and generate a response.
        
        Args:
            source_agent_id: The source agent identifier
            message: The text message to process
            audio: The audio input to process
            session_id: Session identifier for conversation continuity
            
        Returns:
            AgentResponse with the agent's reply
        """
        # For this simple example, we just process the text message
        # and ignore the audio input
        return await self.handle_act(source_agent_id, message, session_id)
    
    async def handle_view(
        self,
        source_agent_id: str,
        message: str,
        media: Union[VideoArtifact, ImageArtifact],
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Process visual media with optional text and generate a response.
        
        Args:
            source_agent_id: The source agent identifier
            message: The text message to process
            media: The media input (image or video) to process
            session_id: Session identifier for conversation continuity
            
        Returns:
            AgentResponse with the agent's reply
        """
        # For this simple example, we just process the text message
        # and ignore the media input
        return await self.handle_act(source_agent_id, message, session_id)
    
    def apply_user_context(self, user_id: str) -> None:
        """
        Apply user-specific context to the agent.
        
        Args:
            user_id: ID of the user to apply context for
        """
        # Store original context for later restoration
        self.original_context = self.agent.context_store.get("default", {}).copy()
        
        # Apply user-specific context if it exists
        if user_id in self.agent.context_store:
            # Merge with default context
            user_context = {**self.original_context, **self.agent.context_store[user_id]}
            self.agent.context_store["default"] = user_context
    
    def reset_context(self) -> None:
        """
        Reset to original context after processing a user request.
        """
        # Restore original context
        self.agent.context_store["default"] = self.original_context


def create_custom_agent(
    instructions: str,
    name: str = "custom-agent",
    key_path: Optional[str] = None
) -> CustomAgent:
    """
    Create a custom agent with DID-based security.
    
    Args:
        instructions: The instructions/prompt for the agent
        name: Name identifier for the agent
        key_path: Path to store the DID key (if None, uses default path)
        
    Returns:
        A CustomAgent instance with DID capabilities
    """
    # Default key path if not provided
    if key_path is None:
        key_path = f"keys/{name.replace(' ', '_').lower()}_key.json"
    
    # Create and secure the agent with DID
    @with_did(key_path=key_path, endpoint=f"https://pebbling-agent.example.com/{name}")
    def build_agent():
        return CustomAgent(instructions=instructions, name=name)
    
    return build_agent()


async def deploy_agent(
    agent: CustomAgent,
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
    Deploy a custom agent with Pebbling's protocol framework.
    
    Args:
        agent: The CustomAgent instance to deploy
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
    # Create the adapter for the agent
    adapter = CustomAgentAdapter(agent)
    
    # Default description
    if description is None:
        description = f"A custom agent named {agent.name}"
    
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
        tags = ["custom-agent"]
    
    # Define supported protocol methods
    supported_methods = [
        CoreProtocolMethod.CONTEXT,
        CoreProtocolMethod.ACT,
    ]
    
    # Deploy the agent with pebbling
    await pebblify(
        agent=adapter,
        supported_methods=supported_methods,
        pebbling_port=pebbling_port,
        user_port=user_port,
        host=host,
        protocol_config_path=protocol_config_path,
        # Security configuration
        did_manager=agent.pebble_did_manager,
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
            "framework": "Pebbling Custom Agent",
            "programming_language": "Python",
            "supported_languages": ["en"]
        },
        agent_author="Pebbling Developer"
    )


# Convenience function for one-line agent creation and deployment
async def run_custom_agent(
    instructions: str,
    name: str = "custom-agent",
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
    Create and deploy a custom agent in one function call.
    
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
    agent = create_custom_agent(
        instructions=instructions,
        name=name,
        key_path=key_path
    )
    
    print(f"Agent created: {agent.name}")
    print(f"Agent DID: {agent.pebble_did}")
    
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


# Example of creating a custom agent subclass
class MyCustomAgent(CustomAgent):
    """Example of extending CustomAgent with specific behavior."""
    
    def process_message(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a message and return a customized response.
        
        Args:
            message: The input message to process
            session_id: Optional session identifier
            
        Returns:
            The agent's response
        """
        # Simple example of custom processing logic
        if "hello" in message.lower():
            return "Hello there! How can I assist you today?"
        elif "bye" in message.lower():
            return "Goodbye! Have a great day!"
        else:
            return f"I received your message: '{message}'. How can I help with that?"


# Example usage
if __name__ == "__main__":
    # Define agent instructions
    instructions = dedent(
        """\
        You are a helpful assistant that provides concise and accurate responses.
        Always be polite and respectful in your interactions.
        """
    )
    
    # Run the custom agent with a single function call
    asyncio.run(
        run_custom_agent(
            instructions=instructions,
            name="helpful-assistant",
            register_with_hibiscus=False,  # Set to True to register with Hibiscus
        )
    )
    
    # Alternative: create a custom agent subclass and run it
    """
    # Create a custom agent instance
    my_agent = MyCustomAgent(
        instructions=instructions,
        name="my-custom-assistant"
    )
    
    # Apply DID security
    @with_did(key_path="keys/my_custom_assistant_key.json", 
              endpoint="https://pebbling-agent.example.com/my-custom-assistant")
    def secure_my_agent():
        return my_agent
    
    secured_agent = secure_my_agent()
    
    # Deploy manually
    asyncio.run(
        deploy_agent(
            agent=secured_agent,
            name="my-custom-assistant",
            register_with_hibiscus=False,
        )
    )
    """
