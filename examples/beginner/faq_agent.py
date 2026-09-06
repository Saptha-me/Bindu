"""
Bindu Docs QA Agent 🌻
Answers questions about Bindu documentation.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools

# ---------------------------------------------------------------------------
# Agent Configuration
# ---------------------------------------------------------------------------
agent = Agent(
    name="Bindu Docs Agent",
    instructions="""
    You are an expert assistant for Bindu (GetBindu).

    TASK:
    1. Search the Bindu documentation (docs.getbindu.com) for the user's query.
    2. Answer the question clearly.

    FORMATTING RULES:
    - Return your answer in CLEAN Markdown.
    - Use '##' for main headers.
    - Use bullet points for lists.
    - Do NOT wrap the entire response in JSON code blocks. Just return the text.
    - At the end, include a '### Sources' section with links found.
    """,
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    markdown=True,
)

# ---------------------------------------------------------------------------
# Handler (FIXED)
# ---------------------------------------------------------------------------
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=MessageConverter.to_chat_format(messages))
    return result
# ---------------------------------------------------------------------------
# Bindu config
# ---------------------------------------------------------------------------
config = {
    "author": "your.email@example.com",
    "name": "bindu_docs_agent",
    "description": "Answers questions about Bindu documentation",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}

# Run the Bindu wrapper
bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
