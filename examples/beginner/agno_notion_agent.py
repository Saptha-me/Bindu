"""Notion Integration Agent

A Bindu agent that integrates with Notion for content management.
Can create pages and search existing database entries.

Features:
- Create new Notion pages
- Search Notion database
- OpenRouter integration with gpt-oss-120b

Usage:
    python agno_notion_agent.py

Environment:
    Requires OPENROUTER_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID in .env file
"""

import os
from dotenv import load_dotenv
from bindu.penguin.bindufy import bindufy
from bindu.utils.worker import MessageConverter
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from notion_client import Client

load_dotenv()

# -----------------------------
# Environment Variables
# -----------------------------
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise RuntimeError("NOTION_API_KEY and NOTION_DATABASE_ID must be set")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY must be set")

notion = Client(auth=NOTION_API_KEY)


# -----------------------------
# Notion Tools
# -----------------------------
def create_notion_page(title: str, content: str):
    """Create a page in Notion database"""
    return notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={"Name": {"title": [{"text": {"content": title}}]}},
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"text": [{"type": "text", "text": {"content": content}}]},
            }
        ],
    )


def search_notion(query: str):
    """Search pages in Notion database"""
    return notion.databases.query(
        **{
            "database_id": NOTION_DATABASE_ID,
            "filter": {
                "or": [
                    {"property": "Name", "title": {"contains": query}},
                    {"property": "Content", "rich_text": {"contains": query}},
                ]
            },
        }
    )


# -----------------------------
# Agent Definition
# -----------------------------
agent = Agent(
    instructions="You are a Notion assistant. Use tools to create and search Notion pages.",
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=OPENROUTER_API_KEY,
    ),
    tools=[create_notion_page, search_notion],
)

# -----------------------------
# Bindu Configuration
# -----------------------------
config = {
    "author": "paras.chamoli@gmail.com",
    "name": "agno-notion-agent",
    "description": "Notion assistant agent (OpenRouter)",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/pdf-processing", "skills/question-answering"],
}


# -----------------------------
# Handler Function
# -----------------------------
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response"""
    return agent.run(input=MessageConverter.to_chat_format(messages))


# -----------------------------
# Start the agent with Bindu
# -----------------------------
bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
