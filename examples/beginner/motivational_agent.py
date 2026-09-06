"""Motivational Coach Agent

A Bindu agent that provides motivation, encouragement, and positive inspiration.
Helps users stay motivated, overcome challenges, and achieve their goals.

Features:
- Daily motivation and positive affirmations
- Goal setting and achievement strategies
- Overcoming procrastination and self-doubt
- Web search for inspirational content and success stories
- OpenRouter integration with gpt-oss-120b

Usage:
    python motivational_agent.py

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
        "You are a motivational coach and personal development guide. "
        "Your job is to inspire, encourage, and motivate users to achieve their goals. "
        "Provide positive affirmations, practical advice for overcoming challenges, "
        "strategies for success, and help users build confidence and resilience. "
        "Be empathetic, supportive, and uplifting while maintaining a professional tone. "
        "Draw inspiration from successful people, psychology, and proven motivational techniques. "
        "When users face specific challenges, provide actionable steps and encouragement."
    ),
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    tools=[DuckDuckGoTools()],  # optional: for inspirational quotes and success stories
)


# Configuration
# Note: Infrastructure configs (storage, scheduler, sentry, API keys) are now
# automatically loaded from environment variables. See .env.example for details.
config = {
    "author": "jerphinasmi24@gmail.com",
    "name": "motivational_agent",
    "description": "A motivational coach agent for personal development and goal achievement",
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
