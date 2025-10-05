#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Simple but beautiful logging configuration for Pebbling using Rich."""

import os
import sys
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

# Set up Rich console with custom theme
PEBBLING_THEME = Theme(
    {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "debug": "dim blue",
        "pebbling.did": "bold green",
        "pebbling.security": "bold magenta",
        "pebbling.agent": "bold blue",
    }
)

# Create console with our theme
console = Console(theme=PEBBLING_THEME, highlight=True)

# Install Rich traceback handler for prettier exceptions
install_rich_traceback(console=console, show_locals=True)

# Global flag to track if logging has been configured
_is_logging_configured = False


def configure_logger(docker_mode: bool = False) -> None:
    """Configure loguru logger with Rich integration.

    Args:
        docker_mode: Optimize for Docker environment
    """
    global _is_logging_configured

    # Only configure once
    if _is_logging_configured:
        return

    # Remove default logger
    logger.remove()

    # File logging (skip in Docker mode)
    if not docker_mode:
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/pebbling_server.log",
            rotation="10 MB",
            retention="1 week",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {module}:{function}:{line} | {message}",
        )

    # Add Rich handler for beautiful console output with our custom theme
    logger.configure(
        handlers=[
            {
                "sink": RichHandler(console=console, rich_tracebacks=True, markup=True, log_time_format="[%X]"),
                "format": "{message} {extra}",
            }
        ]
    )

    # Show a startup banner (not in Docker)
    if not docker_mode:
        console.print(Panel.fit("[bold cyan]Pebbling 🐧 [/bold cyan]", border_style="cyan"))

    _is_logging_configured = True


def get_logger(name: Optional[str] = None) -> logger.__class__:
    """Get a configured logger instance.

    Args:
        name: Optional name for the logger

    Returns:
        A configured logger instance
    """
    # Ensure global logging is configured
    configure_logger()

    # If name is not provided, try to infer it from the caller's frame
    if name is None:
        frame = sys._getframe(1)
        name = frame.f_globals.get("__name__", "unknown")

    # Return a contextualized logger
    return logger.bind(module=name)


# Export commonly used objects
log = get_logger("pebbling 🐧")  # Quick access to logger
