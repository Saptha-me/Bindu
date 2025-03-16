"""
Agno agent handler implementation.

This module provides a specific handler for Agno agents.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from .base_handler import BaseAgentHandler
from ...constants import AgentType
from ...protocol.adapters.agno_adapter import AgnoAdapter
from ...protocol.protocol import Protocol, Message, MessageType

# Set up logging
logger = logging.getLogger(__name__)

class AgnoAgentHandler(BaseAgentHandler):
    """Handler for Agno agent types.
    
    This handler adapts between the FastAPI routes and the Agno agent protocol adapter,
    ensuring consistent identity and communication patterns.
    """
    
    def __init__(self, agent: Any, adapter: Optional[AgnoAdapter] = None, verbose: bool = False):
        """Initialize the handler with an agent instance and its protocol adapter.
        
        Args:
            agent: The agent instance to handle
            adapter: The protocol adapter for the agent (optional)
            verbose: Whether to enable verbose logging
        """
        super().__init__(agent, verbose)
        # Set up the protocol adapter - create a new one if not provided
        self.adapter = adapter or AgnoAdapter(agent)
        self.protocol = Protocol()
    
    async def handle_action(self, prompt: str, **kwargs) -> Any:
        """Handle action for Agno agent using the protocol system.
        
        Args:
            prompt: The input prompt for the Agno agent
            **kwargs: Agno-specific parameters including:
                - stream: Whether to stream the response (default: True)
                - add_references: Whether to add knowledge references (default: False)
                - session_id: Optional session ID for conversation tracking
                - context: Optional context for the agent
                - history: Previous messages to include (default: None)
                - num_history_responses: Number of historical responses to include (default: None)
                - tools: Additional tools to make available to the agent (default: None)
                
        Returns:
            The processed response from the Agno agent
            
        Raises:
            AttributeError: If the agent doesn't have expected attributes
            ValueError: If there are issues with the provided parameters
            Exception: Any exception from the underlying Agno agent
        """
        self._log_debug(f"Preparing Agno agent with prompt via protocol adapter: {prompt[:50]}...")
        
        try:
            # Extract key parameters
            stream = kwargs.pop('stream', True)
            session_id = kwargs.pop('session_id', None)
            
            # Use the protocol adapter to create and send a message
            message = self.protocol.create_message(
                message_type=MessageType.TEXT,
                sender="user",  # User is always the sender for incoming prompts
                receiver=self.adapter.agent_id,
                content=prompt,
                metadata={
                    "stream": stream,
                    "session_id": session_id or getattr(self.agent, 'session_id', None),
                    **kwargs  # Include any other parameters
                }
            )
            
            # Send the message through the adapter and get the response
            response_message = await self.adapter.send_message(message)
            
            if response_message:
                # If streaming is requested and supported by the adapter
                if stream and hasattr(self.adapter, 'stream_response'):
                    return self.adapter.stream_response(response_message)
                
                # Return the content of the response message
                return response_message.content
            else:
                # Fallback to direct agent invocation if the adapter didn't provide a response
                self._log_debug("Protocol adapter did not provide a response, falling back to direct agent invocation")
                return await self._direct_agent_invocation(prompt, stream=stream, **kwargs)
                
        except Exception as e:
            self._log_error(f"Error in protocol-based handling: {str(e)}", e)
            # Try fallback to direct invocation
            return await self._direct_agent_invocation(prompt, **kwargs)
            
    async def _direct_agent_invocation(self, prompt: str, **kwargs) -> Any:
        """Fall back to direct agent invocation if protocol handling fails.
        
        This preserves the original handler logic as a fallback mechanism.
        
        Args:
            prompt: The input prompt for the Agno agent
            **kwargs: Agent-specific parameters
            
        Returns:
            The processed response from the Agno agent
        """
        self._log_debug(f"Preparing Agno agent with prompt: {prompt[:50]}...")
        
        # Extract and configure Agno-specific parameters
        stream = kwargs.pop('stream', True)
        add_references = kwargs.pop('add_references', False)
        session_id = kwargs.pop('session_id', None)
        context = kwargs.pop('context', None)
        history = kwargs.pop('history', None)
        num_history_responses = kwargs.pop('num_history_responses', None)
        tools = kwargs.pop('tools', None)
        
        try:
            # Configure agent for this run
            agno_config = {}
            
            # Handle context if provided
            if context is not None:
                if hasattr(self.agent, 'context'):
                    # Save original state
                    self._save_original_state('context')
                    
                    if isinstance(context, dict):
                        # If original context is None, initialize it
                        if self.agent.context is None:
                            self.agent.context = {}
                        # Merge new context with existing
                        self.agent.context.update(context)
                    else:
                        self.agent.context = context
                    agno_config['context'] = self.agent.context
                else:
                    logger.warning("Agno agent does not support context, ignoring context parameter")
            
            # Configure references
            if hasattr(self.agent, 'add_references'):
                self._save_original_state('add_references')
                self.agent.add_references = add_references
                agno_config['add_references'] = add_references
            
            # Set session ID if provided
            if session_id is not None and hasattr(self.agent, 'session_id'):
                self._save_original_state('session_id')
                self.agent.session_id = session_id
                agno_config['session_id'] = session_id
            
            # Configure message history
            if history is not None and hasattr(self.agent, 'add_history_to_messages'):
                self._save_original_state('add_history_to_messages')
                self.agent.add_history_to_messages = True
                agno_config['history'] = history
                
            if num_history_responses is not None and hasattr(self.agent, 'num_history_responses'):
                self._save_original_state('num_history_responses')
                self.agent.num_history_responses = num_history_responses
                agno_config['num_history_responses'] = num_history_responses
                
            # Add tools if provided
            if tools is not None and hasattr(self.agent, 'tools'):
                # Save original tools
                self._save_original_state('tools')
                
                # If agent has tools but they're None, initialize
                if self.agent.tools is None:
                    self.agent.tools = []
                
                # Add new tools to existing tools
                if isinstance(tools, list):
                    self.agent.tools.extend(tools)
                else:
                    self.agent.tools.append(tools)
                agno_config['tools'] = self.agent.tools
            
            self._log_debug(f"Configured Agno agent with: {agno_config}")
            
            try:
                # Use the agent's run method if available, otherwise fall back to get_response
                if hasattr(self.agent, 'run'):
                    self._log_debug("Using Agno agent's run method")
                    response = await self._run_async_or_threaded(
                        self.agent.run, prompt, stream=stream, **kwargs
                    )
                    
                    # Extract the actual response content if it's wrapped in a response object
                    if hasattr(response, 'response'):
                        return response.response
                    return response
                else:
                    self._log_debug("Using Agno agent's get_response method")
                    return await self._run_async_or_threaded(
                        self.agent.get_response, prompt, stream=stream, **kwargs
                    )
            finally:
                # Restore original agent state
                self._restore_original_state()
                
        except AttributeError as e:
            self._log_error(f"Agno agent structure error: {str(e)}", e)
            raise
        except ValueError as e:
            self._log_error(f"Invalid parameters for Agno agent: {str(e)}", e)
            raise
        except Exception as e:
            self._log_error(f"Unexpected error with Agno agent: {str(e)}", e)
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata specific to Agno agent type.
        
        Returns:
            Dict[str, Any]: A dictionary containing Agno-specific metadata
        """
        # Get base metadata
        metadata = super().get_metadata()
        
        # Get agent_id from the adapter first, then fall back to the agent attribute
        agent_id = self.adapter.agent_id if self.adapter else getattr(self.agent, 'agent_id', None)
        
        # Use the session_id from the adapter's context if available
        session_id = None
        if hasattr(self.adapter, 'get_current_session'):
            session_id = self.adapter.get_current_session()
        if not session_id and hasattr(self.agent, 'session_id'):
            session_id = self.agent.session_id
            
        # Add Agno-specific metadata
        metadata.update({
            "agent_type": AgentType.AGNO,
            "agent_id": agent_id,
            "model": str(getattr(self.agent, 'model', 'Unknown')),
            "session_id": session_id,
            "knowledge": bool(getattr(self.agent, 'knowledge', None)),
            "tools": bool(getattr(self.agent, 'tools', None)),
            "memory": bool(getattr(self.agent, 'memory', None)),
            "tools_count": len(getattr(self.agent, 'tools', [])) if hasattr(self.agent, 'tools') else 0,
            "protocol_enabled": bool(self.adapter),
            "adapter_type": type(self.adapter).__name__ if self.adapter else None
        })
        
        return metadata
