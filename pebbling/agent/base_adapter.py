"""
Base Adapter for pebbling Protocol.

This module defines the base adapter interface that all agent-specific adapters must implement.
It provides protocol handlers for the pebbling protocol methods.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from pebbling.server.schemas.model import (
    AgentResponse,
    AudioArtifact,
    ImageArtifact,
    VideoArtifact,
)


class BaseAdapter:
    """
    Base adapter class for integrating any agent with the pebbling protocol.

    Subclasses must implement the create_agent_runner and create_protocol_handler methods.
    """

    def __init__(self, agent_id: Optional[str] = None):
        """
        Initialize with an optional agent ID.

        Args:
            agent_id: Optional agent identifier.
        """
        self.agent_id = agent_id or str(uuid.uuid4())


class BaseAgentRunner(BaseAdapter, ABC):
    """
    Base class for agent runners that all framework-specific implementations must implement.

    This class defines the interface for the REST API server endpoints.
    """

    @abstractmethod
    def run(
        self,
        input_text: str,
        **kwargs,
    ) -> Any:
        """Run the agent with the given input text."""
        pass

    def get_status(self) -> str:
        """Get the current status of the agent."""
        return "healthy"


class BaseProtocolHandler(BaseAdapter, ABC):
    """
    Base class for protocol handlers that all framework-specific implementations must implement.

    This class defines handlers for the pebbling protocol methods.

    All protocol handlers should implement:
    1. Context management (handle_Context)
    2. Core interaction methods (act, listen, view)
    3. Session management
    4. User context management
    """

    def __init__(self, agent_id: Optional[str] = None):
        """Initialize with an optional agent ID."""
        super().__init__(agent_id)

        # Implementing classes should initialize:
        # - Protocol object
        # - Agent capabilities
        # - Session storage
        # - User context storage

    @abstractmethod
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the Context method.

        Required params:
            - operation: The operation to perform (add, update, delete)
            - key: The key of the context

        Optional params:
            - value: The value of the context (required for add/update)
            - metadata: Metadata for the context
            - user_id: User-specific context identifier

        Returns:
            Dict with operation result
        """
        pass

    @abstractmethod
    def act(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a text request and generate a response.

        Args:
            message: The text message to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        pass

    @abstractmethod
    def listen(
        self,
        message: str,
        audio: AudioArtifact,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process audio input with optional text and generate a response.

        Args:
            message: The text message to process
            audio: The audio input to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        pass

    @abstractmethod
    def view(
        self,
        message: str,
        media: Union[VideoArtifact, ImageArtifact],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process visual media with optional text and generate a response.

        Args:
            message: The text message to process
            media: The media input (image or video) to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        pass

    @abstractmethod
    def apply_user_context(self, user_id: str) -> None:
        """
        Apply user-specific context to the agent.

        This method should load user-specific context and apply it to the agent,
        storing the original context for later restoration.

        Args:
            user_id: ID of the user to apply context for
        """
        pass

    @abstractmethod
    def reset_context(self) -> None:
        """
        Reset to original context after processing a user request.

        This method should restore the agent's context to its state before
        apply_user_context was called.
        """
        pass
