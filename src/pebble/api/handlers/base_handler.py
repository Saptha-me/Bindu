"""
Base agent handler implementation.

This module provides a base class for handling different agent types with common
functionality shared across all agent handlers.
"""

import asyncio
import inspect
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

class BaseAgentHandler(ABC):
    """Base class for all agent type handlers.
    
    This abstract class defines the common interface and shared functionality
    for handling different agent types.
    """
    
    def __init__(self, agent: Any, verbose: bool = False):
        """Initialize the handler with an agent instance.
        
        Args:
            agent: The agent instance to handle
            verbose: Whether to enable verbose logging
        """
        self.agent = agent
        self.verbose = verbose
        self.original_state = {}  # For storing original agent state
    
    @abstractmethod
    async def handle_action(self, prompt: str, **kwargs) -> Any:
        """Handle an action for this agent type. Must be implemented by subclasses.
        
        Args:
            prompt: The input prompt for the agent
            **kwargs: Agent-specific parameters
            
        Returns:
            The processed response from the agent
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata specific to this agent type.
        
        Returns:
            Dict[str, Any]: A dictionary containing agent-specific metadata
        """
        # Base metadata that all agent types should provide
        return {
            "timestamp": self._get_current_timestamp()
        }
    
    def _get_current_timestamp(self) -> str:
        """Get the current timestamp in ISO format.
        
        Returns:
            str: The current timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def _run_async_or_threaded(self, func, *args, **kwargs):
        """Run a function asynchronously or in a thread pool if it's synchronous.
        
        Args:
            func: The function to run
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function
        """
        if inspect.iscoroutinefunction(func):
            # Function is already async, just await it
            return await func(*args, **kwargs)
        else:
            # Function is synchronous, run it in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                lambda: func(*args, **kwargs)
            )
    
    def _log_debug(self, message: str):
        """Log a debug message if verbose is enabled.
        
        Args:
            message: The message to log
        """
        if self.verbose:
            logger.debug(message)
    
    def _log_error(self, message: str, exc: Optional[Exception] = None):
        """Log an error message and optionally the exception stack trace.
        
        Args:
            message: The error message
            exc: The exception that was raised, if any
        """
        logger.error(message)
        if exc is not None and self.verbose:
            logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def _save_original_state(self, attribute: str):
        """Save the original value of an agent attribute.
        
        Args:
            attribute: The name of the attribute to save
        """
        if hasattr(self.agent, attribute):
            self.original_state[attribute] = getattr(self.agent, attribute)
    
    def _restore_original_state(self):
        """Restore all saved original attribute values."""
        for attr, value in self.original_state.items():
            if hasattr(self.agent, attr):
                setattr(self.agent, attr, value)
        
        # Clear the saved state
        self.original_state = {}
