"""Echo agent with push notification support.

This example demonstrates how to configure push notifications when using bindufy.
The agent will send webhook notifications for all task state changes and artifacts.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Handle incoming messages by echoing back the user's latest input.

    Args:
        messages: List of message dictionaries containing conversation history.

    Returns:
        List containing a single assistant message with the user's content.
    """
    return [{"role": "assistant", "content": messages[-1]["content"]}]


config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_webhook_agent",
    "description": "Echo agent with push notification support for testing webhooks.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    
    # Enable push notifications capability
    "capabilities": {
        "push_notifications": True
    },
    
    # Optional: Configure global webhook for all tasks
    # If not specified, clients must provide webhook in each request
    "global_webhook_url": "https://myapp.com/webhooks/global",
    "global_webhook_token": "global_secret_token_123"
}

bindufy(config, handler)
