"""AG2 (formerly AutoGen) agent wrapped with Bindu.

A simple Q&A agent using AG2's ConversableAgent, exposed as a
Bindu-compatible networked service with identity, communication,
and payment capabilities.
"""

import os

from autogen import ConversableAgent, LLMConfig
from bindu.penguin import bindufy
from dotenv import load_dotenv

load_dotenv()

llm_config = LLMConfig(
    {
        "model": os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
    }
)

config = {
    "author": "ag2-community",
    "name": "ag2-assistant",
    "description": (
        "A research assistant powered by AG2 (formerly AutoGen). "
        "Ask any question and get a clear, concise answer."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/question-answering"],
}


def handler(messages: list[dict[str, str]]):
    """Forward messages to the AG2 agent and return its response."""
    if not messages:
        return [{"role": "assistant", "content": "No input provided."}]

    user_input = " ".join(
        part.get("text", "")
        for part in messages[-1].get("parts", [])
        if part.get("kind") == "text"
    ).strip()
    if not user_input:
        return [{"role": "assistant", "content": "Empty message."}]

    # Fresh agents per request to avoid state leakage
    agent = ConversableAgent(
        name="assistant",
        system_message=(
            "You are a helpful research assistant. Provide "
            "clear, concise answers to questions. When you "
            "don't know something, say so."
        ),
        llm_config=llm_config,
    )
    user_proxy = ConversableAgent(
        name="user", human_input_mode="NEVER",
    )

    result = user_proxy.initiate_chat(
        agent, message=user_input, max_turns=1
    )
    if not result.chat_history:
        return [{"role": "assistant", "content": "No response."}]
    reply = result.chat_history[-1].get("content", "")
    return [{"role": "assistant", "content": reply}]


if __name__ == "__main__":
    bindufy(config, handler)
