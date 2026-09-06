"""Zero-Configuration Beginner Agent

A minimal Bindu agent for first-time users.
No external dependencies - perfect for learning Bindu basics.

Features:
- Zero configuration required
- Simple, friendly responses
- Web search capability
- OpenRouter integration with gpt-oss-120b

Usage:
    python beginner_zero_config_agent.py

Environment:
    Requires OPENROUTER_API_KEY in .env file
"""

import os
from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


agent = Agent(
    instructions="You are a friendly assistant that explains things simply.",
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    tools=[DuckDuckGoTools()],
)

config = {
    "author": "21uad051@kamarajengg.edu.in",
    "name": "beginner_zero_config_agent",
    "description": "Zero-config local Bindu agent for first-time users",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}

def handler(messages):
    return agent.run(input=MessageConverter.to_chat_format(messages))

bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
