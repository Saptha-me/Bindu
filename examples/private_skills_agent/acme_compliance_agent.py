"""ACME Compliance — example of an agent with private skills.

This example exists to show the shape of the `private_skills` +
`allowed_dids` config. It does NOT call an LLM; the handler is a
deliberately boring echo so you can run it without any API key.

What the example demonstrates:

  GET /.well-known/agent.json    → "greet" and "status" only
                                   (the public catalog)
  GET /agent/private.json        → 401 without auth
                                   → 403 with auth but non-allowlisted DID
                                   → 200 with merged catalog when DID is
                                     on the allowlist (greet + status +
                                     cbam-line-classify + eudr-due-diligence)

Run it:

    $ uv run python examples/private_skills_agent/acme_compliance_agent.py

Then hit it with curl:

    $ curl -s http://localhost:3773/.well-known/agent.json | jq .skills

    $ curl -s -o /dev/null -w "%{http_code}\\n" http://localhost:3773/agent/private.json
    401

(For the 200 case you need a Hydra-issued bearer + DID signature; see
docs/AUTHENTICATION.md. The unit tests in
tests/unit/server/endpoints/test_private_agent_card.py cover the
authenticated branch with a stub middleware.)
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Echo the last message back. The point of the example is the
    PAYWALL shape on /agent/private.json, not what the handler does."""
    last_msg = messages[-1] if messages else {}
    # A2A contract: the message text lives in parts. Fall back to "content"
    # so the example also works against older bindu releases that flattened
    # history to chat format.
    text = " ".join(
        p.get("text", "") for p in last_msg.get("parts", []) if p.get("kind") == "text"
    )
    last = text or last_msg.get("content", "")
    return f"acme_compliance_agent: received '{last}'"


config = {
    "author": "acme.compliance@example.com",
    "name": "acme_compliance_agent",
    "description": (
        "ACME Compliance — demo agent for the private-skills surface. "
        "Public catalog shows generic 'greet' + 'status'; the real product "
        "(CBAM / EUDR) lives behind /agent/private.json."
    ),
    "deployment": {
        "url": "http://localhost:3773",
        "expose": False,
    },
    "skills": [
        "skills/public-greet",
        "skills/public-status",
    ],
    # ─── The new bit ──────────────────────────────────────────────
    "private_skills": [
        "skills/cbam-line-classify",
        "skills/eudr-due-diligence",
    ],
    "allowed_dids": [
        # Replace with the actual DIDs of your partner agents.
        # Each entry here is a partner that gets to see the full
        # /agent/private.json response.
        "did:bindu:partner-bank:agent:abc123",
        "did:bindu:partner-customs-broker:agent:def456",
    ],
    # ──────────────────────────────────────────────────────────────
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "debug_mode": False,
}


if __name__ == "__main__":
    bindufy(config, handler)
