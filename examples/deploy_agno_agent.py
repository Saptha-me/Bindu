#!/usr/bin/env python
"""
Deploy Agno Agent Example

This example demonstrates how to deploy an Agno agent using Pebble with full configuration.
"""
import os
import sys
import logging
import pathlib

# Add parent directory to path to allow importing from utils
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# Import Agno agent components
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.tools.web import WebSearchTools
from agno.tools.image import ImageProcessingTools

# Import pebble components
from pebble import pebblify
from pebble.schemas.models import (
    DeploymentConfig, 
    DeploymentMode, 
    RouterRegistration,
    DockerConfig
)
from pebble.logging.config import configure_logging

def create_agent():
    """Create an Agno agent with web search and image processing tools."""
    # Configure the model
    model = OpenAIChat(model="gpt-4-vision-preview")
    
    # Create the agent with web search and image capabilities
    agent = AgnoAgent(
        name="MulticapabilityAgent",
        model=model,
        tools=[WebSearchTools(), ImageProcessingTools()],
        description="An agent that can search the web and process images.",
        instructions=(
            "You are a helpful assistant that can search the web for information "
            "and analyze images when they are provided."
        )
    )
    
    return agent

def local_deployment(agent):
    """Deploy the agent locally."""
    # Configure local deployment
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
    print("Deploying agent locally...")
    adapters = pebblify(
        agent=agent,
        name="MultiCapabilityAgent",
        config=config,
        autostart=True
    )
    
    print("Agent deployed successfully!")
    print("API server is running at http://localhost:8000")
    print("Documentation available at http://localhost:8000/docs")
    
    return adapters

def router_deployment(agent):
    """Deploy the agent and register with a router."""
    # Get the router API key from environment
    api_key = os.environ.get("ROUTER_API_KEY")
    if not api_key:
        print("Warning: ROUTER_API_KEY environment variable not set.")
        api_key = "demo_key"  # Use a placeholder key
    
    # Configure router registration
    router_config = RouterRegistration(
        router_url="https://router.example.com",
        api_key=api_key,
        description="Web search and image processing agent",
        tags=["search", "web", "image", "vision"]
    )
    
    # Configure deployment
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
    print("Deploying agent and registering with router...")
    registration_url = pebblify(
        agent=agent,
        name="MultiCapabilityAgent",
        config=config
    )
    
    print("Agent deployed and registered successfully!")
    print(f"Agent can be accessed via: {registration_url}")
    
    return registration_url

def docker_deployment(agent):
    """Create Docker deployment artifacts for the agent."""
    # Configure Docker deployment
    docker_config = DockerConfig(
        base_image="python:3.10-slim",
        output_dir="./docker_deploy",
        include_requirements=True,
        expose_port=8000,
        environment_vars={
            "OPENAI_API_KEY": "${OPENAI_API_KEY}",  # Pass through from host environment
            "LOG_LEVEL": "INFO",
            "AUTH_ENABLED": "true"
        }
    )
    
    # Configure deployment
    config = DeploymentConfig(
        mode=DeploymentMode.DOCKER,
        docker_config=docker_config
    )
    
    # Create Docker deployment artifacts
    print("Creating Docker deployment artifacts...")
    docker_path = pebblify(
        agent=agent,
        name="MultiCapabilityAgent",
        config=config
    )
    
    print("Docker deployment artifacts created successfully!")
    print(f"Docker artifacts created at: {docker_path}")
    print("To build and run the Docker container:")
    print(f"  cd {docker_path}")
    print(f"  docker-compose up --build")
    
    return docker_path

def main():
    """Run the example with the deployment mode specified by command-line argument."""
    # Configure logging
    configure_logging(log_level="INFO", log_format="json")
    
    # Create the agent
    agent = create_agent()
    
    # Get deployment mode from command line argument, default to "local"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "local"
    
    # Deploy according to specified mode
    if mode == "local":
        local_deployment(agent)
    elif mode == "router":
        router_deployment(agent)
    elif mode == "docker":
        docker_deployment(agent)
    else:
        print(f"Unknown deployment mode: {mode}")
        print("Valid modes are: local, router, docker")
        sys.exit(1)

if __name__ == "__main__":
    main()