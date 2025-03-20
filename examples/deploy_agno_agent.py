#!/usr/bin/env python
"""
Deploy Authenticated Agno Agent Example

This example demonstrates how to deploy an Agno agent using the pebblify module with
protocol system integration and proper authentication. The agent will be deployed locally
and accessible via API endpoints with token-based authentication secured with an .env file.
"""

import sys
import pathlib
from typing import Dict, Any

# Add parent directory to path to allow importing from utils
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from utils.manage_secrets import ensure_env_file

# Import Agno agent components
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

# Import pebble components
from pebble import deploy
from pebble.schemas.models import DeploymentConfig
from pebble.security.keys import get_secret_key, rotate_key_with_awk


def main():
    # Ensure .env file exists with SECRET_KEY
    ensure_env_file()
    
    # Optional: Rotate the SECRET_KEY for enhanced security using awk command
    # Uncomment to rotate on each deployment
    # rotate_key_with_awk()
    
    # Get the current secret key (first 10 chars for logging only)
    secret_key = get_secret_key()
    print(f"Using SECRET_KEY from .env file (first 10 chars): {secret_key[:10]}...")
    
    # Initialize a simple Agno agent
    agent = AgnoAgent(
        name="Customer Support Assistant",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a helpful customer support assistant for a software company.",
        instructions=[
            "Be concise and professional.",
            "If you don't know an answer, acknowledge it.",
            "Make use of your tools when appropriate.",
            "Focus on providing actionable solutions."
        ],
        tools=[DuckDuckGoTools()],
        show_tool_calls=True,
        markdown=True
    )
    
    # Configure deployment settings
    # This shows all available options with their default values
    config = DeploymentConfig(
        host="0.0.0.0",         # Host to bind to
        port=8000,              # Port to listen on
        cors_origins=["*"],     # CORS allowed origins
        enable_docs=True,       # Enable Swagger docs at /docs
        require_auth=True,      # Require authentication
        access_token_expire_minutes=30,  # Token expiration time
        api_key_expire_days=365  # API key expiration time
    )
    
    print("Deploying Agno agent with protocol-integrated pebblify and authentication...")
    
    # Deploy the agent with configuration
    # You can pass either the raw agent or the adapted agent
    deploy(
        agent=agent,
        host=config.host,
        port=config.port,
        cors_origins=config.cors_origins,
        enable_docs=config.enable_docs,
        require_auth=config.require_auth
    )
    
    print("\nOnce the server is running, try these endpoints:")
    print("- GET /agent/status: Check the agent's status (requires authentication)")
    print("- POST /agent/action: Send a message to the agent (requires authentication)")
    print("- GET /docs: Full API documentation")
    print("\nAuthentication:")
    print("- The API key will be shown in the server logs when starting")
    print("- Add header 'X-API-Key: <your-api-key>' to your requests")
    print("- Or use Bearer authentication with 'Authorization: Bearer <your-api-key>'")
    
    print("\nExample curl command to check status:")
    print("curl -H 'X-API-Key: <your-api-key>' http://localhost:8000/agent/status")
    
    print("\nExample curl command to send a message:")
    print("""curl -X POST -H 'Content-Type: application/json' \\
    -H 'X-API-Key: <your-api-key>' \\
    -d '{"agent_id": "<agent-id-from-status>", "message": "How can you help me?"}' \\
    http://localhost:8000/agent/action""")


if __name__ == "__main__":
    main()
