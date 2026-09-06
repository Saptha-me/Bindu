"""Echo Testing Agent

A minimal Bindu agent for testing connectivity.
Echoes back user input to verify the system is working.

Features:
- Simple echo functionality
- No external dependencies
- Perfect for testing Bindu installation
- Lightweight and fast

Usage:
    python echo_simple_agent.py

Environment:
    No environment variables required
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Handle incoming messages by echoing back the user's latest input.

    Args:
        messages: List of message dictionaries containing conversation history.

    Returns:
        List containing a single assistant message with the user's content.
    """
    # Reply with the text of the user's latest input (A2A parts contract)
    text = " ".join(
        part.get("text", "")
        for part in messages[-1].get("parts", [])
        if part.get("kind") == "text"
    )
    return [{"role": "assistant", "content": text}]


config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}

bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
