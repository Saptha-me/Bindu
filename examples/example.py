import json
import os
from typing import AsyncGenerator, List


from pebbling.common.protocol.types import AgentCapabilities, AgentSkill
from pebbling.penguin.pebblify import pebblify
from pebbling.common.models import DeploymentConfig

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
    name=config.get("name"),
    description=config.get("description"),
    version=config.get("version", "1.0.0"),
    recreate_keys=config.get("recreate_keys", True),
    skills=[AgentSkill(**skill) for skill in config.get("skills", [])],
    capabilities=AgentCapabilities(**config["capabilities"]),
    agent_trust=config.get("agent_trust"),
    kind=config.get("kind", "agent"),
    debug_mode=config.get("debug_mode", False),
    debug_level=config.get("debug_level", 1),
    monitoring=config.get("monitoring", False),
    telemetry=config.get("telemetry", True),
    num_history_sessions=config.get("num_history_sessions", 10),
    documentation_url=config.get("documentation_url"),
    extra_metadata=config.get("extra_metadata", {}),
    deployment_config=DeploymentConfig(**config["deployment"]),
)
async def news_reporter_agent(messages: List[str]) -> AsyncGenerator[str, None]:
    """User writes protocol-compliant code directly."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Get current news from amsterdam",
        model=OpenAIChat(id="gpt-4o")
    )
    result = await agent.arun(messages=messages)
    
    # Yield protocol-compliant response
    yield result.to_dict()['content']