"""Summarizer Agent — generates a concise summary of the user's message.

Useful as a practical example of using Bindu for text transformation.
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat


# Define summarizer agent
agent = Agent(
    instructions="You are a summarization assistant. Summarize the input text in 2-3 sentences.",
    model=OpenAIChat(id="gpt-4o"),
)


def handler(messages):
    """Return a summary of the user's latest input message."""
    user_input = messages[-1]["content"]
    result = agent.run(input=user_input)
    return [{"role": "assistant", "content": result}]


config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "summarizer_agent",
    "description": "Summarizes input text into a concise version.",
    "deployment": {"url": "http://localhost:3774", "expose": True},
    "skills": [],
}

bindufy(config, handler)
