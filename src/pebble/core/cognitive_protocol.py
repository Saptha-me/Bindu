"""
Cognitive Protocol extension for the standard agent protocol.

This module extends the base AgentProtocol with cognitive abilities inspired by
the TinyTroupe framework, enabling more sophisticated agent interaction models.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pebble.db.storage import PostgresStateProvider

logger = logging.getLogger(__name__)

# Maximum number of retry attempts for LLM operations
MAX_RETRIES = 2

from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    CognitiveRequest,
    CognitiveResponse,
    MessageRole,
    StimulusType
)


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
    
    def act(self, request: CognitiveRequest) -> CognitiveResponse:
        """Acts in the environment and updates internal cognitive state.
        
        This method allows the agent to take action based on its current 
        cognitive state and the environmental context provided.
        
        Args:
            request: The cognitive request containing context and parameters
            
        Returns:
            CognitiveResponse: The response with action results and updated state
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
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content=action_response.message,
                stimulus_type=StimulusType.ACTION,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in cognitive operation 'act': {e}")
            
            # Implement retry logic with simplified prompt
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = CognitiveRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    content=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={**exec_metadata, "retry_count": retry_count + 1}
                )
                logger.info(f"Retrying 'act' operation (attempt {retry_count + 1}/{MAX_RETRIES})")
                return self.act(retry_request)
            
            # Log failed interaction if storage_provider is available
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
            
            # Return graceful failure response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content="I'm having trouble processing this request. Let's try a different approach.",
                stimulus_type=request.stimulus_type,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def listen(self, request: CognitiveRequest) -> CognitiveResponse:
        """Listens to another agent and updates internal cognitive state.
        
        This method allows the agent to process verbal input from another agent
        or human and update its cognitive state accordingly.
        
        Args:
            request: The cognitive request containing the verbal input
            
        Returns:
            CognitiveResponse: The response with updated cognitive state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        # Check if we should load state from database (if storage_provider in metadata)
        if "storage_provider" in exec_metadata:
            storage_provider = exec_metadata["storage_provider"]
            self.load_cognitive_state(storage_provider, request.session_id)
        
        # Prune episodic memory if it's getting too large
        self.prune_episodic_memory()
        
        try:
            # Update cognitive state with request context
            self._update_cognitive_state(request)
            
            # Prepare listen context
            listen_context = {
                "current_state": self.cognitive_state,
                "verbal_input": request.content,
                "speaker": request.metadata.get("speaker", "Unknown"),
                "stimulus_type": StimulusType.VERBAL
            }
            
            # Create action request for underlying agent
            action_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=self._format_listen_message(listen_context),
                role=MessageRole.USER,
                metadata=request.metadata
            )
            
            # Process action with underlying agent implementation
            listen_response = self.process_action(action_request)
            
            # Update cognitive state with listen results
            self._update_cognitive_state_from_response(listen_response)
            
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
                    request_content=request.content,
                    response_content=listen_response.message,
                    metadata=exec_metadata
                )
            
            # Return cognitive response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content=listen_response.message,
                stimulus_type=StimulusType.VERBAL,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in cognitive operation 'listen': {e}")
            
            # Implement retry logic
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = CognitiveRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    content=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={**exec_metadata, "retry_count": retry_count + 1}
                )
                logger.info(f"Retrying 'listen' operation (attempt {retry_count + 1}/{MAX_RETRIES})")
                return self.listen(retry_request)
            
            # Log failed interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="listen",
                    request_content=request.content,
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Return graceful failure response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content="I'm having trouble understanding this input. Could you phrase it differently?",
                stimulus_type=request.stimulus_type,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def see(self, request: CognitiveRequest) -> CognitiveResponse:
        """Perceives a visual stimulus and updates internal cognitive state.
        
        This method allows the agent to process visual input in the form of
        descriptions and update its cognitive state accordingly.
        
        Args:
            request: The cognitive request containing the visual description
            
        Returns:
            CognitiveResponse: The response with updated cognitive state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        # Check if we should load state from database (if storage_provider in metadata)
        if "storage_provider" in exec_metadata:
            storage_provider = exec_metadata["storage_provider"]
            self.load_cognitive_state(storage_provider, request.session_id)
        
        # Prune episodic memory if it's getting too large
        self.prune_episodic_memory()
        
        try:
            # Update cognitive state with request context
            self._update_cognitive_state(request)
            
            # Prepare visual context
            visual_context = {
                "current_state": self.cognitive_state,
                "visual_description": request.content,
                "stimulus_type": StimulusType.VISUAL
            }
            
            # Create action request for underlying agent
            action_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=self._format_visual_message(visual_context),
                role=MessageRole.SYSTEM,
                metadata=request.metadata
            )
            
            # Process action with underlying agent implementation
            visual_response = self.process_action(action_request)
            
            # Update cognitive state with visual results
            self._update_cognitive_state_from_response(visual_response)
            
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
                    request_content=request.content,
                    response_content=visual_response.message,
                    metadata=exec_metadata
                )
            
            # Return cognitive response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content=visual_response.message,
                stimulus_type=StimulusType.VISUAL,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in cognitive operation 'see': {e}")
            
            # Implement retry logic
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = CognitiveRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    content=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={**exec_metadata, "retry_count": retry_count + 1}
                )
                logger.info(f"Retrying 'see' operation (attempt {retry_count + 1}/{MAX_RETRIES})")
                return self.see(retry_request)
            
            # Log failed interaction if storage_provider is available
            if "storage_provider" in exec_metadata:
                storage_provider = exec_metadata["storage_provider"]
                storage_provider.log_interaction(
                    agent_id=str(self.agent_id),
                    session_id=request.session_id,
                    operation="see",
                    request_content=request.content,
                    response_content=None,
                    metadata=exec_metadata,
                    error=str(e)
                )
            
            # Return graceful failure response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content="I'm having trouble processing this visual information. Could you describe it differently?",
                stimulus_type=request.stimulus_type,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def think(self, request: CognitiveRequest) -> CognitiveResponse:
        """Forces the agent to think about something and updates cognitive state.
        
        This method allows the agent to perform internal reflection and reasoning
        about a topic without taking external actions.
        
        Args:
            request: The cognitive request containing the thinking topic
            
        Returns:
            CognitiveResponse: The response with thinking results and updated state
        """
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Track execution metadata
        exec_metadata = request.metadata.copy() if request.metadata else {}
        exec_metadata["start_time"] = start_time
        
        # Check if we should load state from database (if storage_provider in metadata)
        if "storage_provider" in exec_metadata:
            storage_provider = exec_metadata["storage_provider"]
            self.load_cognitive_state(storage_provider, request.session_id)
        
        # Prune episodic memory if it's getting too large
        self.prune_episodic_memory()
        
        try:
            # Update cognitive state with request context
            self._update_cognitive_state(request)
            
            # Prepare thinking context
            thinking_context = {
                "current_state": self.cognitive_state,
                "topic": request.content,
                "stimulus_type": StimulusType.THOUGHT
            }
            
            # Create action request for underlying agent
            action_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=self._format_thinking_message(thinking_context),
                role=MessageRole.SYSTEM,
                metadata=request.metadata
            )
            
            # Process action with underlying agent implementation
            thinking_response = self.process_action(action_request)
            
            # Update cognitive state with thinking results
            self._update_cognitive_state_from_response(thinking_response)
            
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
            
            # Return cognitive response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content=thinking_response.message,
                stimulus_type=StimulusType.THOUGHT,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error in cognitive operation 'think': {e}")
            
            # Implement retry logic
            retry_count = exec_metadata.get("retry_count", 0)
            if retry_count < MAX_RETRIES:
                # Modify request for retry with simplified prompt
                retry_request = CognitiveRequest(
                    agent_id=request.agent_id,
                    session_id=request.session_id,
                    content=f"[Simplified] {request.content}",
                    stimulus_type=request.stimulus_type,
                    metadata={**exec_metadata, "retry_count": retry_count + 1}
                )
                logger.info(f"Retrying 'think' operation (attempt {retry_count + 1}/{MAX_RETRIES})")
                return self.think(retry_request)
            
            # Log failed interaction if storage_provider is available
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
            
            # Return graceful failure response
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content="I'm having trouble processing this thought. Let me consider a simpler perspective.",
                stimulus_type=request.stimulus_type,
                cognitive_state=self.cognitive_state,
                metadata={**request.metadata, "error": str(e)}
            )
    
    def listen_and_act(self, request: CognitiveRequest) -> CognitiveResponse:
        """Convenience method that combines listen and act methods.
        
        Args:
            request: The cognitive request containing verbal input and action context
            
        Returns:
            CognitiveResponse: The response with action results after listening
        """
        # First listen to update cognitive state
        listen_response = self.listen(request)
        
        # Then act based on the updated cognitive state
        act_request = CognitiveRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=request.metadata.get("action_instruction", "Decide what to do next based on what you just heard."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def see_and_act(self, request: CognitiveRequest) -> CognitiveResponse:
        """Convenience method that combines see and act methods.
        
        Args:
            request: The cognitive request containing visual input and action context
            
        Returns:
            CognitiveResponse: The response with action results after seeing
        """
        # First see to update cognitive state
        see_response = self.see(request)
        
        # Then act based on the updated cognitive state
        act_request = CognitiveRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=request.metadata.get("action_instruction", "Decide what to do next based on what you just saw."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def think_and_act(self, request: CognitiveRequest) -> CognitiveResponse:
        """Convenience method that combines think and act methods.
        
        Args:
            request: The cognitive request containing thinking topic and action context
            
        Returns:
            CognitiveResponse: The response with action results after thinking
        """
        # First think to update cognitive state
        think_response = self.think(request)
        
        # Then act based on the updated cognitive state
        act_request = CognitiveRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=request.metadata.get("action_instruction", "Decide what to do next based on what you just thought about."),
            stimulus_type=StimulusType.ACTION,
            metadata=request.metadata
        )
        
        return self.act(act_request)
    
    def _update_cognitive_state(self, request: CognitiveRequest) -> None:
        """Update the agent's cognitive state based on the request.
        
        Args:
            request: The cognitive request to process
        """
        # Add request to episodic memory
        self.cognitive_state["episodic_memory"].append({
            "timestamp": request.metadata.get("timestamp", "unknown"),
            "stimulus_type": request.stimulus_type,
            "content": request.content
        })
        
        # Update attention based on stimulus type
        self.cognitive_state["attention"] = request.stimulus_type
        
        # Update context if provided
        if "context" in request.metadata:
            self.cognitive_state["context"] = request.metadata["context"]
    
    def persist_cognitive_state(self, storage_provider: PostgresStateProvider, session_id: str) -> bool:
        """Persist cognitive state to an external storage provider.
        
        Args:
            storage_provider: The storage provider to use
            session_id: The session ID to use for storing the state
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return storage_provider.save_state(
                agent_id=str(self.agent_id),
                session_id=session_id,
                state_data=self.cognitive_state
            )
        except Exception as e:
            logger.error(f"Failed to persist cognitive state: {e}")
            return False
    
    def load_cognitive_state(self, storage_provider: PostgresStateProvider, session_id: str) -> bool:
        """Load cognitive state from an external storage provider.
        
        Args:
            storage_provider: The storage provider to use
            session_id: The session ID to use for retrieving the state
            
        Returns:
            bool: True if state was loaded successfully, False otherwise
        """
        try:
            state = storage_provider.load_state(
                agent_id=str(self.agent_id),
                session_id=session_id
            )
            
            if state:
                self.cognitive_state = state
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to load cognitive state: {e}")
            return False
    
    def prune_episodic_memory(self, max_entries: int = 100) -> None:
        """Limit the size of episodic memory to prevent unbounded growth.
        
        Args:
            max_entries: Maximum number of entries to keep in episodic memory
        """
        if len(self.cognitive_state["episodic_memory"]) > max_entries:
            # Keep important oldest entries (first 10) for context
            oldest = self.cognitive_state["episodic_memory"][:10]
            # Keep most recent entries for recency
            newest = self.cognitive_state["episodic_memory"][-(max_entries-10):]
            self.cognitive_state["episodic_memory"] = oldest + newest
            
            # Log memory pruning
            logger.info(f"Pruned episodic memory for agent {self.agent_id} to {len(self.cognitive_state['episodic_memory'])} entries")
    
    def _update_cognitive_state_from_response(self, response: ActionResponse) -> None:
        """Update the agent's cognitive state based on the agent's response.
        
        Args:
            response: The action response from the agent
        """
        # Add response to episodic memory
        self.cognitive_state["episodic_memory"].append({
            "timestamp": response.metadata.get("timestamp", "unknown"),
            "stimulus_type": StimulusType.RESPONSE,
            "content": response.message
        })
        
        # Extract any cognitive state updates from response metadata
        if "cognitive_state_updates" in response.metadata:
            updates = response.metadata["cognitive_state_updates"]
            
            # Update mental state if provided
            if "mental_state" in updates:
                self.cognitive_state["mental_state"].update(updates["mental_state"])
            
            # Update semantic memory if provided
            if "semantic_memory" in updates:
                self.cognitive_state["semantic_memory"].update(updates["semantic_memory"])
    
    def _format_action_message(self, context: Dict[str, Any]) -> str:
        """Format an action message for the underlying agent.
        
        Args:
            context: The action context
            
        Returns:
            str: The formatted message
        """
        return f"""
You are acting in an environment. Based on your current cognitive state, decide what to do.

CURRENT COGNITIVE STATE:
{context['current_state']}

INSTRUCTION:
{context['instruction']}

Respond with your action and reasoning. Your response should explain what you are doing and why.
"""
    
    def _format_listen_message(self, context: Dict[str, Any]) -> str:
        """Format a listen message for the underlying agent.
        
        Args:
            context: The listen context
            
        Returns:
            str: The formatted message
        """
        return f"""
You have just heard the following message from {context['speaker']}:

"{context['verbal_input']}"

CURRENT COGNITIVE STATE:
{context['current_state']}

Process this verbal input and respond with your understanding and any updates to your cognitive state.
"""
    
    def _format_visual_message(self, context: Dict[str, Any]) -> str:
        """Format a visual message for the underlying agent.
        
        Args:
            context: The visual context
            
        Returns:
            str: The formatted message
        """
        return f"""
You are observing the following scene:

{context['visual_description']}

CURRENT COGNITIVE STATE:
{context['current_state']}

Process this visual input and respond with your perception and any updates to your cognitive state.
"""
    
    def _format_thinking_message(self, context: Dict[str, Any]) -> str:
        """Format a thinking message for the underlying agent.
        
        Args:
            context: The thinking context
            
        Returns:
            str: The formatted message
        """
        return f"""
You need to think deeply about the following topic:

{context['topic']}

CURRENT COGNITIVE STATE:
{context['current_state']}

Think through this topic step by step and respond with your reasoning and conclusions.
"""

    # Add to CognitiveAgentProtocol
    def persist_cognitive_state(self, storage_provider):
        """Persist cognitive state to an external storage provider."""
        storage_provider.save(f"agent_{self.agent_id}_state", self.cognitive_state)
        
    def load_cognitive_state(self, storage_provider):
        """Load cognitive state from an external storage provider."""
        state = storage_provider.load(f"agent_{self.agent_id}_state")
        if state:
            self.cognitive_state = state
    
    # Add memory management
    def prune_episodic_memory(self, max_entries=100):
        """Limit the size of episodic memory to prevent unbounded growth."""
        if len(self.cognitive_state["episodic_memory"]) > max_entries:
            # Keep most recent entries, but also preserve some oldest for context
            oldest = self.cognitive_state["episodic_memory"][:10]
            newest = self.cognitive_state["episodic_memory"][-max_entries+10:]
            self.cognitive_state["episodic_memory"] = oldest + newest
