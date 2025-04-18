from textwrap import dedent
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from pebble.core.protocol import ProtocolMethod
from pebble.server.pebble_server import pebblify


# Create an Agno agent
agno_agent = Agent(
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

# You can test the agent directly without pebblifying
#agno_agent.print_response("Tell me about a breaking news story from New York.", stream=True)

# Alternatively, pebblify the agent to enable JSON-RPC and REST API communication
if __name__ == "__main__":
    print("Starting pebblified Agno agent...")
    # Wrap the agent with Pebble protocol capabilities
    pebblify(
        agent=agno_agent,
        agent_id="news-reporter-agent",  # Optional custom ID for the agent
        supported_methods=[  # List of supported protocols
            ProtocolMethod.CONTEXT  # Added Context protocol support
        ],
        pebble_port=3773,  # Port for the JSON-RPC server to communicate with other agents
        user_port=3774,  # Port for the REST API to communicate with users
        host="0.0.0.0",  # Host to bind the servers to
        protocol_config_path="./protocol_config.json"  # Path to protocol config
    )
    # Note: The pebblify function starts the servers and blocks until they are stopped with Ctrl+C