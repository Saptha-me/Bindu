from textwrap import dedent

# Agno imports
from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat

# pebbling imports
from pebbling.core.protocol import ProtocolMethod
from pebbling.server.server_security import SecurityMiddleware
from pebbling.server.pebbling_server import pebblify

localhost: str = "127.0.0.1"
port: int = 8000

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

supported_methods = [
    ProtocolMethod.CONTEXT,
    ProtocolMethod.ACT,
]

# Create a DID manager for secure agent communication
# This generates/loads private keys and creates DID documents
did_manager = DIDManager(key_path="./{{cookiecutter.project_slug}}_private_key.json")

# Wrap the agent with pebbling protocol capabilities
pebblify(
    agent=news_reporter_agent,
    supported_methods=supported_methods,
    pebbling_port=port,
    user_port=port + 1,
    host=localhost,
    protocol_config_path="./protocol_config.json",
    # Enable DID-based security for secure agent-to-agent communication
    did_manager=did_manager,
    enable_security=True,
    # Uncomment to register with a Hibiscus registry when available
    # register_with_hibiscus=True,
    # hibiscus_url="https://hibiscus.example.com",
)