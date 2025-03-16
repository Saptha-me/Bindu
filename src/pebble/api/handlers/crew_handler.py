"""
Crew agent handler implementation.

This module provides a specific handler for CrewAI agents.
"""

import inspect
import logging
from typing import Any, Dict, List, Optional

from .base_handler import BaseAgentHandler
from ...constants import AgentType

# Set up logging
logger = logging.getLogger(__name__)

class CrewAgentHandler(BaseAgentHandler):
    """Handler for CrewAI agent types."""
    
    def __init__(self, agent: Any, verbose: bool = False):
        """Initialize the handler with a CrewAI agent instance.
        
        Args:
            agent: The CrewAI agent instance to handle
            verbose: Whether to enable verbose logging
        """
        super().__init__(agent, verbose)
        self.transfer_context = None  # For storing transferred knowledge
    
    async def handle_action(self, prompt: str, **kwargs) -> Any:
        """Handle action for CrewAI agent.
        
        Args:
            prompt: The input prompt for the CrewAI agent
            **kwargs: CrewAI-specific parameters including:
                - task_description: Optional detailed task description
                - context: Optional context for the task
                - tools: Optional list of tools to use
                - cache: Whether to use cache (default: True)
                - expected_output: Description of the expected output format
                - async_execution: Whether to run tasks asynchronously
                - task_id: Optional ID for the task
                - callbacks: Optional callbacks for monitoring task execution
                
        Returns:
            The processed response from the CrewAI agent
            
        Raises:
            ImportError: If required CrewAI modules are not available
            ValueError: If the agent doesn't have expected execution methods
            Exception: Any exception from the underlying CrewAI execution
        """
        self._log_debug(f"Preparing CrewAI agent with prompt: {prompt[:50]}...")
        
        try:
            # Extract CrewAI specific parameters
            task_description = kwargs.pop('task_description', prompt)
            context = kwargs.pop('context', None)
            tools = kwargs.pop('tools', [])
            cache = kwargs.pop('cache', True)
            expected_output = kwargs.pop('expected_output', "Detailed response to the query or task")
            async_execution = kwargs.pop('async_execution', True)
            task_id = kwargs.pop('task_id', None)
            callbacks = kwargs.pop('callbacks', None)
            
            # Store configuration for logging
            crew_config = {
                "has_task_description": task_description != prompt,
                "has_context": context is not None,
                "tools_count": len(tools) if isinstance(tools, list) else 1 if tools else 0,
                "cache_enabled": cache,
                "async_execution": async_execution
            }
            
            # Create a safe context if provided
            safe_context = None
            if context is not None:
                if isinstance(context, dict):
                    # Make a copy to avoid side effects
                    safe_context = context.copy()
                else:
                    safe_context = context
            
            # Keep track of original tools if we're modifying them
            if tools and hasattr(self.agent, 'tools'):
                self._save_original_state('tools')
                
                # Update tools for this request
                if isinstance(tools, list):
                    self.agent.tools = tools
                else:
                    self.agent.tools = [tools]
            
            self._log_debug(f"Configured CrewAI agent with: {crew_config}")
            
            # If agent has a transfer_context from previous knowledge transfer
            if hasattr(self, 'transfer_context') and self.transfer_context:
                # Combine with existing context or create new one
                if safe_context is None:
                    safe_context = self.transfer_context
                elif isinstance(safe_context, dict):
                    safe_context['transferred_knowledge'] = self.transfer_context
                elif isinstance(safe_context, str):
                    safe_context = f"{safe_context}\n\nAdditional context: {self.transfer_context}"
                
                self._log_debug("Added transferred knowledge to context")
            
            try:
                # Try to create and execute a Task object if appropriate
                task_execution_result = None
                
                # First check if we have a proper task description and CrewAI is available
                if task_description and task_description != prompt:
                    try:
                        from crewai import Task
                        
                        # Create a task with all available parameters
                        task_args = {
                            "description": task_description,
                            "agent": self.agent,
                            "expected_output": expected_output,
                        }
                        
                        # Add optional parameters
                        if safe_context is not None:
                            task_args["context"] = safe_context
                        if task_id is not None:
                            task_args["id"] = task_id
                        if callbacks is not None:
                            task_args["callbacks"] = callbacks
                        
                        # Create and execute the task
                        task = Task(**task_args)
                        
                        self._log_debug("Created CrewAI Task for execution")
                        
                        if async_execution:
                            task_execution_result = await task.execute()
                        else:
                            # Use thread pool for synchronous execution
                            task_execution_result = await self._run_async_or_threaded(
                                task.execute_sync
                            )
                            
                        self._log_debug("CrewAI Task execution completed successfully")
                    except ImportError as e:
                        logger.warning(f"CrewAI Task module not available: {str(e)}")
                        # Continue to try alternate methods
                        
                # If task execution didn't work, try direct agent methods
                if task_execution_result is None:
                    if hasattr(self.agent, 'execute_task'):
                        self._log_debug("Using CrewAI agent's execute_task method")
                        
                        # Prepare kwargs for execute_task
                        execution_kwargs = kwargs.copy()
                        if safe_context is not None:
                            execution_kwargs['context'] = safe_context
                            
                        task_execution_result = await self._run_async_or_threaded(
                            self.agent.execute_task,
                            prompt, 
                            **execution_kwargs
                        )
                                
                    elif hasattr(self.agent, 'run') and callable(self.agent.run):
                        self._log_debug("Using CrewAI agent's run method")
                        
                        task_execution_result = await self._run_async_or_threaded(
                            self.agent.run,
                            prompt, 
                            **kwargs
                        )
                    else:
                        # No suitable execution method found
                        raise ValueError("CrewAI agent does not have expected execution methods (execute_task or run)")
                
                # Process and return the result
                if isinstance(task_execution_result, dict) and 'output' in task_execution_result:
                    return task_execution_result['output']
                
                return task_execution_result
                
            finally:
                # Restore original agent state
                self._restore_original_state()
                
        except ImportError as e:
            self._log_error(f"Missing CrewAI dependency: {str(e)}", e)
            raise
        except ValueError as e:
            self._log_error(f"Invalid CrewAI configuration: {str(e)}", e)
            raise
        except Exception as e:
            self._log_error(f"Unexpected error with CrewAI agent: {str(e)}", e)
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata specific to CrewAI agent type.
        
        Returns:
            Dict[str, Any]: A dictionary containing CrewAI-specific metadata
        """
        # Get base metadata
        metadata = super().get_metadata()
        
        # Add CrewAI-specific metadata
        metadata.update({
            "agent_type": AgentType.CREW,
            "agent_id": str(getattr(self.agent, 'id', None)),
            "role": getattr(self.agent, 'role', None),
            "goal": getattr(self.agent, 'goal', None),
            "backstory": getattr(self.agent, 'backstory', None),
            "allow_delegation": getattr(self.agent, 'allow_delegation', False),
            "tools_count": len(getattr(self.agent, 'tools', [])) if hasattr(self.agent, 'tools') else 0
        })
        
        return metadata
