"""
Cognitive adapter for Agno agents.

This module provides a cognitive adapter that extends the Agno agent framework
with cognitive capabilities inspired by TinyTroupe.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.schemas.cognitive_models import (
    StimulusType,
    CognitiveRequest,
    CognitiveResponse
)
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    MessageRole
)


class AgnoCognitiveAdapter(CognitiveAgentProtocol):
    """Cognitive adapter for Agno agents."""
    
    def __init__(self, agent, agent_id=None, name=None, metadata=None, cognitive_capabilities=None):
        """Initialize the Agno cognitive adapter.
        
        Args:
            agent: An Agno agent instance
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            metadata: Additional metadata about the agent
            cognitive_capabilities: List of cognitive capabilities
        """
        # Extract capabilities from the Agno agent's tools
        capabilities = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, 'name'):
                    capabilities.append(tool.name)
        
        # If cognitive capabilities are not specified, assume the agent can do everything
        if cognitive_capabilities is None:
            cognitive_capabilities = ["act", "listen", "see", "think"]
        
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name or getattr(agent, 'name', 'Agno Cognitive Agent'),
            framework="agno",
            capabilities=capabilities,
            metadata=metadata or {},
            cognitive_capabilities=cognitive_capabilities
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
            logger.error(f"Error in cognitive operation: {e}")
            # Implement retry logic or fallback
            retry_count = request.metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                request.metadata["retry_count"] = retry_count + 1
                return self.act(request)  # Recursively retry
            else:
                # Return graceful failure response
                return CognitiveResponse(
                    agent_id=self.agent_id,
                    session_id=request.session_id,
                    content="I'm having trouble processing this request. Let's try a different approach.",
                    stimulus_type=request.stimulus_type,
                    cognitive_state=self.cognitive_state,
                    metadata={"error": str(e)}
                )
        
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
    
    def _extract_cognitive_metadata(self, result: Any) -> Dict[str, Any]:
        """Extract cognitive metadata from the Agno agent's response.
        
        Args:
            result: The result from the Agno agent
            
        Returns:
            Dict[str, Any]: Cognitive metadata extracted from the result
        """
        cognitive_metadata = {}
        
        # Try to extract emotional state if available
        if hasattr(result, 'metadata') and result.metadata:
            if 'emotional_state' in result.metadata:
                cognitive_metadata['mental_state'] = {
                    'emotions': result.metadata['emotional_state']
                }
            
            # Try to extract other cognitive states
            if 'cognitive_state' in result.metadata:
                cognitive_metadata.update(result.metadata['cognitive_state'])
        
        return cognitive_metadata
