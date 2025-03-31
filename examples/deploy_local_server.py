#!/usr/bin/env python
"""
Deploy Local Server Example

This example demonstrates how to deploy an Agno agent as a local API server.
"""
import os
import sys
import pathlib

# Add parent directory to path to allow importing from utils
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# Import Agno agent components
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.tools.web import WebSearchTools

# Import pebble components
from pebble import pebblify
from pebble.schemas.models import DeploymentConfig, DeploymentMode

def main():
    """Run the example."""
    # Create an Agno agent
    model = OpenAIChat(model="gpt-4")
    
    agent = AgnoAgent(
        name="Local Web Search Agent",
        model=model,
        tools=[WebSearchTools()],
        description="A helpful agent that can search the web.",
        instructions="You are a helpful agent that can search the web to find information."
    )
    
    # Configure the deployment
    config = DeploymentConfig(
        host="0.0.0.0",
        port=8000,
        cors_origins=["*"],
        enable_docs=True,
        require_auth=True,
        mode=DeploymentMode.LOCAL,
        log_level="INFO"
    )
    
    # Deploy the agent
    print(f"Deploying agent '{agent.name}' as a local API server...")
    adapters = pebblify(
        agent=agent,
        name="WebSearchAgent",
        config=config,
        autostart=True
    )
    
    print(f"Agent deployed successfully!")
    print(f"API server is running at http://localhost:8000")
    print(f"Documentation available at http://localhost:8000/docs")

if __name__ == "__main__":
    main()