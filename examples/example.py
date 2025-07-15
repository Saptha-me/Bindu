"""
News Reporter Agent Example.

This example demonstrates how to create an Agno agent with a news reporter personality
and integrate it with pebbling's protocol framework for JSON-RPC and REST API communication.
"""

from textwrap import dedent

# Agno imports
from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat

# pebbling imports
from pebbling.core.protocol import CoreProtocolMethod
# from pebbling.server.pebbling_server import pebblify
from pebbling.security.did.decorators import with_did

localhost: str = "127.0.0.1"

@with_did(key_path="keys/news_reporter_key.json", endpoint="https://pebbling-agent.example.com/pebble")
def news_reporter_agent():
    return Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=dedent(
            """\
            You are an enthusiastic news reporter with a flair for storytelling.
            """
        ),
        markdown=True,
    )

supported_methods = [
    CoreProtocolMethod.CONTEXT,
    CoreProtocolMethod.LISTEN,
    CoreProtocolMethod.ACT,
]

agent = news_reporter_agent()
    
print(f"Agent DID: {agent.pebble_did}")
print(f"DID Document: {agent.pebble_did_document}")