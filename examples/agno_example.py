import json
import os
from typing import List

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from pebbling.common.models import DeploymentConfig, SchedulerConfig, StorageConfig
from pebbling.common.protocol.types import AgentCapabilities, AgentSkill
from pebbling.penguin.pebblify import pebblify


def load_config(config_path: str):
    """Load configuration from JSON with defaults."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, config_path)
    
    with open(full_path, 'r') as f:
        config = json.load(f)
        print(f"Loaded config from {full_path}")
        return config

# Load different configs for each agent
news_config = load_config("news_reporter_config.json")
weather_config = load_config("weather_agent_config.json")
story_config = load_config("story_agent_config.json")
simple_config = load_config("simple_agent_config.json")


# # 1. ASYNC GENERATOR EXAMPLE - inspect.isasyncgenfunction()
# @pebblify(
#     author=news_config["author"],
#     name=news_config.get("name"),
#     description=news_config.get("description"),
#     version=news_config.get("version", "1.0.0"),
#     recreate_keys=news_config.get("recreate_keys", True),
#     skills=[AgentSkill(**skill) for skill in news_config.get("skills", [])],
#     capabilities=AgentCapabilities(**news_config["capabilities"]),
#     agent_trust=news_config.get("agent_trust"),
#     kind=news_config.get("kind", "agent"),
#     debug_mode=news_config.get("debug_mode", False),
#     debug_level=news_config.get("debug_level", 1),
#     monitoring=news_config.get("monitoring", False),
#     telemetry=news_config.get("telemetry", True),
#     num_history_sessions=news_config.get("num_history_sessions", 10),
#     documentation_url=news_config.get("documentation_url"),
#     extra_metadata=news_config.get("extra_metadata", {}),
#     deployment_config=DeploymentConfig(**news_config["deployment"]),
# )
# async def news_reporter_agent(messages: List[str]) -> AsyncGenerator[str, None]:
#     """Async generator function example - yields multiple results asynchronously."""
    
#     # Use any framework internally
#     agent = Agent(
#         instructions="Get current news from amsterdam",
#         model=OpenAIChat(id="gpt-4o")
#     )
#     result = agent.run(messages=messages)
    
#     # Yield protocol-compliant response
#     yield result.to_dict()['content']


# # 2. COROUTINE EXAMPLE - inspect.iscoroutinefunction()
# @pebblify(
#     author=weather_config["author"],
#     name=weather_config.get("name"),
#     description=weather_config.get("description"),
#     version=weather_config.get("version", "1.0.0"),
#     recreate_keys=weather_config.get("recreate_keys", True),
#     skills=[AgentSkill(**skill) for skill in weather_config.get("skills", [])],
#     capabilities=AgentCapabilities(**weather_config["capabilities"]),
#     agent_trust=weather_config.get("agent_trust"),
#     kind=weather_config.get("kind", "agent"),
#     debug_mode=weather_config.get("debug_mode", False),
#     debug_level=weather_config.get("debug_level", 1),
#     monitoring=weather_config.get("monitoring", False),
#     telemetry=weather_config.get("telemetry", True),
#     num_history_sessions=weather_config.get("num_history_sessions", 10),
#     documentation_url=weather_config.get("documentation_url"),
#     extra_metadata=weather_config.get("extra_metadata", {}),
#     deployment_config=DeploymentConfig(**weather_config["deployment"]),
# )
# async def weather_agent(messages: List[str]):
#     """Coroutine function example - manifest handles streaming automatically."""
    
#     # User writes simple agent code - manifest handles streaming
#     agent = Agent(
#         instructions="Provide weather information for the requested location",
#         model=OpenAIChat(id="gpt-4o")
#     )
    
#     # Await the agent result - this returns the streaming object
#     result = await agent.arun(messages=messages, stream=True)
    
#     # Return the streaming result - manifest will detect it's async iterable
#     return result


# # 3. GENERATOR EXAMPLE - inspect.isgeneratorfunction()
# @pebblify(
#     author=story_config["author"],
#     name=story_config.get("name"),
#     description=story_config.get("description"),
#     version=story_config.get("version", "1.0.0"),
#     recreate_keys=story_config.get("recreate_keys", True),
#     skills=[AgentSkill(**skill) for skill in story_config.get("skills", [])],
#     capabilities=AgentCapabilities(**story_config["capabilities"]),
#     agent_trust=story_config.get("agent_trust"),
#     kind=story_config.get("kind", "agent"),
#     debug_mode=story_config.get("debug_mode", False),
#     debug_level=story_config.get("debug_level", 1),
#     monitoring=story_config.get("monitoring", False),
#     telemetry=story_config.get("telemetry", True),
#     num_history_sessions=story_config.get("num_history_sessions", 10),
#     documentation_url=story_config.get("documentation_url"),
#     extra_metadata=story_config.get("extra_metadata", {}),
#     deployment_config=DeploymentConfig(**story_config["deployment"]),
# )
# def story_agent(messages: List[str]) -> Generator[str, None, None]:
#     """Generator function example - yields multiple results synchronously."""
    
#     # Use any framework internally
#     agent = Agent(
#         instructions="Create an engaging story based on the user's request, tell it in parts",
#         model=OpenAIChat(id="gpt-4o")
#     )
    
#     # Simulate streaming response by yielding parts
#     yield "Starting the story..."
    
#     result = agent.run(messages=messages)
#     content = result.to_dict()['content']

#     yield content
    
#     # Split content into parts and yield each
#     sleep(2)
    
#     yield "Story complete!"


# 4. REGULAR FUNCTION EXAMPLE - else case
@pebblify(
    author=simple_config["author"],
    name=simple_config.get("name"),
    description=simple_config.get("description"),
    version=simple_config.get("version", "1.0.0"),
    recreate_keys=simple_config.get("recreate_keys", True),
    skills=[AgentSkill(**skill) for skill in simple_config.get("skills", [])],
    capabilities=AgentCapabilities(**simple_config["capabilities"]),
    agent_trust=simple_config.get("agent_trust"),
    kind=simple_config.get("kind", "agent"),
    debug_mode=simple_config.get("debug_mode", False),
    debug_level=simple_config.get("debug_level", 1),
    monitoring=simple_config.get("monitoring", False),
    telemetry=simple_config.get("telemetry", True),
    num_history_sessions=simple_config.get("num_history_sessions", 10),
    documentation_url=simple_config.get("documentation_url"),
    extra_metadata=simple_config.get("extra_metadata", {}),
    deployment_config=DeploymentConfig(**simple_config["deployment"]),
    storage_config=StorageConfig(**simple_config["storage"]),
    scheduler_config=SchedulerConfig(**simple_config["scheduler"]),
)
def simple_agent(messages: List[str]) -> str:
    """Regular function example - returns single result."""
    
    # Use any framework internally
    agent = Agent(
        instructions="Provide a simple response to the user's message",
        model=OpenAIChat(id="gpt-4o")
    )
    
    result = agent.run(input=messages)
    
    return result.to_dict()['content']


if __name__ == "__main__":
    print("Agno Example - All Function Types")
    print("1. news_reporter_agent - Async Generator")
    print("2. weather_agent - Coroutine") 
    print("3. story_agent - Generator")
    print("4. simple_agent - Regular Function")
