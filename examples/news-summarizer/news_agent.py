"""
News Summarizer Agent

A Bindu agent that searches and summarizes latest news on any topic.
Runs locally via Ollama - no API key required!

Features:
- Real-time web search using DuckDuckGo
- Local LLM via Ollama
- Works for any topic: sports, tech, finance, politics etc..

Usage:
    python news_agent.py

"""

import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.duckduckgo import DuckDuckGoTools
from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter

load_dotenv()

# Agent Brain
agent = Agent(
    instructions=(
        "You are a news research assistant. "
        "When given a topic, search for the latest news about it. "
        "Return a structured summary with: "
        "1. Top 3 headlines "
        "2. Brief summary of each "
        "3. Overall sentiment (positive/negative/neutral)"
    ),
    model=Ollama(id="llama3.2"),
    tools=[DuckDuckGoTools()],
)

# Bindu Config
config = {
    "author": "SSJ.shabdsnehi08@gmail.com",
    "name": "news_summarizer_agent",
    "description": "Searches and summarizes latest news on any topic using local Ollama",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": [],
}

# Handler
def handler(messages: list[dict[str, str]]):
    """Process incoming messages and return news summary.

    Args:
        messages: Conversation history as raw A2A messages, e.g.
                  [{"role": "user", "parts": [{"kind": "text", "text": "cricket news"}], ...}]

    Returns:
        Agent response with structured news summary
    """
    result = agent.run(input=MessageConverter.to_chat_format(messages))
    return result

# Launch
if __name__ == "__main__":
    os.environ["AUTH_ENABLED"] = "false"
    bindufy(config, handler)
