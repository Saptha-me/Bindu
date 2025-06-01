"""Logging configuration utilities for the pebbling framework."""

from loguru import logger
import os
import sys
from typing import Optional


def configure_logger(
    log_file: Optional[str] = None,
    console_level: str = "DEBUG",
    file_level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "1 week",
    format_string: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message} | {extra}"
) -> None:
    """Configure the logger with file and console outputs.
    
    Args:
        log_file: Path to the log file. If None, only console logging is configured.
        console_level: Logging level for console output.
        file_level: Logging level for file output.
        rotation: When to rotate the log file (size or time).
        retention: How long to keep old log files.
        format_string: Format string for log messages.
    """
    # Remove existing handlers
    logger.remove()
    
    # Ensure logs directory exists if log_file is provided
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add file logger
        logger.add(
            log_file,
            rotation=rotation,
            retention=retention,
            level=file_level,
            format=format_string
        )
    
    # Add console logger
    logger.add(
        lambda msg: print(msg),
        level=console_level,
        colorize=True
    )
    
    logger.debug("Logger configured successfully")


def get_module_logger(module_name: str) -> logger:
    """Get a logger for a specific module.
    
    Args:
        module_name: Name of the module requesting the logger
        
    Returns:
        Configured logger instance
    """
    return logger.bind(module=module_name)
