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
from pebbling.server.pebbling_server import pebblify
from pebbling.security import with_did

localhost: str = "127.0.0.1"

# Apply the with_did decorator to enable DID-based security
# This automatically:
# 1. Generates an Ed25519 key pair (or loads if existing)
# 2. Creates a DID document for the agent
@with_did(key_path="keys/news_reporter_key.json", endpoint="https://pebbling-agent.example.com/pebble")
def news_reporter_agent():
    return Agent(
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

# After decorating with with_did, the returned agent will now have:
# - agent.did: The DID string (did:pebble:...)
# - agent.did_document: The complete DID Document
# - agent.did_manager: Instance of DIDManager for signing/verification

supported_methods = [
    CoreProtocolMethod.CONTEXT,
    CoreProtocolMethod.LISTEN,
    CoreProtocolMethod.ACT,
]

# Define an async main function
async def main():
    # Instantiate the agent
    agent = news_reporter_agent()
    
    print(f"Agent DID: {agent.pebble_did}")
    print(f"DID Document: {agent.pebble_did_document}")
    
    # Wrap the agent with pebbling protocol capabilities
    # Steps:
    # 1-2. DID generation already done by with_did decorator
    # 3. Register the agent's DID with Hibiscus
    # 4-7. CSR generation, JWT proof, and certificate issuance via Sheldon
    await pebblify(
        agent=agent,
        supported_methods=supported_methods,
        pebbling_port=3773,  # Using port 3774 instead of 3773 since 3773 is already in use
        user_port=3774,
        host=localhost,
        protocol_config_path="./protocol_config.json",
        # Security configuration
        did_manager=agent.pebble_did_manager,
        enable_security=True,  # Enable DID-based security
        enable_mtls=True,      # Enable mTLS with Sheldon certificates
        cert_path="keys/",
        # Hibiscus registration (Step 3)
        register_with_hibiscus=True,
        hibiscus_url="http://localhost:8000",  # Hibiscus registry
        hibiscus_api_key="pb_3ded3290d33ce7cecbcb549fc39a7805",
        # Sheldon CA configuration (Steps 5-7)
        sheldon_ca_url="http://localhost:19190",  # Sheldon CA service
        # Agent metadata
        agent_name="news-reporter",
        agent_description="An enthusiastic news reporter agent with a NYC flair",
        agent_capabilities=[
            {
                "name": "news-reporting",
                "description": "Can report news with a NYC attitude"
            },
            {
                "name": "storytelling",
                "description": "Creates engaging narratives with local color"
            }
        ],
        agent_domains=["news", "entertainment"],
        agent_tags=["news-reporter", "nyc-style", "storytelling"],
        agent_metadata={
            "framework": "Agno",
            "programming_language": "Python",
            "supported_languages": ["en"]
        },
        agent_author="Pebble Example"
    )

# Run the async main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())