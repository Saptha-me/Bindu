"""Optimized logging configuration for bindu using Rich and Loguru."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    from loguru import Logger

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

from bindu.settings import app_settings

# Lazy initialization - console created only when needed
_console: Optional[Console] = None
_is_logging_configured = False


def _get_console() -> Console:
    """Get or create the Rich console instance (lazy initialization)."""
    global _console
    if _console is None:
        # Build theme from settings
        theme = Theme(
            {
                "info": app_settings.logging.theme_info,
                "warning": app_settings.logging.theme_warning,
                "error": app_settings.logging.theme_error,
                "critical": app_settings.logging.theme_critical,
                "debug": app_settings.logging.theme_debug,
                "bindu.did": app_settings.logging.theme_did,
                "bindu.security": app_settings.logging.theme_security,
                "bindu.agent": app_settings.logging.theme_agent,
            }
        )
        _console = Console(theme=theme, highlight=True)
        install_rich_traceback(
            console=_console,
            show_locals=app_settings.logging.show_locals,
            width=app_settings.logging.traceback_width,
        )
    # Type narrowing: _console is guaranteed to be Console here
    return cast(Console, _console)


def configure_logger(
    docker_mode: bool = False,
    log_level: Optional[str] = None,
    show_banner: bool = True,
) -> None:
    """Configure loguru logger with Rich integration.

    Args:
        docker_mode: Optimize for Docker environment (no file logging)
        log_level: Minimum log level (uses settings default if not provided)
        show_banner: Show startup banner
    """
    global _is_logging_configured

    if _is_logging_configured:
        return

    logger.remove()
    console = _get_console()

    # Use settings default if log_level not provided
    level = log_level or app_settings.logging.default_level

    # File logging (skip in Docker mode for performance)
    if not docker_mode:
        log_dir = Path(app_settings.logging.log_dir)
        log_file = log_dir / app_settings.logging.log_filename
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_file,
            rotation=app_settings.logging.log_rotation,
            retention=app_settings.logging.log_retention,
            level=level,
            format=app_settings.logging.log_format,
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
        level=level,
    )

    _is_logging_configured = True


def get_logger(name: Optional[str] = None) -> "Logger":
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
