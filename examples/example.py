from pebbling.agent import pebblify
from pebbling.agent.runner import run_agent
from pebbling.protocol.types import AgentCapabilities, AgentSkill, AgentManifest
from pebbling.utils.logging import get_logger, configure_logger

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pydantic.types import SecretStr
import os

# Initialize logger first with proper configuration
configure_logger(docker_mode=False)  # Pass docker_mode=True if running in Docker
# Get a logger for this specific module
logger = get_logger("news_reporter_agent")

@pebblify(
    logger=logger,
    expose=True,
    agent_registry_pat_token=SecretStr(os.environ.get("HIBISCUS_PAT_TOKEN", "")),
    agent_registry_url="http://localhost:19191",  # Use configured Hibiscus URL
    store_in_registry=True  # Enable registry integration
)
def news_reporter() -> AgentManifest:
    """Create a news reporter agent with storytelling capabilities."""
    logger.debug("Creating news reporter agent")
    
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
        agent=agent,
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

def main() -> None:
    """Main entry point demonstrating agent execution."""
    try:
        logger.info("Initializing agent...")
        agent_manifest = news_reporter()
        
        # Show the DID information if available
        if agent_manifest.did:
            logger.info(f"Agent registered with DID: {agent_manifest.did}")
        
        # Access the agent directly from the manifest
        agent = agent_manifest.agent
        if not agent:
            logger.error("Agent not found in manifest")
            return
            
        # Generate a story
        logger.info("Generating story...")
        story = agent.generate("Write a short story about AI and its impact on society in 2025")
        
        # Display results
        print("\n===== GENERATED STORY =====")
        print(story)
        
        # Show metadata
        print("\n===== AGENT METADATA =====")
        print(f"Agent ID: {agent_manifest.agent_id}")
        print(f"Agent Name: {agent_manifest.name}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()