"""Optimized logging configuration for bindu using Rich and Loguru."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

# Constants
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "bindu_server.log"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "1 week"
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}"

# Rich theme for colorful logging
BINDU_THEME = Theme(
    {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "debug": "dim blue",
        "bindu.did": "bold green",
        "bindu.security": "bold magenta",
        "bindu.agent": "bold blue",
    }
)

# Lazy initialization - console created only when needed
_console: Optional[Console] = None
_is_logging_configured = False


def _get_console() -> Console:
    """Get or create the Rich console instance (lazy initialization)."""
    global _console
    if _console is None:
        _console = Console(theme=BINDU_THEME, highlight=True)
        install_rich_traceback(console=_console, show_locals=True, width=120)
    return _console


def configure_logger(
    docker_mode: bool = False,
    log_level: str = "INFO",
    show_banner: bool = True,
) -> None:
    """Configure loguru logger with Rich integration.

    Args:
        docker_mode: Optimize for Docker environment (no file logging)
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        show_banner: Show startup banner
    """
    global _is_logging_configured

    if _is_logging_configured:
        return

    logger.remove()
    console = _get_console()

    # File logging (skip in Docker mode for performance)
    if not docker_mode:
        LOG_DIR.mkdir(exist_ok=True)
        logger.add(
            LOG_FILE,
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION,
            level=log_level,
            format=LOG_FORMAT,
            enqueue=True,  # Async logging for better performance
            backtrace=True,
            diagnose=True,
        )

    # Rich console handler
    logger.add(
        RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=True,
            log_time_format="[%X]",
            show_path=False,  # Cleaner output
        ),
        format="{message}",
        level=log_level,
    )

    # Optional startup banner
    if show_banner and not docker_mode:
        console.print("[bold cyan]🌻 bindu logging initialized[/bold cyan]", style="dim")

    _is_logging_configured = True


def get_logger(name: Optional[str] = None) -> logger.__class__:
    """Get a configured logger instance with automatic name inference.

    Args:
        name: Optional logger name (auto-inferred from caller if not provided)

    Returns:
        Configured logger instance bound to the module name
    """
    configure_logger()

    if name is None:
        # Auto-infer module name from caller's frame
        frame = sys._getframe(1)
        name = frame.f_globals.get("__name__", "bindu")

    return logger.bind(module=name)


def set_log_level(level: str) -> None:
    """Dynamically change log level at runtime.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger.level(level)


# Pre-configured logger for quick access
log = get_logger("bindu")
