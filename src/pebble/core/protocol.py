"""
Protocol definition for standardized agent communication.

This module defines the core protocol that all agents must follow to ensure
consistent communication regardless of the underlying framework. It also provides
an extended CognitiveAgentProtocol with enhanced capabilities for more sophisticated agent interactions.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pebble.db.storage import PostgresStateProvider
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    AgentStatus,
    MessageRole, 
    StatusResponse,
    StimulusType,
    ListenRequest,
    ViewRequest
)

import logging
import time

logger = logging.getLogger(__name__)

# Maximum number of retry attempts for LLM operations
MAX_RETRIES = 2


class AgentProtocol:
    """Base class for the agent protocol."""
    
    def __init__(
        self,
        agent: Any,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        framework: str = "unknown",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize the agent protocol.
        
        Args:
            agent: The underlying agent implementation
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            framework: Name of the framework the agent is based on
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
        """
        self.agent = agent
        self.agent_id = agent_id or uuid4()
        self.name = name or getattr(agent, "name", "Unnamed Agent")
        self.framework = framework
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.status = AgentStatus.READY
        self.sessions = {}
    
    def get_status(self) -> StatusResponse:
        """Get the current status of the agent.
        
        Returns:
            StatusResponse: The current status of the agent
        """
        return StatusResponse(
            agent_id=self.agent_id,
            name=self.name,
            framework=self.framework,
            status=self.status,
            capabilities=self.capabilities,
            metadata=self.metadata
        )
    
    def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request and return a response.
        
        This method should be implemented by adapter classes.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("This method must be implemented by adapter classes")
    
    def act(self, request: ActionRequest) -> ActionResponse:
        """Process a standard text-based action and return a response.
        
        This is a convenience wrapper around process_action.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        return self.process_action(request)
    
    def listen(self, request: ListenRequest) -> ActionResponse:
        """Process an audio input and return a response.
        
        This method should be implemented by adapter classes that support audio processing.
        
        Args:
            request: The listen request containing audio data to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("Audio processing not supported by this adapter")
    
    def view(self, request: ViewRequest) -> ActionResponse:
        """Process an image or video input and return a response.
        
        This method should be implemented by adapter classes that support image/video processing.
        
        Args:
            request: The view request containing image/video data to process
            
        Returns:
            ActionResponse: The response from the agent
        """
        raise NotImplementedError("Image/video processing not supported by this adapter")


