"""Example of creating a research assistant agent using Bindu and Agno with Streamlit UI.

This example demonstrates how to create a simple research assistant agent
that uses DuckDuckGo for web searches and can be deployed as a Bindu agent
with a Streamlit interface.
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
}


# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result


# Bindu-fy it with Streamlit UI
# Note: This will start the server. Run Streamlit separately with:
# streamlit run bindu/ui/streamlit_ui.py
bindufy(config, handler, ui="streamlit")
