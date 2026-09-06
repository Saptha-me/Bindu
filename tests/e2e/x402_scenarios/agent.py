"""Minimal Bindu echo agent behind an x402 paywall.

Points at the local mock_facilitator (127.0.0.1:3775). Mirrors the
config in ``examples/beginner/echo_agent_behind_paywall.py`` with the
facilitator URL overridden via the documented env var.

Run: ``uv run python tests/e2e/x402_scenarios/agent.py``
"""

from __future__ import annotations

import os

# Point at the local mock facilitator BEFORE importing bindu — settings
# are read from env at module import time.
os.environ.setdefault("X402__FACILITATOR_URL", "http://127.0.0.1:3775")

from bindu.penguin.bindufy import bindufy  # noqa: E402


def handler(messages):
    """Echo back the last user message wrapped in a PAID JOB DONE marker."""
    last = messages[-1] if messages else {}
    # A2A contract: the message text lives in parts.
    text = " ".join(
        p.get("text", "") for p in last.get("parts", []) if p.get("kind") == "text"
    )
    return f"PAID JOB DONE — agent received: '{text}'"


bindufy(
    {
        "author": "e2e@example.com",
        "name": "e2e_echo_agent",
        "description": "Echo agent for #562 E2E scenarios.",
        "deployment": {"url": "http://localhost:3773", "expose": False},
        "execution_cost": {
            "amount": "0.01",
            "token": "USDC",
            "network": "base-sepolia",
            "pay_to_address": "0xa11ce0000000000000000000000000000000a11ce",
            "protected_methods": ["message/send"],
        },
        "skills": [],
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"},
    },
    handler,
)
