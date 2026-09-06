"""AG2 (formerly AutoGen) multi-agent research team wrapped with Bindu.

Three specialized agents collaborate under GroupChat with LLM-driven
speaker selection to produce structured research reports. The team is
exposed as a single Bindu agent, callable via A2A protocol.

Architecture:
    User (via Bindu A2A) → handler → AG2 GroupChat
        ├── researcher — gathers information
        ├── analyst   — evaluates findings
        └── writer    — produces the final report
"""

import os

from autogen import ConversableAgent, LLMConfig
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import AutoPattern
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
    "name": "ag2-research-team",
    "description": (
        "A multi-agent research team powered by AG2 (formerly "
        "AutoGen). Three specialists — researcher, analyst, and "
        "writer — collaborate to produce structured reports on "
        "any topic."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/research-team-skill"],
}


def handler(messages: list[dict[str, str]]):
    """Run the AG2 research team and return the final report."""
    if not messages:
        return [{"role": "assistant", "content": "No input provided."}]
    last = messages[-1]
    # A2A contract: the message text lives in parts. Fall back to "content"
    # so the example also works against older bindu releases that flattened
    # history to chat format.
    text = " ".join(
        p.get("text", "") for p in last.get("parts", []) if p.get("kind") == "text"
    )
    user_input = text or last.get("content", "")
    if not user_input:
        return [{"role": "assistant", "content": "Empty message."}]

    # Fresh agents per request to avoid state leakage
    researcher = ConversableAgent(
        name="researcher",
        system_message=(
            "You are a research specialist. Investigate the "
            "given topic thoroughly. Present key facts, data "
            "points, and sources in a structured format."
        ),
        llm_config=llm_config,
    )

    analyst = ConversableAgent(
        name="analyst",
        system_message=(
            "You are an analyst. Review the researcher's "
            "findings. Identify trends, implications, risks, "
            "and opportunities. Be quantitative where possible."
        ),
        llm_config=llm_config,
    )

    writer = ConversableAgent(
        name="writer",
        system_message=(
            "You are a report writer. Once the researcher and "
            "analyst have contributed, synthesize their work "
            "into a structured report with: Executive Summary, "
            "Key Findings, Analysis, and Recommendations. "
            "Keep it under 500 words. End with TERMINATE."
        ),
        llm_config=llm_config,
    )

    user = ConversableAgent(
        name="user", human_input_mode="NEVER"
    )

    pattern = AutoPattern(
        initial_agent=researcher,
        agents=[researcher, analyst, writer],
        user_agent=user,
        group_manager_args={"llm_config": llm_config},
    )

    result, ctx, last = initiate_group_chat(
        pattern=pattern,
        messages=f"Research and produce a report on: {user_input}",
        max_rounds=10,
    )

    # Extract the last substantive message
    for msg in reversed(result.chat_history):
        content = msg.get("content", "")
        if content and "TERMINATE" not in content:
            return [{"role": "assistant", "content": content}]

    return [{"role": "assistant", "content": "Research complete."}]


if __name__ == "__main__":
    bindufy(config, handler)
