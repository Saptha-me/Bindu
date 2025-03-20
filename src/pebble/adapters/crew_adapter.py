"""
Adapter for CrewAI agents.

This module provides an adapter that translates between the CrewAI agent framework
and the unified pebble protocol.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole


class CrewAdapter(AgentProtocol):
    """Adapter for CrewAI agents."""
    
    def __init__(self, agent, agent_id=None, name=None, metadata=None):
        """Initialize the CrewAI adapter.
        
        Args:
            agent: A CrewAI agent instance
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            metadata: Additional metadata about the agent
        """
        # Extract capabilities from the CrewAI agent's tools
        capabilities = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, 'name'):
                    capabilities.append(tool.name)
        
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name or getattr(agent, 'role', 'CrewAI Agent'),
            framework="crewai",
            capabilities=capabilities,
            metadata=metadata or {}
        )
        
        # Store session history for continuity
        self.sessions = {}
    
    def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request with a CrewAI agent.
        
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
        
        # Create a task object for the CrewAI agent
        # CrewAI agents typically expect a Task object
        task = {
            "description": request.message,
            "expected_output": "A detailed response to the user's request.",
            "agent_id": str(self.agent_id),
            "session_id": str(session_id)
        }
        
        # Store the request message in session history
        self.sessions[session_id]["history"].append({
            "role": request.role,
            "content": request.message
        })
        
        # Process the request with the CrewAI agent
        # CrewAI typically uses 'execute_task' method
        tool_calls = []
        try:
            context = "\n".join([f"{msg['role']}: {msg['content']}" 
                               for msg in self.sessions[session_id]["history"]])
            
            # Execute the task with the CrewAI agent
            result = self.agent.execute_task(task, context=context)
            response_content = result
            
            # Extract tool calls if they were used
            # Note: This assumes CrewAI has some way to access tool calls
            # May need adjustment based on actual CrewAI implementation
            if hasattr(self.agent, 'tools_handler') and hasattr(self.agent.tools_handler, 'get_last_tool_calls'):
                tool_calls = self.agent.tools_handler.get_last_tool_calls()
            
        except Exception as e:
            response_content = f"Error processing request: {str(e)}"
        
        # Store the response in session history
        self.sessions[session_id]["history"].append({
            "role": MessageRole.AGENT,
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
