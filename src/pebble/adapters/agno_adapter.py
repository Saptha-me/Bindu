"""
Adapter for Agno agents.

This module provides an adapter that translates between the Agno agent framework
and the unified pebble protocol.
"""
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole


class AgnoAdapter(AgentProtocol):
    """Adapter for Agno agents."""
    
    def __init__(self, agent, agent_id=None, name=None, metadata=None):
        """Initialize the Agno adapter.
        
        Args:
            agent: An Agno agent instance
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            metadata: Additional metadata about the agent
        """
        # Extract capabilities from the Agno agent's tools
        capabilities = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, 'name'):
                    capabilities.append(tool.name)
        
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name or getattr(agent, 'name', 'Agno Agent'),
            framework="agno",
            capabilities=capabilities,
            metadata=metadata or {}
        )
        
        # Store session history for continuity
        self.sessions = {}
    
    def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request with an Agno agent.
        
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
        
        # Get or set the agent_id and session_id for the Agno agent
        if hasattr(self.agent, 'agent_id') and not self.agent.agent_id:
            self.agent.agent_id = str(self.agent_id)
        
        if hasattr(self.agent, 'session_id') and not self.agent.session_id:
            self.agent.session_id = str(session_id)
        
        # Create message for Agno agent
        message = request.message
        
        # Store the request message in session history
        self.sessions[session_id]["history"].append({
            "role": request.role,
            "content": message
        })
        
        # Set stream mode if applicable
        if hasattr(self.agent, 'stream'):
            self.agent.stream = request.stream
        
        # Process the request with the Agno agent
        # Agno typically uses a 'run' method
        tool_calls = []
        try:
            result = self.agent.run(message)
            
            # Extract tool calls if they exist and are visible
            if hasattr(self.agent, 'show_tool_calls') and self.agent.show_tool_calls:
                if hasattr(result, 'tool_calls'):
                    tool_calls = result.tool_calls
                elif hasattr(result, 'get_tool_calls'):
                    tool_calls = result.get_tool_calls()
            
            # Extract the response content
            if hasattr(result, 'response'):
                response_content = result.response
            elif hasattr(result, 'content'):
                response_content = result.content
            else:
                response_content = str(result)
            
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
