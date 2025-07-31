

from pebbling.protocol.types import AgentCapabilities, AgentSkill
from pebbling.agent.pebblify import pebblify
from pebbling.security.setup_security import create_security_config

from agno.agent import Agent
from agno.models.openai import OpenAIChat


@pebblify(
    skill=AgentSkill(
        description="You are a news reporter with a flair for storytelling.",
        id="news-reporting",
        input_modes=["text"],
        name="News Reporting",
        output_modes=["text"],
        tags=["news","reporting","storytelling"]
    ),
    capabilities=AgentCapabilities(streaming=True),
    credentials=create_security_config(did_required=True, pki_dir=True, recreate_keys=True),
)
async def news_reporter(
    input: str
) -> AsyncGenerator[str, None]:
    """User writes protocol-compliant code directly."""
    
    # Use any framework internally
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    result = await agent.arun(input)
    
    # Yield protocol-compliant response
    yield result