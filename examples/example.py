import json
import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from pydantic.types import SecretStr

from pebbling.common.protocol.types import AgentCapabilities, AgentSkill
from pebbling.penguin.pebblify import pebblify
from pebbling.common.models import (
    SecurityConfig, 
    DeploymentConfig
)

from agno.agent import Agent
from agno.models.openai import OpenAIChat



def load_config(config_path: str = "agent_config.json"):
    """Load configuration from JSON with defaults."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, config_path)
    
    with open(full_path, 'r') as f:
        config = json.load(f)
        print(f"Loaded config from {full_path}")
        return config

config = load_config()

@pebblify(
    author=config["author"],
    recreate_keys=config["recreate_keys"],
    skill=AgentSkill(**config["skill"]),
    capabilities=AgentCapabilities(**config["capabilities"]),
    deployment_config=DeploymentConfig(**config["deployment"]),
)
async def news_reporter_agent(
    input: str
) -> AsyncGenerator[str, None]:
    """User writes protocol-compliant code directly."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Get current news from amsterdam",
        model=OpenAIChat(id="gpt-4o"))
    result = await agent.arun(input)
    
    # Yield protocol-compliant response
    yield result