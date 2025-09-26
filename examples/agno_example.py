"""
Example: Using the new pebblify API style
=========================================

The new pebblify function takes three arguments:
1. agent: The agent instance (created once, reused for all requests)
2. config: Configuration dictionary
3. handler: Function that processes messages using the agent

Benefits:
- Agent is instantiated once, not per request
- Clear separation of concerns
- Easy to test handlers independently
- Can swap agents or configs without changing handler logic
"""

from typing import Dict, Any, List
import json
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pebbling.penguin import pebblify
from pebbling.common.models import DeploymentConfig, SchedulerConfig, StorageConfig
from pebbling.common.protocol.types import AgentCapabilities, AgentSkill

# Load configuration
def load_config(config_path: str):
    """Load configuration from JSON with defaults."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, config_path)
    with open(full_path, "r") as f:
        return json.load(f)

simple_config = load_config("simple_agent_config.json")

# 1. SIMPLE STATELESS AGENT - Direct response
# Create the agent instance once
simple_agent = Agent(
    instructions="Provide helpful responses to user messages",
    model=OpenAIChat(id="gpt-4o")
)

# Define the handler function that uses the agent
def simple_handler(messages: str) -> str:
    """Simple stateless agent handler - sees current message.
    
    A2A Protocol: Each message creates a new task.
    Context continuity maintained via contextId and referenceTaskIds.
    """
    result = simple_agent.run(input=messages)
    return result.to_dict()["content"]


# Convert the loaded config to match the new pebblify API
config_dict = {
    "author": simple_config["author"],
    "name": simple_config.get("name", "simple-agent"),
    "description": simple_config.get("description", "A helpful assistant"),
    "version": simple_config.get("version", "1.0.0"),
    "recreate_keys": simple_config.get("recreate_keys", True),
    "skills": simple_config.get("skills", []),
    "capabilities": simple_config["capabilities"],
    "agent_trust": simple_config.get("agent_trust"),
    "kind": simple_config.get("kind", "agent"),
    "debug_mode": simple_config.get("debug_mode", False),
    "debug_level": simple_config.get("debug_level", 1),
    "monitoring": simple_config.get("monitoring", False),
    "telemetry": simple_config.get("telemetry", True),
    "num_history_sessions": simple_config.get("num_history_sessions", 10),
    "documentation_url": simple_config.get("documentation_url"),
    "extra_metadata": simple_config.get("extra_metadata", {}),
    "deployment": simple_config["deployment"],
    "storage": simple_config["storage"],
    "scheduler": simple_config["scheduler"],
}

# Pebblify the simple agent
manifest = pebblify(simple_agent, config_dict, simple_handler)


