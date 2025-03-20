"""
MCP integration example for Pebble.

This example demonstrates how to use the Model Context Protocol (MCP) with Pebble,
including setting up MCP clients and servers for agent communication.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, Any

from pebble.adapters.agno_adapter import AgnoAdapter
from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.core.protocol import AgentProtocol
from pebble.mcp.client import MCPClientAdapter, MCPCognitiveAdapter
from pebble.mcp.server import MCPServer, MCPTool, MCPPrompt, MCPResource
from pebble.mcp.utils import (
    create_mcp_client,
    create_mcp_cognitive_client,
    create_mcp_server,
    register_standard_tools,
    register_standard_prompts,
    register_standard_resources
)
from pebble.schemas.models import (
    ActionRequest,
    CognitiveRequest,
    MessageRole,
    StimulusType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Example 1: Using MCP Client with an external MCP server
async def example_mcp_client():
    """Demonstrate how to use an MCP client to communicate with an external MCP server."""
    logger.info("=== Example: MCP Client ===")
    
    # Create an MCP client
    # Note: Replace 'endpoint' with the actual MCP server endpoint if using SSE
    mcp_client = create_mcp_client(
        transport_type="stdio",  # Use "sse" for Server-Sent Events
        # endpoint="http://localhost:8080",  # Required for SSE
        name="Pebble MCP Client",
        capabilities=["resources", "tools", "prompts", "sampling"],
        metadata={"model": {"name": "claude-3-haiku"}}
    )
    
    try:
        # Connect to the MCP server
        # Note: This is commented out because we don't have a real MCP server to connect to
        # await mcp_client.transport.connect()
        
        # Example of processing an action with the MCP client
        logger.info("Processing action through MCP client...")
        
        # Create an action request
        request = ActionRequest(
            agent_id=mcp_client.agent_id,
            session_id=str(uuid.uuid4()),
            message="What is the capital of France?",
            role=MessageRole.USER,
            metadata={}
        )
        
        # Process the action (commented out since we're not connected to a real server)
        # response = await mcp_client.process_action(request)
        # logger.info(f"Response: {response.message}")
        
        # Example of accessing an MCP resource
        logger.info("Accessing MCP resource...")
        # resource = await mcp_client.read_resource("mcp://resources/world_capitals")
        # logger.info(f"Resource content: {resource}")
        
        # Example of executing an MCP tool
        logger.info("Executing MCP tool...")
        # result = await mcp_client.execute_tool(
        #     session_id=str(uuid.uuid4()),
        #     tool_name="search_capitals",
        #     parameters={"country": "France"}
        # )
        # logger.info(f"Tool result: {result}")
        
        logger.info("MCP client example completed")
        
    except Exception as e:
        logger.error(f"Error in MCP client example: {e}")


# Example 2: Using MCP Server to expose a Pebble agent
async def example_mcp_server():
    """Demonstrate how to expose a Pebble agent as an MCP server."""
    logger.info("=== Example: MCP Server ===")
    
    # Create a mock agent implementation
    class MockAgent:
        def run(self, message):
            return f"Mock response to: {message}"
    
    # Create a Pebble agent adapter
    agent_adapter = AgnoAdapter(
        agent=MockAgent(),
        name="Mock Agno Agent",
        metadata={"description": "A mock agent for demonstration"}
    )
    
    # Create an MCP server that exposes the agent
    mcp_server = create_mcp_server(
        agent_protocol=agent_adapter,
        transport_type="stdio"  # Use "sse" for Server-Sent Events with web apps
    )
    
    # Register standard tools, prompts, and resources
    register_standard_tools(mcp_server)
    register_standard_prompts(mcp_server)
    register_standard_resources(mcp_server)
    
    # Register a custom tool
    async def calculate_sum(session_id: str, params: Dict[str, Any]) -> int:
        """Calculate the sum of two numbers."""
        a = params.get("a", 0)
        b = params.get("b", 0)
        return a + b
    
    mcp_server.register_tool(MCPTool(
        name="calculate_sum",
        description="Calculate the sum of two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        },
        handler=calculate_sum
    ))
    
    # Register a custom prompt
    mcp_server.register_prompt(MCPPrompt(
        name="math_problem",
        description="Generate a math problem",
        template="Create a math problem involving {operation} with difficulty level {difficulty}.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "Type of operation"},
                "difficulty": {"type": "string", "description": "Difficulty level"}
            },
            "required": ["operation", "difficulty"]
        }
    ))
    
    # Register a custom resource
    mcp_server.register_resource(MCPResource(
        uri="mcp://resources/math_operations",
        content_type="application/json",
        content={
            "operations": ["addition", "subtraction", "multiplication", "division"],
            "difficulties": ["easy", "medium", "hard"]
        },
        metadata={"description": "Available math operations and difficulty levels"}
    ))
    
    try:
        # Start the MCP server
        # Note: This is commented out because it would block the execution
        # await mcp_server.start()
        logger.info("MCP server example completed (server start commented out)")
        
    except Exception as e:
        logger.error(f"Error in MCP server example: {e}")


# Example 3: Using MCP with CognitiveAgentProtocol
async def example_mcp_cognitive():
    """Demonstrate how to use MCP with cognitive agents."""
    logger.info("=== Example: MCP with Cognitive Agents ===")
    
    # Create a mock cognitive agent
    cognitive_agent = CognitiveAgentProtocol(
        agent=None,  # No underlying agent for this example
        name="Cognitive Agent",
        cognitive_capabilities=["act", "listen", "think", "see"]
    )
    
    # Create an MCP cognitive client
    mcp_cognitive_client = create_mcp_cognitive_client(
        transport_type="stdio",
        name="MCP Cognitive Client",
        cognitive_capabilities=["act", "listen", "think"]
    )
    
    # Create an MCP server for the cognitive agent
    mcp_cognitive_server = create_mcp_server(
        agent_protocol=cognitive_agent,
        transport_type="stdio"
    )
    
    # Register cognitive-specific tools and prompts
    register_standard_tools(mcp_cognitive_server)
    register_standard_prompts(mcp_cognitive_server)
    
    try:
        # Example of a cognitive action through MCP
        logger.info("Processing cognitive action...")
        
        # Create a cognitive request
        request = CognitiveRequest(
            agent_id=cognitive_agent.agent_id,
            session_id=str(uuid.uuid4()),
            content="What is the significance of this historical event?",
            stimulus_type=StimulusType.ACTION,
            metadata={}
        )
        
        # Process the cognitive action (commented out since we're not connecting to a real server)
        # response = await mcp_cognitive_client.act(request)
        # logger.info(f"Cognitive response: {response.content}")
        # logger.info(f"Updated cognitive state: {response.cognitive_state}")
        
        logger.info("MCP cognitive example completed")
        
    except Exception as e:
        logger.error(f"Error in MCP cognitive example: {e}")


# Example 4: Bridging multiple agent frameworks via MCP
async def example_mcp_bridge():
    """Demonstrate how to use MCP to bridge multiple agent frameworks."""
    logger.info("=== Example: MCP Bridge Between Agent Frameworks ===")
    
    # For this example, we'll simulate having agents from different frameworks
    # In a real implementation, these would be actual agents from Agno, CrewAI, etc.
    
    # Simulate Agno agent
    class MockAgnoAgent:
        def run(self, message):
            return f"Agno agent processed: {message}"
    
    # Wrap with Pebble adapter
    agno_adapter = AgnoAdapter(
        agent=MockAgnoAgent(),
        name="Agno Agent",
        metadata={"framework": "agno"}
    )
    
    # Simulate CrewAI agent (placeholder)
    class MockCrewAgent:
        def process(self, message):
            return f"CrewAI agent processed: {message}"
    
    # Create a simple adapter for CrewAI (placeholder)
    class MockCrewAdapter(AgentProtocol):
        def __init__(self, agent, agent_id=None, name=None, metadata=None):
            super().__init__(
                agent=agent,
                agent_id=agent_id,
                name=name or "Crew Agent",
                framework="crew",
                capabilities=[],
                metadata=metadata or {}
            )
        
        async def process_action(self, request):
            result = self.agent.process(request.message)
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=result,
                role=MessageRole.AGENT,
                metadata=request.metadata
            )
    
    crew_adapter = MockCrewAdapter(
        agent=MockCrewAgent(),
        name="CrewAI Agent",
        metadata={"framework": "crew"}
    )
    
    # Create MCP servers for each agent
    agno_mcp_server = create_mcp_server(
        agent_protocol=agno_adapter,
        transport_type="stdio"
    )
    
    crew_mcp_server = create_mcp_server(
        agent_protocol=crew_adapter,
        transport_type="stdio"
    )
    
    # Create MCP clients to connect to each server
    # In a real implementation, these would connect to the actual servers
    agno_mcp_client = create_mcp_client(
        transport_type="stdio",
        name="Agno MCP Client"
    )
    
    crew_mcp_client = create_mcp_client(
        transport_type="stdio",
        name="Crew MCP Client"
    )
    
    try:
        # Simulate message passing between agents via MCP
        logger.info("Simulating message passing between agents via MCP...")
        
        # Create a message to start the chain
        initial_message = "Analyze this data and provide insights"
        
        # In a real implementation, we would:
        # 1. Send the message to Agno agent via MCP
        # agno_request = ActionRequest(
        #     agent_id=agno_mcp_client.agent_id,
        #     session_id=str(uuid.uuid4()),
        #     message=initial_message,
        #     role=MessageRole.USER,
        #     metadata={}
        # )
        # agno_response = await agno_mcp_client.process_action(agno_request)
        
        # 2. Take Agno's response and send to CrewAI agent
        # crew_request = ActionRequest(
        #     agent_id=crew_mcp_client.agent_id,
        #     session_id=str(uuid.uuid4()),
        #     message=agno_response.message,
        #     role=MessageRole.USER,
        #     metadata={}
        # )
        # crew_response = await crew_mcp_client.process_action(crew_request)
        
        # 3. Output the final result
        # logger.info(f"Final response from agent chain: {crew_response.message}")
        
        logger.info("MCP bridge example completed")
        
    except Exception as e:
        logger.error(f"Error in MCP bridge example: {e}")


async def main():
    """Run all MCP examples."""
    logger.info("Starting MCP integration examples")
    
    await example_mcp_client()
    await example_mcp_server()
    await example_mcp_cognitive()
    await example_mcp_bridge()
    
    logger.info("All MCP examples completed")


if __name__ == "__main__":
    asyncio.run(main())
