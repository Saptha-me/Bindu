"""Echo agent fixture for the boxd_e2e test.

Runs *inside* the boxd VM during e2e. Not invoked by the host directly.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Echo the last user message back, or a placeholder when input is empty."""
    if not messages:
        return "no message"
    last = messages[-1]
    # A2A contract: the message text lives in parts. Fall back to "content"
    # so the fixture also works against older bindu releases that flattened
    # history to chat format.
    text = " ".join(
        p.get("text", "") for p in last.get("parts", []) if p.get("kind") == "text"
    )
    return [
        {
            "role": "assistant",
            "content": text or last.get("content", ""),
        }
    ]


config = {
    "author": "e2e@azin.run",
    "name": "boxd-e2e-echo",
    "description": "echo agent for e2e",
    "deployment": {
        # Bind on all interfaces so the boxd proxy can reach us.
        "url": "http://0.0.0.0:3773",
        "expose": True,
    },
}

if __name__ == "__main__":
    bindufy(config, handler)
