#!/usr/bin/env python
"""
Deploy Agno Agent Example

This example demonstrates how to deploy an Agno agent using the pebblify module with
protocol system integration. The agent will be deployed locally and accessible via
API endpoints, with proper agent_id and session_id handling provided by the protocol.
"""

# Import Agno agent
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType

# Import pebblify module
from pebble import pebblify

# Import protocol system components for direct access (optional)
from pebble.protocol.protocol import Protocol
from pebble.protocol.coordinator import ProtocolCoordinator

def main():
    # Initialize Agno agent
    # You can customize the agent with your desired parameters
    agent = AgnoAgent(
        name="Thai Cuisine Expert",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a Thai cuisine expert!",
        instructions=[
            "Search your knowledge base for Thai recipes.",
            "If the question is better suited for the web, search the web to fill in gaps.",
            "Prefer the information in your knowledge base over the web results."
        ],
        knowledge=PDFUrlKnowledgeBase(
            urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
            vector_db=LanceDb(
                uri="tmp/lancedb",
                table_name="recipes",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
            ),
        ),
        tools=[DuckDuckGoTools()],
        show_tool_calls=True,
        markdown=True
        # No agent_id or session_id needed - the protocol system will handle these
    )

    # Optional: You can also access the protocol coordinator directly
    # This is useful for advanced use cases like multi-agent systems
    coordinator = ProtocolCoordinator()
    
    # You can inspect the default protocol
    protocol = Protocol()
    print(f"Using protocol version: {getattr(protocol, 'version', 'default')}")

    print("Deploying Agno agent with protocol-integrated pebblify...")
    
    # Deploy the agent
    # The agent will be automatically registered with the protocol system
    # which will handle agent_id and session_id management
    # By default, it will be deployed on localhost:8000
    # You can access the API documentation at http://localhost:8000/docs
    pebblify.deploy(agent)
    
    print("\nOnce the server is running, try these endpoints:")
    print("- GET /agent/status: Check the agent's status including protocol info")
    print("- POST /agent/action: Send a message to the agent")
    print("- GET /docs: Full API documentation")

if __name__ == "__main__":
    main()
