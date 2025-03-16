"""
Smol agent handler implementation.

This module provides a specific handler for Smol agents.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_handler import BaseAgentHandler
from ...constants import AgentType

# Set up logging
logger = logging.getLogger(__name__)

class SmolAgentHandler(BaseAgentHandler):
    """Handler for Smol agent types."""
    
    async def handle_action(self, prompt: str, **kwargs) -> Any:
        """Handle action for Smol agent.
        
        Args:
            prompt: The input prompt for the Smol agent
            **kwargs: Smol-specific parameters including:
                - task_name: Name for the task (default: 'Default Task')
                - memory: Optional memory instance
                - use_tools: Whether tools should be used (default: True)
                - verbose: Whether to be verbose (default: False)
                - max_steps: Maximum steps for the agent to take
                - persist_memory: Whether to persist memory between runs (default: True)
                - tools: Optional list of tools to use for this specific request
                - context: Optional context to provide for this request
                
        Returns:
            The processed response from the Smol agent
            
        Raises:
            AttributeError: If the agent doesn't have expected attributes
            ValueError: If there are issues with the provided parameters
            Exception: Any exception from the underlying Smol agent
        """
        self._log_debug(f"Preparing SmolaAgent with prompt: {prompt[:50]}...")
        
        try:
            # Extract SmolaAgent specific parameters
            task_name = kwargs.pop('task_name', 'Default Task')
            memory = kwargs.pop('memory', None)
            use_tools = kwargs.pop('use_tools', True)
            verbose = kwargs.pop('verbose', False)
            max_steps = kwargs.pop('max_steps', None)
            persist_memory = kwargs.pop('persist_memory', True)
            tools = kwargs.pop('tools', None)
            context = kwargs.pop('context', None)
            
            # Store configuration for logging
            smol_config = {
                "task_name": task_name,
                "use_tools": use_tools,
                "verbose": verbose,
                "persist_memory": persist_memory
            }
            
            # Configure memory if provided
            if memory is not None and hasattr(self.agent, 'memory'):
                self._save_original_state('memory')
                self.agent.memory = memory
                smol_config["memory"] = "custom"
            elif not persist_memory and hasattr(self.agent, 'memory'):
                # Clear memory if not persisting
                self._save_original_state('memory')
                self.agent.memory = None
                smol_config["memory"] = "cleared"
            elif hasattr(self.agent, 'memory') and self.agent.memory is not None:
                smol_config["memory"] = "existing"
            
            # Configure max steps if provided
            agent_options = {}
            if max_steps is not None:
                agent_options['max_steps'] = max_steps
                smol_config["max_steps"] = max_steps
            
            # Add tools if provided
            if tools is not None and hasattr(self.agent, 'tools'):
                # Store original tools
                self._save_original_state('tools')
                
                # Update tools for this request
                if isinstance(tools, list):
                    self.agent.tools = tools
                else:
                    self.agent.tools = [tools]
                    
                smol_config["tools"] = f"custom ({len(self.agent.tools)} tools)"
            elif hasattr(self.agent, 'tools') and self.agent.tools:
                smol_config["tools"] = f"existing ({len(self.agent.tools)} tools)"
            
            # Add context if provided
            if context is not None:
                agent_options['context'] = context
                smol_config["context"] = "provided"
            
            self._log_debug(f"Configured Smol agent with: {smol_config}")
            
            try:
                # Execute agent action
                # Use the solve method if available, otherwise fall back to chat
                if hasattr(self.agent, 'solve'):
                    self._log_debug("Using SmolaAgent's solve method")
                    
                    result = await self._run_async_or_threaded(
                        self.agent.solve,
                        prompt, 
                        task_name=task_name,
                        memory=memory if memory is not None else getattr(self.agent, 'memory', None),
                        use_tools=use_tools,
                        verbose=verbose,
                        **agent_options,
                        **kwargs
                    )
                else:
                    self._log_debug("Using SmolaAgent's chat method")
                    result = await self._run_async_or_threaded(
                        self.agent.chat,
                        prompt, 
                        **kwargs
                    )
                
                self._log_debug("SmolaAgent execution completed successfully")
                
                # Build enhanced response structure
                if hasattr(result, 'output') and result.output is not None:
                    # Extract steps information if available
                    steps_info = []
                    if hasattr(result, 'steps') and result.steps:
                        for i, step in enumerate(result.steps):
                            step_data = {
                                "step": i+1,
                                "thought": getattr(step, 'thought', None),
                                "action": getattr(step, 'action', None),
                                "observation": getattr(step, 'observation', None)
                            }
                            steps_info.append(step_data)
                    
                    # Create a structured response
                    if steps_info:
                        return {
                            "final_answer": result.output,
                            "steps": steps_info,
                            "num_steps": len(steps_info)
                        }
                    else:
                        return result.output
                
                # Return the raw result if no output property is found
                return result
                
            finally:
                # Restore original agent state
                self._restore_original_state()
                
        except AttributeError as e:
            self._log_error(f"Smol agent structure error: {str(e)}", e)
            raise
        except ValueError as e:
            self._log_error(f"Invalid parameters for Smol agent: {str(e)}", e)
            raise
        except Exception as e:
            self._log_error(f"Unexpected error with Smol agent: {str(e)}", e)
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata specific to Smol agent type.
        
        Returns:
            Dict[str, Any]: A dictionary containing Smol-specific metadata
        """
        # Get base metadata
        metadata = super().get_metadata()
        
        # Add Smol-specific metadata
        metadata.update({
            "agent_type": AgentType.SMOL,
            "tools": bool(getattr(self.agent, 'tools', None)),
            "tools_count": len(getattr(self.agent, 'tools', [])) if hasattr(self.agent, 'tools') else 0,
            "memory": bool(getattr(self.agent, 'memory', None)),
            "planning": bool(getattr(self.agent, 'planning', False)),
            "model": str(getattr(self.agent, 'model', 'Unknown'))
        })
        
        return metadata
