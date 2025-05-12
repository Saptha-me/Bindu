"""
News Reporter Agent Example

This example demonstrates how to create an Agno agent with a news reporter personality
and integrate it with pebbling's protocol framework for JSON-RPC and REST API communication.
"""
from textwrap import dedent
from typing import List, Optional
from loguru import logger

# Agno imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# pebbling imports
from pebbling.core.protocol import ProtocolMethod
from pebbling.server.pebbling_server import pebblify

news_reporter_agent = Agent(
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

supported_methods = [
    ProtocolMethod.CONTEXT,
    ProtocolMethod.LISTEN,
    ProtocolMethod.ACT,
]

# Wrap the agent with pebbling protocol capabilities
pebblify(
    agent=news_reporter_agent,
    supported_methods=supported_methods,
    pebbling_port=3773,
    user_port=3774,
    host="0.0.0.0",
    protocol_config_path="./protocol_config.json",
)



#registrer to hibiscus