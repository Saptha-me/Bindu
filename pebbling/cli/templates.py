HELLO_WORLD_AGENT_TEMPLATE = """# Example Pebble agent
# Save as your agent entrypoint. Run `pebble launch` later.

from typing import AsyncGenerator

from pebbling.penguin.pebblify import pebblify
from pebbling.protocol.types import AgentCapabilities, AgentSkill
from pebbling.common.models.models import SecurityConfig, DeploymentConfig


@pebblify(
    author="you",
    skill=AgentSkill(name="hello", description="Says hello"),
    capabilities=AgentCapabilities(),
    security_config=SecurityConfig(),
    deployment_config=DeploymentConfig(),
)
async def hello_agent(input: str) -> AsyncGenerator[str, None]:
    yield f"Hello, {input}!"
"""


