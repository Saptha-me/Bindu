import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pydantic.types import SecretStr

from pebbling.agent import pebblify
from pebbling.protocol.types import AgentCapabilities, AgentManifest, AgentSkill
from pebbling.utils.logging import configure_logger, get_logger

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
    agent_instance = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="You are a news reporter with a flair for storytelling.",
        markdown=True
    )
    
    # Return a proper AgentManifest with all metadata
    return AgentManifest(
        id="news-reporter",
        name="News Reporter",
        description="You are a news reporter with a flair for storytelling.",
        user_id="default-user",
        instance=agent_instance,
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

if __name__ == "__main__":
    try:
        news_reporter()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")