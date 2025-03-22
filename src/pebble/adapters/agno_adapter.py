"""
Adapter for Agno agents.

This module provides an adapter that translates between the Agno agent framework
and the unified pebble protocol.
"""
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole
# Import media models
from pebble.schemas.media_models import (
    Media,
    AudioArtifact
)


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
    
    def _initialize_session(self, session_id, request):
        """Helper to initialize session and set agent properties"""
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
            
        # Set stream mode if applicable
        if hasattr(self.agent, 'stream'):
            self.agent.stream = request.stream
    
    def _extract_response(self, result):
        """Extract content and tool calls from Agno response"""
        tool_calls = []
        # Extract tool calls if they exist and are visible
        if result and hasattr(self.agent, 'show_tool_calls') and self.agent.show_tool_calls:
            if hasattr(result, 'tool_calls'):
                tool_calls = result.tool_calls
            elif hasattr(result, 'get_tool_calls'):
                tool_calls = result.get_tool_calls()
        
        # Extract the response content
        if result:
            if hasattr(result, 'response'):
                response_content = result.response
            elif hasattr(result, 'content'):
                response_content = result.content
            else:
                response_content = str(result)
        else:
            response_content = "No response generated."
            
        return response_content, tool_calls
    
    def _create_response(self, session_id, response_content, request, tool_calls=None):
        """Create response and update session history"""
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
    
    def act(self, request: ActionRequest) -> ActionResponse:
        """
        Acts in the environment and updates its internal cognitive state.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        session_id = request.session_id
        message = request.message
        
        # Initialize session and configure agent
        self._initialize_session(session_id, request)
        
        # Store the request message in session history
        self.sessions[session_id]["history"].append({
            "role": request.role,
            "content": message
        })
        
        # Process the request with the Agno agent
        try:
            result = self.agent.run(message)
            response_content, tool_calls = self._extract_response(result)
        except Exception as e:
            response_content = f"Error processing request: {str(e)}"
            tool_calls = []
        
        # Create and return the response
        return self._create_response(session_id, response_content, request, tool_calls)

    def listen(self, request: ActionRequest, audio: AudioArtifact) -> ActionResponse:
        """
        Process audio input and respond accordingly.
        
        Args:
            request: The action request to process
            audio: Audio data to process, either as URL or base64-encoded
            
        Returns:
            ActionResponse: The response from the agent
        """
        session_id = request.session_id
        message = request.message or "Process this audio input"
        
        # Initialize session and configure agent
        self._initialize_session(session_id, request)
        
        # Store the request in session history with audio reference
        self.sessions[session_id]["history"].append({
            "role": request.role,
            "content": message,
            "has_audio": True
        })
        
        # Import Agno's Audio class
        from agno.media import Audio
        import base64
        
        # Create Audio object based on input type
        if audio.url:
            try:
                agno_audio = Audio(url=audio.url)
            except Exception as e:
                return self._create_response(
                    session_id, 
                    f"Error creating Audio from URL: {str(e)}", 
                    request
                )
        elif audio.base64_audio:
            try:
                audio_bytes = base64.b64decode(audio.base64_audio)
                agno_audio = Audio(content=audio_bytes)
            except Exception as e:
                return self._create_response(
                    session_id, 
                    f"Error processing base64 audio: {str(e)}", 
                    request
                )
        else:
            return self._create_response(
                session_id, 
                "No audio data provided. Either URL or base64-encoded audio is required.", 
                request
            )
        
        # Package the audio for Agno
        audio_sequence = [agno_audio]
        
        # Process with Agno
        try:
            # Use dedicated listen method if available, otherwise use run
            if hasattr(self.agent, 'listen'):
                result = self.agent.listen(audio_sequence, context=message)
            else:
                result = self.agent.run(message, audio=audio_sequence)
                
            # Extract response and tool calls
            response_content, tool_calls = self._extract_response(result)
            
        except Exception as e:
            return self._create_response(
                session_id, 
                f"Error processing audio with Agno: {str(e)}", 
                request
            )
        
        # Create and return the response
        return self._create_response(session_id, response_content, request, tool_calls)
