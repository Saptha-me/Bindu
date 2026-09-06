"""Summarizer Agent — generates a concise summary of the user's message.

Useful as a practical example of using Bindu for text transformation.
Features OpenRouter integration with openai/gpt-oss-120b model.
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv
import os
load_dotenv()


# Define summarizer agent
agent = Agent(
    instructions="You are a professional summarization assistant. Create clear, concise summaries that capture the main points and essential information from any input text. Aim for 2-3 sentences that preserve the core meaning while being significantly shorter than the original.",
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
)




def handler(messages):
    """Return a summary of the user's latest input message."""
    latest = messages[-1]
    user_input = " ".join(
        part.get("text", "")
        for part in latest.get("parts", [])
        if part.get("kind") == "text"
    ).strip()
    result = agent.run(input=user_input)
    return result


config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "summarizer_agent",
    "description": "Professional text summarization agent using OpenRouter's openai/gpt-oss-120b model.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/text-summarization-skill"],
}

bindufy(config, handler)
