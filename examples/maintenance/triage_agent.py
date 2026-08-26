"""Issue Triage Agent

A Bindu agent that automates issue triage for the Bindu repository.
Classifies issues, assigns priority, and generates responses.

Features:
- Issue classification (Bug/Feature/Question)
- Priority assignment (High/Medium/Low)
- Automated polite response generation

Usage:
    python triage_agent.py

Environment:
    Requires OPENAI_API_KEY in .env file
"""

import os
from dotenv import load_dotenv
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from pydantic import BaseModel, Field

load_dotenv()

# -----------------------------
# Data Models
# -----------------------------
class IssueTriage(BaseModel):
    category: str = Field(..., description="The category of the issue: 'Bug', 'Feature', or 'Question'.")
    priority: str = Field(..., description="The priority of the issue: 'High', 'Medium', or 'Low'.")
    response: str = Field(..., description="A polite, automated response based on the classification.")

# -----------------------------
# Agent Definition
# -----------------------------
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    response_model=IssueTriage,
    instructions="You are an expert GitHub issue triager. Analyze the issue description and provide classification, priority, and a polite response.",
)

# -----------------------------
# Bindu Configuration
# -----------------------------
config = {
    "author": "maintainer@getbindu.com",
    "name": "issue_triager",
    "description": "Automates issue triage for the Bindu repository to help manage the 7,000+ applicant influx.",
    "skills": ["skills/issue-analyzer"],
    "deployment": {
        "url": "http://localhost:8000",
        "env_vars": {"OPENAI_API_KEY": "env"},
    },
}


# -----------------------------
# Handler Function
# -----------------------------
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response"""
    # Run the agent with the input messages
    response = agent.run(input=messages)

    # Return the structured response (IssueTriage object)
    return response.content


# -----------------------------
# Start the agent with Bindu
# -----------------------------
if __name__ == "__main__":
    bindufy(config, handler)
