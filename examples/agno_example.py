"""
News Reporter Agent Example

This example demonstrates how to create an Agno agent with a news reporter personality
and integrate it with Pebble's protocol framework for JSON-RPC and REST API communication.
"""
from textwrap import dedent
from typing import List, Optional
from loguru import logger

# Agno imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Pebble imports
from pebble.core.protocol import ProtocolMethod
from pebble.server.pebble_server import pebblify


def create_news_reporter_agent() -> Agent:
    """
    Create an Agno agent with a news reporter personality.
    
    Returns:
        Agent: Configured Agno agent instance
    """
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=dedent("""\
            You are an enthusiastic news reporter with a flair for storytelling! 🗽
            Think of yourself as a mix between a witty comedian and a sharp journalist.

            Your style guide:
            - Start with an attention-grabbing headline using emoji
            - Share news with enthusiasm and NYC attitude
            - Keep your responses concise but entertaining
            - Throw in local references and NYC slang when appropriate
            - End with a catchy sign-off like 'Back to you in the studio!' or 'Reporting live from the Big Apple!'

            Remember to verify all facts while keeping that NYC energy high!\
        """),
        markdown=True,
    )


def start_pebblified_agent(
    agent: Agent,
    agent_id: str = "news-reporter-agent",
    supported_methods: Optional[List[ProtocolMethod]] = None,
    pebble_port: int = 3773,
    user_port: int = 3774,
    host: str = "0.0.0.0",
    protocol_config_path: str = "./protocol_config.json"
) -> None:
    """
    Start a Pebble server with the provided agent.
    
    Args:
        agent: The agent to pebblify
        agent_id: Custom ID for the agent
        supported_methods: List of supported protocol methods
        pebble_port: Port for the JSON-RPC server to communicate with other agents
        user_port: Port for the REST API to communicate with users
        host: Host to bind the servers to
        protocol_config_path: Path to protocol config
    """
    if supported_methods is None:
        supported_methods = [ProtocolMethod.CONTEXT]
        
    logger.info(f"Starting pebblified agent with ID: {agent_id}")
    
    # Wrap the agent with Pebble protocol capabilities
    pebblify(
        agent=agent,
        agent_id=agent_id,
        supported_methods=supported_methods,
        pebble_port=pebble_port,
        user_port=user_port,
        host=host,
        protocol_config_path=protocol_config_path
    )
    # Note: The pebblify function starts the servers and blocks until they are stopped with Ctrl+C


def test_agent_directly(agent: Agent) -> None:
    """
    Test the agent directly without pebblifying it.
    
    Args:
        agent: The agent to test
    """
    logger.info("Testing agent directly...")
    print(agent.run("Tell me about a breaking news story from New York."))


def main() -> None:
    """Main function to create and start the news reporter agent."""
    # Create the news reporter agent
    logger.info("Creating news reporter agent...")
    agno_agent = create_news_reporter_agent()
    
    # Uncomment to test the agent directly
    # test_agent_directly(agno_agent)
    
    # Start the pebblified agent
    start_pebblified_agent(agent=agno_agent)


if __name__ == "__main__":
    main()