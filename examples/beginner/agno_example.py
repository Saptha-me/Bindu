"""Joke Telling Entertainment Agent

A Bindu agent that tells jokes and entertains users.
Provides witty, clean humor with customizable topics.

Features:
- Puns, dad jokes, tech jokes, situational humor
- Topic-specific joke generation
- Web search for trending content
- OpenRouter integration with gpt-oss-120b

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
    instructions=(
        "You are a witty joke-telling agent. "
        "Your job is to entertain users with clever, clean, and funny jokes. "
        "You can tell puns, dad jokes, tech jokes, and situational humor. "
        "Keep the tone light, playful, and human-like. "
        "If a topic is given, tailor the joke to that topic."
    ),
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    tools=[DuckDuckGoTools()],  # optional: for topical or trending jokes
)


# Configuration
# Note: Infrastructure configs (storage, scheduler, sentry, API keys) are now
# automatically loaded from environment variables. See .env.example for details.
config = {
    "author": "raahul.dutta@example.com",
    "name": "joke_agent",
    "description": "A research assistant agent",
    "deployment": {
            "url": "http://localhost:3773",
            "expose": True,
            "cors_origins": ["http://localhost:5173"]
        },
    "skills": ["skills/question-answering", "skills/pdf-processing"],
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
bindufy(config, handler)
