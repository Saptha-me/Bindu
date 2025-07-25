from pebbling.protocol import PebblingMessage, PebblingContext
from pebbling.agent.pebblify import pebblify
from pebbling.security.setup_security import setup_security
from pebbling.registry.setup_registry import setup_registry
from pebbling.deployment.setup_deployment import DeploymentConfig


@pebblify(
    name="News Reporter",
    description="Reports news with flair",
    security=setup_security(did_required=True),
    registry=setup_registry(store_in_hibiscus=True),
    deployment=DeploymentConfig(expose=True, port=3773)
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