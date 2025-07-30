from pebbling.protocol.types import PebblingMessage, PebblingContext, AgentCapabilities, AgentSkill
from pebbling.agent.pebblify import pebblify
from pebbling.security.setup_security import create_security_config
from pebbling.registry.setup_registry import create_registry_config
from pebbling.security.ca.setup_ca import create_ca_config
from pebbling.deployment.setup_deployment import create_deployment_config

from agno import Agent
from agno.openai import OpenAIChat


@pebblify(
    name="News Reporter",
    description="Reports news with flair", 
    skills=["news-reporting", "financial-analysis"],
    capabilities=AgentCapabilities(streaming=True),
    security=create_security_config(did_required=True, keys_required=True, recreate_keys=True),
    registry=create_registry_config(store_in_hibiscus=True),
    ca=create_ca_config(cert_authority="sheldon", issue_certificate=True),
    deployment=create_deployment_config(expose=True, port=3773)
)
async def news_reporter(
    input: PebblingMessage, 
    context: PebblingContext
) -> AsyncGenerator[PebblingMessage, None]:
    """User writes protocol-compliant code directly."""
    
    # Extract text from protocol message
    text = input.get_text()
    
    # Use any framework internally
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    result = await agent.arun(text)
    
    # Yield protocol-compliant response
    yield PebblingMessage.from_text(result.content)