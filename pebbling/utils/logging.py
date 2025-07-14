"""Logging configuration for the Pebbling server."""

import os
from loguru import logger

def configure_logger() -> None:
    """Configure loguru logger for the pebbling server.
    
    Sets up file-based logging with rotation and console logging with colorization.
    """
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
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
    )
    
    # Add console logger for development
    logger.add(
        lambda msg: print(msg),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
        colorize=True
    )