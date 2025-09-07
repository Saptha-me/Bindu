import json
import os
from time import sleep
from typing import AsyncGenerator, Generator, List

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


# 1. ASYNC GENERATOR EXAMPLE - inspect.isasyncgenfunction()
@pebblify(
    author=config["author"],
    name="News Reporter Agent",
    description="Agent using async generator function",
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
    """Async generator function example - yields multiple results asynchronously."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Get current news from amsterdam",
        model=OpenAIChat(id="gpt-4o")
    )
    result = agent.run(messages=messages)
    
    # Yield protocol-compliant response
    yield result.to_dict()['content']


# 2. COROUTINE EXAMPLE - inspect.iscoroutinefunction()
@pebblify(
    author=config["author"],
    name="Weather Agent",
    description="Agent using coroutine function",
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
async def weather_agent(messages: List[str]):
    """Coroutine function example - manifest handles streaming automatically."""
    
    # User writes simple agent code - manifest handles streaming
    agent = Agent(
        instructions="Provide weather information for the requested location",
        model=OpenAIChat(id="gpt-4o")
    )
    
    # Await the agent result - this returns the streaming object
    result = await agent.arun(messages=messages, stream=True)
    
    # Return the streaming result - manifest will detect it's async iterable
    return result


# 3. GENERATOR EXAMPLE - inspect.isgeneratorfunction()
@pebblify(
    author=config["author"],
    name="Story Agent",
    description="Agent using generator function",
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
def story_agent(messages: List[str]) -> Generator[str, None, None]:
    """Generator function example - yields multiple results synchronously."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Create an engaging story based on the user's request, tell it in parts",
        model=OpenAIChat(id="gpt-4o")
    )
    
    # Simulate streaming response by yielding parts
    yield "Starting the story..."
    
    result = agent.run(messages=messages)
    content = result.to_dict()['content']

    yield content
    
    # Split content into parts and yield each
    sleep(2)
    
    yield "Story complete!"


# 4. REGULAR FUNCTION EXAMPLE - else case
@pebblify(
    author=config["author"],
    name="Simple Agent",
    description="Agent using regular function",
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
def simple_agent(messages: List[str]) -> str:
    """Regular function example - returns single result."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Provide a simple response to the user's message",
        model=OpenAIChat(id="gpt-4o")
    )
    
    result = agent.run(messages=messages)
    
    # Return single result
    return result.to_dict()['content']


if __name__ == "__main__":
    print("Agno Example - All Function Types")
    print("1. news_reporter_agent - Async Generator")
    print("2. weather_agent - Coroutine") 
    print("3. story_agent - Generator")
    print("4. simple_agent - Regular Function")