class CognitiveAgentProtocol(AgentProtocol):
    """Extension of the base AgentProtocol with cognitive capabilities."""
    
    def __init__(
        self,
        agent: Any,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        framework: str = "unknown",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cognitive_capabilities: Optional[List[str]] = None
    ):
        """Initialize the cognitive agent protocol.
        
        Args:
            agent: The underlying agent implementation
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent (taken from agent if available)
            framework: Name of the framework the agent is based on
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
            cognitive_capabilities: List of cognitive capabilities (act, listen, see, think)
        """
        super().__init__(
            agent=agent,
            agent_id=agent_id,
            name=name,
            framework=framework,
            capabilities=capabilities,
            metadata=metadata
        )
        
        # Add cognitive capabilities
        self.cognitive_capabilities = cognitive_capabilities or ["act"]
        
        # Cognitive state (maintained across interactions)
        self.cognitive_state = {
            "mental_state": {},
            "episodic_memory": [],
            "semantic_memory": {},
            "attention": None,
            "context": []
        }
    
    def act(self, request: ActionRequest) -> ActionResponse:
        """Acts in the environment and updates internal cognitive state.
        
        This method allows the agent to take action based on its current 
        cognitive state and the environmental context provided.
        
        Args:
            request: The action request containing context and parameters
            
        Returns:
            ActionResponse: The response with action results and updated state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        # Check if we should load state from database (if storage_provider is in metadata)
        if "storage_provider" in exec_metadata:
            storage_provider = exec_metadata["storage_provider"]
            self.load_cognitive_state(storage_provider, request.session_id)
        
        # Prune episodic memory if it's getting too large
        self.prune_episodic_memory()
        
        try:
            # Update cognitive state with request context
            self._update_cognitive_state(request)
            
            # Prepare action context
            action_context = {
                "current_state": self.cognitive_state,
                "instruction": request.content,
                "stimulus_type": StimulusType.ACTION
            }
            
            # Create action request for underlying agent
            action_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=self._format_action_message(action_context),
                role=MessageRole.SYSTEM,
                metadata=request.metadata
            )
            
            # Process action with underlying agent implementation
            action_response = self.process_action(action_request)
            
            # Update cognitive state with action results
            self._update_cognitive_state_from_response(action_response)
            
            # Log successful interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                # Save updated state
                self.persist_cognitive_state(storage_provider, request.session_id)
                # Log the interaction
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="act",
                    request_content=request.content,
                    response_content=action_response.message,
                    metadata=exec_metadata
                )
            
            # Return cognitive response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=action_response.message,
                stimulus_type=StimulusType.ACTION,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in act method: {str(e)}")
            
            # Log error if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="act",
                    request_content=request.content,
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Check if we should retry with simplified version
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = ActionRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    message=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={
                        **request.metadata,
                        "retry_count": retry_count + 1
                    }
                )
                logger.info(f"Retrying act with simplified prompt (attempt {retry_count + 1})")
                return self.act(retry_request)
            
            # Return graceful failure response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message="I'm having trouble processing this request. Let's try a different approach.",
                stimulus_type=request.stimulus_type,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def listen(self, request: ListenRequest) -> ActionResponse:
        """Listens to another agent and updates internal cognitive state.
        
        This method allows the agent to process verbal input from another agent
        or human and update its cognitive state accordingly.
        
        Args:
            request: The listen request containing the verbal input
            
        Returns:
            ActionResponse: The response with updated cognitive state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        try:
            # Process audio with underlying agent implementation
            listen_response = super().listen(request)
            
            # Update the cognitive state with the audio transcription/understanding
            if "cognitive_state" not in self.cognitive_state:
                self.cognitive_state["cognitive_state"] = {}
            
            # Add to episodic memory
            self.cognitive_state["episodic_memory"].append({
                "timestamp": time.time(),
                "stimulus_type": StimulusType.AUDIO,
                "content": listen_response.message,
                "metadata": request.metadata
            })
            
            # Update attention
            self.cognitive_state["attention"] = StimulusType.AUDIO
            
            # Log successful interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                # Save updated state
                self.persist_cognitive_state(storage_provider, request.session_id)
                # Log the interaction
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="listen",
                    request_content=str(request.audio),
                    response_content=listen_response.message,
                    metadata=exec_metadata
                )
            
            # Return with cognitive state
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=listen_response.message,
                stimulus_type=StimulusType.AUDIO,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in listen method: {str(e)}")
            
            # Log error if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="listen",
                    request_content=str(request.audio),
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Return graceful failure response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message="I'm having trouble processing this audio. Could you try again or provide text instead?",
                stimulus_type=StimulusType.AUDIO,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def view(self, request: ViewRequest) -> ActionResponse:
        """Perceives a visual stimulus and updates internal cognitive state.
        
        This method allows the agent to process visual input in the form of
        images or videos and update its cognitive state accordingly.
        
        Args:
            request: The view request containing the visual data
            
        Returns:
            ActionResponse: The response with updated cognitive state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        try:
            # Process the image/video with underlying agent implementation
            view_response = super().view(request)
            
            # Update the cognitive state with the visual interpretation
            if "cognitive_state" not in self.cognitive_state:
                self.cognitive_state["cognitive_state"] = {}
            
            # Add to episodic memory
            self.cognitive_state["episodic_memory"].append({
                "timestamp": time.time(),
                "stimulus_type": StimulusType.VISUAL,
                "content": view_response.message,
                "metadata": request.metadata
            })
            
            # Update attention
            self.cognitive_state["attention"] = StimulusType.VISUAL
            
            # Log successful interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                # Save updated state
                self.persist_cognitive_state(storage_provider, request.session_id)
                # Log the interaction
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="see",
                    request_content=str(request.media),
                    response_content=view_response.message,
                    metadata=exec_metadata
                )
            
            # Return with cognitive state
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=view_response.message,
                stimulus_type=StimulusType.VISUAL,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in view method: {str(e)}")
            
            # Log error if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="see",
                    request_content=str(request.media),
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Return graceful failure response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message="I'm having trouble processing this visual input. Could you try again or describe it in text?",
                stimulus_type=StimulusType.VISUAL,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def think(self, request: ActionRequest) -> ActionResponse:
        """Performs internal reflection and reasoning without external actions.
        
        This method allows the agent to think about a topic without taking
        external actions, updating its cognitive state accordingly.
        
        Args:
            request: The action request containing the thinking topic
            
        Returns:
            ActionResponse: The response with thinking results and updated state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        # Prepare thinking context
        thinking_context = {
            **self.cognitive_state,
            "topic": request.content,
            "stimulus_type": StimulusType.THOUGHT
        }
        
        try:
            # Create thinking request for underlying agent
            thinking_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=self._format_thinking_message(thinking_context),
                role=MessageRole.SYSTEM,
                metadata=request.metadata
            )
            
            # Process thinking with underlying agent implementation
            thinking_response = self.process_action(thinking_request)
            
            # Update the cognitive state with the thinking results
            self.cognitive_state["attention"] = StimulusType.THOUGHT
            
            # Add to episodic memory
            self.cognitive_state["episodic_memory"].append({
                "timestamp": time.time(),
                "stimulus_type": StimulusType.THOUGHT,
                "topic": request.content,
                "conclusion": thinking_response.message,
                "metadata": request.metadata
            })
            
            # Log successful interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                # Save updated state
                self.persist_cognitive_state(storage_provider, request.session_id)
                # Log the interaction
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="think",
                    request_content=request.content,
                    response_content=thinking_response.message,
                    metadata=exec_metadata
                )
            
            # Return with cognitive state
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=thinking_response.message,
                stimulus_type=StimulusType.THOUGHT,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in think method: {str(e)}")
            
            # Log error if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="think",
                    request_content=request.content,
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Check if we should retry with simplified version
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = ActionRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    message=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={
                        **request.metadata,
                        "retry_count": retry_count + 1
                    }
                )
                logger.info(f"Retrying think with simplified prompt (attempt {retry_count + 1})")
                return self.think(retry_request)
            
            # Return graceful failure response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message="I'm having trouble thinking about this topic. Let's try a different approach.",
                stimulus_type=StimulusType.THOUGHT,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def listen_and_act(self, request: ActionRequest) -> ActionResponse:
        """Convenience method that combines listen and act methods.
        
        Args:
            request: The action request containing verbal input and action context
            
        Returns:
            ActionResponse: The response with action results after listening
        """
        # First listen to update cognitive state
        listen_response = self.listen(request)
        
        # Then act based on the updated cognitive state
        act_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=request.metadata.get("action_instruction", "Decide what to do next based on what you just heard."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def see_and_act(self, request: ViewRequest) -> ActionResponse:
        """Convenience method that combines see and act methods.
        
        Args:
            request: The view request containing visual input and action context
            
        Returns:
            ActionResponse: The response with action results after seeing
        """
        # First see to update cognitive state
        see_response = self.view(request)
        
        # Then act based on the updated cognitive state
        act_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=request.metadata.get("action_instruction", "Decide what to do next based on what you just saw."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def think_and_act(self, request: ActionRequest) -> ActionResponse:
        """Convenience method that combines think and act methods.
        
        Args:
            request: The action request containing thinking topic and action context
            
        Returns:
            ActionResponse: The response with action results after thinking
        """
        # First think to update cognitive state
        think_response = self.think(request)
        
        # Then act based on the updated cognitive state
        act_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=request.metadata.get("action_instruction", "Decide what to do next based on what you just thought about."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def _update_cognitive_state(self, request: ActionRequest) -> None:
        """Update the agent's cognitive state based on the request.
        
        Args:
            request: The action request to process
        """
        # Add request to episodic memory
        self.cognitive_state["episodic_memory"].append({
            "timestamp": time.time(),
            "stimulus_type": request.stimulus_type if hasattr(request, "stimulus_type") and request.stimulus_type else StimulusType.TEXT,
            "content": request.content if hasattr(request, "content") else request.message,
            "metadata": request.metadata
        })
        
        # Update context with any provided context in metadata
        if request.metadata and "context" in request.metadata:
            self.cognitive_state["context"] = request.metadata["context"]
    
    def _update_cognitive_state_from_response(self, response: ActionResponse) -> None:
        """Update the cognitive state based on a response.
        
        Args:
            response: The response to process
        """
        # Add response to episodic memory
        self.cognitive_state["episodic_memory"].append({
            "timestamp": time.time(),
            "stimulus_type": response.stimulus_type if hasattr(response, "stimulus_type") else StimulusType.TEXT,
            "content": response.content if hasattr(response, "content") else response.message,
            "metadata": response.metadata
        })
    
    def _format_action_message(self, context: Dict[str, Any]) -> str:
        """Format an action message with cognitive context.
        
        Args:
            context: The context to include in the message
            
        Returns:
            str: The formatted message
        """
        # Get cognitive state for context
        state = context.get("current_state", {})
        episodic_memory = state.get("episodic_memory", [])
        semantic_memory = state.get("semantic_memory", {})
        
        # Format episodic memory for better context
        formatted_memory = "\n".join([
            f"- {memory.get('stimulus_type', 'EVENT')}: {memory.get('content', 'No content')}" 
            for memory in episodic_memory[-5:]  # Include last 5 memories
        ]) if episodic_memory else "No episodic memories yet."
        
        # Format semantic knowledge for better context
        formatted_knowledge = "\n".join([
            f"- {topic}: {knowledge}" 
            for topic, knowledge in semantic_memory.items()
        ]) if semantic_memory else "No semantic knowledge yet."
        
        # Format the message with cognitive context
        message = f"""
        COGNITIVE CONTEXT:
        ------------------
        Recent Episodic Memory:
        {formatted_memory}
        
        Semantic Knowledge:
        {formatted_knowledge}
        
        Current Attention Focus: {state.get('attention', 'None')}
        
        INSTRUCTION:
        -----------
        {context.get('instruction', 'No specific instruction provided.')}
        """
        
        return message
    
    def _format_thinking_message(self, context: Dict[str, Any]) -> str:
        """Format a thinking message with cognitive context.
        
        Args:
            context: The context to include in the message
            
        Returns:
            str: The formatted message
        """
        # Format the message with thinking context
        message = f"""
        COGNITIVE REFLECTION:
        --------------------
        Think deeply about the following topic:
        
        TOPIC: {context.get('topic', 'No topic specified')}
        
        Consider your existing knowledge and memories. Think step by step and reason carefully.
        Provide insights, connections to existing knowledge, and any conclusions you can draw.
        """
        
        return message
    
    def prune_episodic_memory(self, max_memories: int = 100) -> None:
        """Prune episodic memory if it's getting too large.
        
        Args:
            max_memories: Maximum number of memories to keep
        """
        if len(self.cognitive_state["episodic_memory"]) > max_memories:
            # Keep only the most recent memories
            self.cognitive_state["episodic_memory"] = self.cognitive_state["episodic_memory"][-max_memories:]
    
    def load_cognitive_state(self, storage_provider: PostgresStateProvider, session_id: str) -> None:
        """Load cognitive state from database.
        
        Args:
            storage_provider: Storage provider for persistence
            session_id: Session ID to load state for
        """
        try:
            state = storage_provider.load_cognitive_state(
                agent_id=str(self.agent_id),
                session_id=session_id
            )
            if state:
                self.cognitive_state = state
                logger.info(f"Loaded cognitive state for agent {self.agent_id}, session {session_id}")
        except Exception as e:
            logger.error(f"Error loading cognitive state: {str(e)}")
    
    def persist_cognitive_state(self, storage_provider: PostgresStateProvider, session_id: str) -> None:
        """Persist cognitive state to database.
        
        Args:
            storage_provider: Storage provider for persistence
            session_id: Session ID to persist state for
        """
        try:
            storage_provider.save_cognitive_state(
                agent_id=str(self.agent_id),
                session_id=session_id,
                state=self.cognitive_state
            )
            logger.info(f"Persisted cognitive state for agent {self.agent_id}, session {session_id}")
        except Exception as e:
            logger.error(f"Error persisting cognitive state: {str(e)}")
