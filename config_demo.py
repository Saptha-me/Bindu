"""
Example: Using ConfigValidator to avoid duplication
===================================================

This shows how to use the ConfigValidator to simplify config handling.
"""

from typing import Dict, Any
import json
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from bindu.penguin import pebblify
from bindu.penguin.config_validator import ConfigValidator, load_and_validate_config

# Option 1: Load and validate in one step
config_dict = load_and_validate_config("simple_agent_config.json")

# Option 2: Validate existing config
# simple_config = json.load(open("simple_agent_config.json"))
# config_dict = ConfigValidator.create_pebblify_config(simple_config)


# Create agents
simple_agent = Agent(
    instructions="Provide helpful responses to user messages",
    model=OpenAIChat(id="gpt-4o")
)

def simple_handler(messages: str) -> str:
    """Simple agent handler."""
    result = simple_agent.run(input=messages)
    return result.to_dict()["content"]

# Use with pebblify - no more manual config building!
manifest = pebblify(
    agent=simple_agent,
    config=config_dict,
    handler=simple_handler
)


# BENEFITS:
# =========
# 1. No more manual field extraction
# 2. Automatic validation of required fields
# 3. Type checking for all fields
# 4. Consistent default values
# 5. Better error messages for missing/invalid config
# 6. Reusable across all agents

if __name__ == "__main__":
    print("Config Validator Demo")
    print("====================")
    print()
    print("OLD WAY: 22 lines of repetitive config extraction")
    print("NEW WAY: 1 line with validation!")
    print()
    print("The ConfigValidator provides:")
    print("- Automatic default values")
    print("- Required field validation")
    print("- Type checking")
    print("- Better error messages")
    print()
    
    # Example of validation errors
    try:
        # Missing required field
        bad_config = {"name": "test"}
        ConfigValidator.validate_and_process(bad_config)
    except ValueError as e:
        print(f"Validation error example: {e}")
