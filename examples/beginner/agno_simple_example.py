"""Research Assistant Agent

A Bindu agent that finds and summarizes information.
Uses DuckDuckGo for web search capabilities.

Features:
- Web search integration
- Information summarization
- Research assistance

Usage:
    python agno_simple_example.py

Environment:
    Requires OPENROUTER_API_KEY in .env file
"""

import os
from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openrouter import OpenRouter

from dotenv import load_dotenv

load_dotenv()

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenRouter(id="openai/gpt-5-mini", api_key=os.getenv("OPENROUTER_API_KEY")),
    tools=[DuckDuckGoTools()],
)


# Configuration
# Note: Infrastructure configs (storage, scheduler, sentry, API keys) are now
# automatically loaded from environment variables. See .env.example for details.
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": os.getenv(
        "BINDU_COMMS_URL",
        "http://127.0.0.1:3787/webhooks/bindu/agno-simple",
    ),
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}


# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=MessageConverter.to_chat_format(messages))
    return result


# Bindu-fy it
if __name__ == "__main__":
    # Disable auth for local development - frontend can connect without OAuth
    import os
    #os.environ["AUTH_ENABLED"] = "false"
    bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
