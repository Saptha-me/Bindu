"""Logging configuration for the Pebbling server."""

import os
import sys
from loguru import logger

# Global flag to track if logging has been configured
_is_logging_configured = False

def configure_logger() -> None:
    """Configure loguru logger for the pebbling server.
    
    Sets up file-based logging with rotation and console logging with colorization.
    """
    global _is_logging_configured
    
    # Only configure once
    if _is_logging_configured:
        return
    
    # Remove default logger
    logger.remove()  # Remove default handlers from loguru
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Add file logger with rotation
    logger.add(
        "logs/pebbling_server.log",
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {module}:{function}:{line} | {message}"
    )
    
    # Add console logger for development
    logger.add(
        lambda msg: print(msg),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {module}:{function}:{line} | {message}",
        colorize=True
    )
    
    _is_logging_configured = True

def get_logger(name: str = None):
    """Get a configured logger instance.
    
    Args:
        name: Optional name for the logger, typically the module name.
              If None, it attempts to infer the caller's module name.
    
    Returns:
        A configured logger instance.
    """
    # Ensure global logging is configured
    configure_logger()
    
    # If name is not provided, try to infer it from the caller's frame
    if name is None:
        frame = sys._getframe(1)
        module = frame.f_globals.get('__name__', 'unknown')
        name = module
    
    # Return a contextualized logger
    return logger.bind(module=name)