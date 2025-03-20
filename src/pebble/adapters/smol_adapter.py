"""
Adapter for SmolaAgents.

This module provides an adapter that translates between the SmolaAgents framework
and the unified pebble protocol.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole


class SmolAdapter(AgentProtocol):
    """Adapter for SmolaAgents."""
    
    def __init__(self, agent, agent_id=None, name=None, metadata=None):
        """Initialize the SmolaAgents adapter.
        
        Args:
            agent: A SmolaAgents agent instance
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            metadata: Additional metadata about the agent
        """
        # Extract capabilities from the SmolaAgents agent's tools if available
        capabilities = []
        if hasattr(agent, 'tools') and agent.tools:
            capabilities = [tool.name for tool in agent.tools if hasattr(tool, 'name')]
        elif hasattr(agent, 'llm') and hasattr(agent.llm, 'function_map'):
            capabilities = list(agent.llm.function_map.keys())
        
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name or getattr(agent, 'name', 'SmolaAgent'),
            framework="smolagents",
            capabilities=capabilities,
            metadata=metadata or {}
        )
        
        # Store session history for continuity
        self.sessions = {}
    
    async def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request with a SmolaAgents agent.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        session_id = request.session_id
        
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "agent_state": {}
            }
        
        # Get the message for the agent
        message = request.message
        
        # Store the request message in session history
        self.sessions[session_id]["history"].append({
            "role": request.role.value.lower(),  # Convert to string for compatibility
            "content": message
        })
        
        try:
            # Process the request with the SmolaAgents agent
            # SmolaAgents typically use a 'run' or '__call__' method
            if hasattr(self.agent, 'run'):
                # Most smolagents have a run method
                result = await self.agent.run(message)
            elif hasattr(self.agent, '__call__'):
                # Some agents might use a callable interface
                result = await self.agent(message)
            elif hasattr(self.agent, 'generate'):
                # Some might use a generate method
                result = await self.agent.generate(message)
            else:
                raise AttributeError("SmolaAgent does not have a supported execution method")
            
            # Extract tool calls if they exist
            tool_calls = []
            if hasattr(result, 'tool_calls'):
                tool_calls = result.tool_calls
            elif hasattr(result, 'function_calls'):
                tool_calls = result.function_calls
            
            # Extract the response content
            if hasattr(result, 'response'):
                response_content = result.response
            elif hasattr(result, 'content'):
                response_content = result.content
            elif hasattr(result, 'output'):
                response_content = result.output
            elif isinstance(result, str):
                response_content = result
            else:
                response_content = str(result)
            
        except Exception as e:
            response_content = f"Error processing request with SmolaAgents: {str(e)}"
            tool_calls = []
        
        # Store the response in session history
        self.sessions[session_id]["history"].append({
            "role": MessageRole.AGENT.value.lower(),
            "content": response_content
        })
        
        # Create and return the response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=session_id,
            message=response_content,
            role=MessageRole.AGENT,
            metadata=request.metadata,
            tool_calls=tool_calls if tool_calls else None
        )
