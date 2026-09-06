"""Web Scraping AI Agent (Local & Cloud SDK)

Crawls web pages, extracts structured data, cleans and formats outputs,
and prepares datasets for analysis or integration.

Features:
- ScrapeGraph AI for intelligent structured extraction
- Mem0 for persistent memory (dedup, extraction profiles)
- OpenRouter (openai/gpt-oss-120b) for synthesis and formatting
- Local run mode + Bindu Cloud SDK deployment

Usage:
    python web_scraping_agent.py

Environment:
    Requires SCRAPEGRAPH_API_KEY, MEM0_API_KEY, OPENROUTER_API_KEY in .env file
"""

import os
from dotenv import load_dotenv

load_dotenv()

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.scrapegraph import ScrapeGraphTools
from agno.tools.mem0 import Mem0Tools

# Initialize the web scraping agent
agent = Agent(
    instructions=(
        "You are a web scraping assistant. Given a URL and an optional extraction prompt, "
        "use ScrapeGraph to extract structured data from the page. Clean and format the output "
        "into JSON. Use memory to avoid re-scraping URLs you have already processed and to "
        "remember extraction preferences ."
    ),
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    tools=[
        ScrapeGraphTools(api_key=os.getenv("SCRAPEGRAPH_API_KEY")),
        Mem0Tools(api_key=os.getenv("MEM0_API_KEY")),
    ],
)

# Agent configuration for Bindu
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "web_scraping_agent",
    "description": (
        "AI-enabled web scraping agent that collects, structures, and processes "
        "data from websites for analysis and automation."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/web-scraping-skill"],
}

def handler(messages: list[dict[str, str]]):
    """
    Process incoming messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Extracted and structured data from the requested web page
    """
    if messages:
        last = messages[-1]
        if isinstance(last, dict):
            # A2A contract: the message text lives in parts. Fall back to
            # "content" for older bindu releases that flattened history to
            # chat format.
            text = " ".join(
                p.get("text", "") for p in last.get("parts", []) if p.get("kind") == "text"
            )
            latest = text or last.get("content", "")
        else:
            latest = str(last)
        result = agent.run(input=latest)
        if hasattr(result, "content"):
            return result.content
        elif hasattr(result, "response"):
            return result.response
        return str(result)
    return "Please provide a URL and an extraction prompt."

if __name__ == "__main__":
    # Bindu-fy the agent — converts it to a discoverable, interoperable Bindu agent
    bindufy(config, handler)
