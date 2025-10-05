"""
The pebblify function takes three arguments:
1. agent: The agent instance (created once, reused for all requests)
2. config: Configuration dictionary
3. handler: Function that processes messages using the agent

Benefits:
- Agent is instantiated once, not per request
- Clear separation of concerns
- Easy to test handlers independently
- Can swap agents or configs without changing handler logic
"""

import json
import os
import sys

# Add parent directory to path so we can import pebbling
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pebbling.penguin.pebblify import pebblify

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


# Pebblify the simple agent
pebblify(simple_agent, simple_config, simple_handler)


