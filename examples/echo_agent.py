"""Minimal Bindu agent — responds with whatever the user sends.

Useful as a sanity check that Bindu is installed and running correctly.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Handle incoming messages by echoing back the user's latest input.

    Args:
        messages: List of message dictionaries containing conversation history.

    Returns:
        List containing a single assistant message with the user's content.
    """
    # Reply with the user's latest input
    return [{"role": "assistant", "content": messages[-1]["content"]}]


config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler configuration (optional)
    # Use "memory" for single-process (default) or "redis" for distributed multi-process
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry error tracking (optional)
    # Configure Sentry directly in code instead of environment variables
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

bindufy(config, handler)
