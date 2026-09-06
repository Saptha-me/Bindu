# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "bindu @ git+https://github.com/GetBindu/Bindu.git",
#   "hermes-agent @ git+https://github.com/NousResearch/hermes-agent.git",
# ]
# ///
"""Hermes-Agent via Bindu.

Runs hermes-agent's ``AIAgent`` — a full tool-using coding/research agent —
as a bindufied A2A microservice. DID identity, OAuth2-ready HTTP on :3773,
optional FRP tunnel, x402 payments.

This example is self-contained: it does not depend on any add-on module.
Only the two packages listed below need to be installed.

Setup (Python 3.12+):
    cp .env.example .env && $EDITOR .env      # set OPENROUTER_API_KEY

Run (one command — uv reads the PEP 723 header and installs deps on demand):
    uv run hermes_simple_example.py

Or, for a persistent install:
    uv pip install bindu \\
        "hermes-agent @ git+https://github.com/NousResearch/hermes-agent.git"
    python hermes_simple_example.py

Tiers (``HERMES_TIER`` env var) control which Hermes toolsets are exposed:
    read    — web search + web extract only (default, safe for tunnels)
    sandbox — adds filesystem read/write and execute_code
    full    — everything (terminal, browser, MCP). Localhost only.

Note: ``full`` tier exposes terminal + code execution. Never combine it with
a public tunnel.
"""

from __future__ import annotations

import os
from typing import Any

from bindu.penguin.bindufy import bindufy
from run_agent import AIAgent

# Toolset tiers. ``None`` means no restriction (full tier).
_TIERS: dict[str, list[str] | None] = {
    "read": ["web"],
    "sandbox": ["web", "file", "moa"],
    "full": None,
}

_agent: AIAgent | None = None


def _get_agent() -> AIAgent:
    """Lazily create one shared AIAgent per process.

    Keeping a single long-lived agent preserves Anthropic prompt caching
    across Bindu calls — Bindu replays the full history every request, but
    we only feed the *new* user message into the agent's growing message list.
    """
    global _agent
    if _agent is None:
        tier = os.getenv("HERMES_TIER", "read")
        _agent = AIAgent(
            model=os.getenv("HERMES_MODEL", "anthropic/claude-3.5-haiku"),
            max_iterations=30,
            enabled_toolsets=_TIERS.get(tier, _TIERS["read"]),
            quiet_mode=True,
            platform="bindu",
            save_trajectories=False,
            skip_memory=True,
            persist_session=False,
        )
    return _agent


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    """Extract the newest user message's text from A2A ``parts`` (chat fallback)."""
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        parts = m.get("parts")
        if isinstance(parts, list):
            return "\n".join(
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("kind") == "text"
            )
        content = m.get("content", "")
        if isinstance(content, str):
            return content
    return ""


def handler(messages: list[dict[str, Any]]) -> str:
    """Bindu handler contract: (messages) -> string."""
    text = _last_user_text(messages)
    if not text.strip():
        return "Empty message."
    return _get_agent().chat(text)


config = {
    "author": os.getenv("HERMES_AUTHOR", "you@example.com"),
    "name": os.getenv("HERMES_NAME", "hermes"),
    "description": "Hermes agent (tool-using) exposed as a Bindu A2A microservice",
    "deployment": {
        "url": os.getenv("HERMES_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
