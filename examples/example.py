from pebbling.agent import pebblify
from pebbling.agent.runner import run_agent
from pebbling.protocol.types import AgentCapabilities, AgentSkill, AgentManifest
from pebbling.utils.logging import logger, configure_logger

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pydantic.types import SecretStr
import os
import asyncio

@pebblify(
    expose=True,
    agent_registry_pat_token=SecretStr(os.environ.get("HIBISCUS_PAT_TOKEN", "")),
    agent_registry_url="http://localhost:19191",  # Use configured Hibiscus URL
    store_in_registry=True  # Enable registry integration
)
def news_reporter() -> AgentManifest:
    """Create a news reporter agent with storytelling capabilities."""
    # Create the base agent for the core functionality
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="You are a news reporter with a flair for storytelling.",
        markdown=True
    )
    
    # Return a proper AgentManifest with all metadata
    return AgentManifest(
        agent_id="news-reporter",
        name="News Reporter",
        user_id="default-user",
        agent=agent,  # Add a field to store the actual agent
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True,
        ),
        skills=[
            AgentSkill(
                id="news-reporting",
                name="News Reporting",
                description="You are a news reporter with a flair for storytelling.",
                input_modes=["text"],
                output_modes=["text"],
                tags=["news", "reporting", "storytelling"],
                domains=["journalism", "creative-writing"]
            )
        ],
        version="1.0.0"
    )

def main():
    """Main entry point demonstrating agent execution with proper async handling."""
    try:
        # Get the agent manifest from the pebblify decorator
        logger.info("Initializing news reporter agent...")
        agent_manifest = news_reporter()
        
        # Show the DID information from the manifest
        if agent_manifest.did:
            logger.info(f"Agent registered with DID: {agent_manifest.did}")
            logger.info(f"DID document contains {len(agent_manifest.did_document or {})} fields")
        else:
            logger.warning("Agent manifest missing DID information")
        
        # Access the agent directly from the manifest
        agent = agent_manifest.agent
        if not agent:
            logger.error("Agent not found in manifest")
            return
            
        # Use the agent's generate method directly
        logger.info("Generating story...")
        story = agent.generate("Write a short story about AI and its impact on society in 2025")
        
        # Display the results
        print("\n===== GENERATED STORY =====")
        print(story)
        
        # Demonstrate how to access agent metadata
        print("\n===== AGENT METADATA =====")
        print(f"Agent ID: {agent_manifest.agent_id}")
        print(f"Agent Name: {agent_manifest.name}")
        print(f"Capabilities: {agent_manifest.capabilities}")
        print(f"Skills: {len(agent_manifest.skills or [])} skills configured")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    # Configure logging first
    configure_logger()
    
    # Run the main function
    main()