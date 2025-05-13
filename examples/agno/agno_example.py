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
from pebbling.core.protocol import ProtocolMethod
from pebbling.server.pebbling_server import pebblify

localhost: str = "127.0.0.1"

news_reporter_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions=dedent(
        """\
        You are an enthusiastic news reporter with a flair for storytelling! 🗽
        Think of yourself as a mix between a witty comedian and a sharp journalist.

        Your style guide:
        - Start with an attention-grabbing headline using emoji
        - Share news with enthusiasm and NYC attitude
        - Keep your responses concise but entertaining
        - Throw in local references and NYC slang when appropriate
        - End with a catchy sign-off like 'Back to you in the studio!' or 'Reporting live from the Big Apple!'

        Remember to verify all facts while keeping that NYC energy high!\
        """
    ),
    markdown=True,
)

audio_agent = Agent(
    name="Audio Assistant",
    model=OpenAIChat(
        id="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "sage", "format": "wav"},
    ),
    description="Processes audio and generates intelligent responses.",
    instructions=["Be concise and professional.", "Use tools when relevant.", "Don’t fake answers."],
    markdown=True,
)

video_agent = Agent(
    name="Video Assistant",
    description="Process videos and generate engaging shorts.",
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
    debug_mode=True,
    instructions=dedent(
        """\
        - Analyze the provided video directly—do NOT reference or analyze any external sources or YouTube videos.
        - Identify engaging moments that meet the specified criteria for short-form content.
        - Provide your analysis in a **table format** with these columns:
          Start Time | End Time | Description | Importance Score
        - Ensure all timestamps use MM:SS format and importance scores range from 1-10.
        - Focus only on segments between 15 and 60 seconds long.
        - Base your analysis solely on the provided video content.
        - Deliver actionable insights to improve the identified segments for short-form optimization.
        """
    ),
)

supported_methods = [
    ProtocolMethod.CONTEXT,
    ProtocolMethod.LISTEN,
    ProtocolMethod.ACT,
]

# Wrap the agent with pebbling protocol capabilities
pebblify(
    agent=video_agent,
    supported_methods=supported_methods,
    pebbling_port=3773,
    user_port=3774,
    host=localhost,
    protocol_config_path="./protocol_config.json",
)
