"""MiniMax AI Research Agent

A Bindu agent powered by MiniMax's M3 model via OpenAI-compatible API.
MiniMax offers high-performance models with up to 1M context window.

Features:
- MiniMax M3 model (1M context)
- Web search integration via DuckDuckGo
- Research and summarization capabilities

Usage:
    python minimax_example.py

Environment:
    Requires MINIMAX_API_KEY in .env file
    Get your API key at https://platform.minimaxi.com
"""

import os
from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAILike

from dotenv import load_dotenv

load_dotenv()

# MiniMax API configuration
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"

# Define your agent with MiniMax M3
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAILike(
        id="MiniMax-M3",
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
    ),
    tools=[DuckDuckGoTools()],
)


# Configuration
config = {
    "author": "your.email@example.com",
    "name": "minimax_research_agent",
    "description": "A research assistant agent powered by MiniMax AI",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
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
    bindufy(config, handler)
