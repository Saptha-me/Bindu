"""Example of creating a research assistant agent using Bindu and Agno.

This example demonstrates how to create a simple research assistant agent
that uses DuckDuckGo for web searches and can be deployed as a Bindu agent.
"""

import os
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Load environment variables from .env file
load_dotenv()

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    "auth": {
        "enabled": True,
        "provider": "auth0",
        "domain": "dev-tlzrol0zsxw40ujx.us.auth0.com",
        "audience": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/",
        "algorithms": ["RS256"],
        "issuer": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/",
        "jwks_uri": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/.well-known/jwks.json",
        "require_permissions": True,
        "public_endpoints": [
            "/health",
            "/docs",
            "/.well-known/*",
            "/did/resolve*",
            "/agent/skills",
            "/agent/skills/*",
            "/static/*",
            "/api/start-payment-session",
            "/payment-capture*",
            "/api/payment-status/*",
        ],
        "permissions": {
            "message/send": ["agent:write"],
            "tasks/get": ["agent:read"],
            "tasks/cancel": ["agent:write"],
            "tasks/list": ["agent:read"],
            "contexts/list": ["agent:read"],
            "tasks/feedback": ["agent:write"],
        },
    },
    "execution_cost": {
        "amount": "$0.0001",
        "token": "USDC",
        "network": "base-sepolia",
        "pay_to_address": "0x2654bb8B272f117c514aAc3d4032B1795366BA5d",
        "protected_methods": ["message/send"],
    },
    "negotiation": {
        "embedding_api_key": os.getenv("OPENROUTER_API_KEY"),  # Load from environment
    },
}


# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result


# Bindu-fy it
bindufy(config, handler)
