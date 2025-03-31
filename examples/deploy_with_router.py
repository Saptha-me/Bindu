#!/usr/bin/env python
"""
Deploy with Router Example

This example demonstrates how to deploy an Agno agent and register it with a router service.
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
from pebble.schemas.models import DeploymentConfig, DeploymentMode, RouterRegistration

def main():
    """Run the example."""
    # Create an Agno agent
    model = OpenAIChat(model="gpt-4")
    
    agent = AgnoAgent(
        name="Web Search Agent",
        model=model,
        tools=[WebSearchTools()],
        description="A helpful agent that can search the web.",
        instructions="You are a helpful agent that can search the web to find information."
    )
    
    # Configure the router registration
    router_config = RouterRegistration(
        router_url="https://router.example.com",
        api_key=os.environ.get("ROUTER_API_KEY"),
        description="Web search capability with Agno",
        tags=["search", "web", "agno"]
    )
    
    # Configure the deployment
    config = DeploymentConfig(
        host="0.0.0.0",
        port=8000,
        cors_origins=["*"],
        enable_docs=True,
        require_auth=True,
        mode=DeploymentMode.REGISTER,
        log_level="INFO",
        router_config=router_config
    )
    
    # Deploy the agent and register with router
    print(f"Deploying agent '{agent.name}' and registering with router...")
    registration_url = pebblify(
        agent=agent,
        name="WebSearchAgent",
        config=config
    )
    
    print(f"Agent deployed and registered successfully!")
    print(f"Agent can be accessed via: {registration_url}")

if __name__ == "__main__":
    main()