"""
Bindu Agent Handler Examples - User Control Patterns.

The bindufy function takes three arguments:
1. agent: The agent instance (created once, reused for all requests)
2. config: Configuration dictionary
3. handler: Function that processes messages using the agent

Benefits:
- Agent is instantiated once, not per request
- Clear separation of concerns
- Easy to test handlers independently
- Can swap agents or configs without changing handler logic
- Framework agnostic (works with Agno, LangChain, custom agents).
"""

import json
import os
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

# Load environment variables from .env file
load_dotenv()


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
    model=OpenAIChat(id="gpt-4o"),
)

# Define the handler function that uses the agent
def simple_handler(messages: list[dict[str, str]]) -> Any:
    """Handle agent messages in a stateless manner.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
                  e.g., [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Returns:
        Agent result in any format - ManifestWorker will intelligently extract the response.
        Can return:
        - Raw agent output (list of Messages, Message object, etc.)
        - Pre-extracted string
        - Structured dict with {"state": "input-required", ...}

    A2A Protocol: Each message creates a new task.
    Context continuity maintained via contextId and referenceTaskIds.
    """
    # Return raw result - let ManifestWorker's _normalize_result() handle extraction
    result = simple_agent.run(input=messages)
    return result


# bindufy the simple agent
bindufy(simple_agent, simple_config, simple_handler)
