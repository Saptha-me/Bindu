from dotenv import load_dotenv
load_dotenv()

import asyncio
from bindu.penguin.bindufy import bindufy
from orchestrator import Orchestrator
from typing import List, Dict, Any

orchestrator = Orchestrator()


def handler(messages: list[dict[str, str]]) -> str:
    """
    Protocol-compliant handler for Bindu.

    Safely extracts user input from message history
    and routes it through the agent marketplace swarm.
    """

    # -------- Input Validation --------

    if not isinstance(messages, list):
        return "Invalid input format: messages must be a list."

    if not messages:
        return "No input message received."

    last_msg = messages[-1]

    if not isinstance(last_msg, dict):
        return "Invalid message structure."

    user_input = last_msg.get("content")

    if not user_input or not isinstance(user_input, str):
        return "Empty or invalid message content."

    # -------- Swarm Execution --------

    try:
        # FIX: Run async orchestrator properly
        result = asyncio.run(orchestrator.run(user_input))
        return result

    except Exception as e:
        return f"Internal agent error: {str(e)}"


if __name__ == "__main__":
    config = {
        "author": "yatirajkulkarni143@gmail.com",
        "name": "agent-marketplace-swarm",
        "description": "Skill-based agent marketplace demonstrating routing between summarization and translation agents using Bindu.",
        "capabilities": {"streaming": True},
        "deployment": {
            "url": "http://localhost:3773",
            "expose": True,
            "cors_origins": ["http://localhost:5173"]
        },
        "skills": ["skills/agent-marketplace-routing"],
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"}
    }

    bindufy(config=config, handler=handler)