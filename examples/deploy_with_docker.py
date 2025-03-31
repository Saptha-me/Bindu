#!/usr/bin/env python
"""
Deploy with Docker Example

This example demonstrates how to create Docker deployment artifacts for an Agno agent.
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
from pebble.schemas.models import DeploymentConfig, DeploymentMode, DockerConfig

def main():
    """Run the example."""
    # Create an Agno agent
    model = OpenAIChat(model="gpt-4")
    
    agent = AgnoAgent(
        name="Docker Web Search Agent",
        model=model,
        tools=[WebSearchTools()],
        description="A helpful agent that can search the web.",
        instructions="You are a helpful agent that can search the web to find information."
    )
    
    # Configure the Docker deployment
    docker_config = DockerConfig(
        base_image="python:3.10-slim",
        output_dir="./docker_deploy",
        include_requirements=True,
        expose_port=8000,
        environment_vars={
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"  # Will be populated from host environment
        }
    )
    
    # Configure the deployment
    config = DeploymentConfig(
        mode=DeploymentMode.DOCKER,
        docker_config=docker_config
    )
    
    # Create Docker deployment artifacts
    print(f"Creating Docker deployment artifacts for agent '{agent.name}'...")
    docker_path = pebblify(
        agent=agent,
        name="WebSearchAgent",
        config=config
    )
    
    print(f"Docker deployment artifacts created successfully at: {docker_path}")
    print(f"To build and run the Docker container:")
    print(f"  cd {docker_path}")
    print(f"  docker-compose up --build")

if __name__ == "__main__":
    main()