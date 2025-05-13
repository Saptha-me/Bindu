"""Agno protocol handler adapter for pebbling."""

import base64
import uuid
from typing import Any, Dict, List, Optional, Union

import httpx
import requests
from agno.agent import Agent as AgnoAgent
from loguru import logger
from rich.console import Console

from pebbling.agent.base_adapter import BaseProtocolHandler
from pebbling.core.protocol import pebblingProtocol
from pebbling.server.schemas.model import (
    AgentResponse,
    AudioArtifact,
    ImageArtifact,
    MessageRole,
    VideoArtifact,
)

# Initialize Rich console with reduced verbosity
console = Console(highlight=False)


class AgnoProtocolHandler(BaseProtocolHandler):
    """Protocol handler implementation for Agno agents."""

    def __init__(self, agent: AgnoAgent, agent_id: Optional[str] = None):
        """Initialize with an Agno agent.

        Args:
            agent: The Agno agent to handle
            agent_id: Optional agent identifier
        """
        super().__init__(agent_id)
        self.agent = agent
        self.protocol = pebblingProtocol()

        # Ensure agent has a context
        if not hasattr(self.agent, "context") or self.agent.context is None:
            self.agent.context = {}

        # Store user-specific contexts and session data
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Extract agent capabilities
        self.capabilities = self._extract_capabilities()

    def _extract_capabilities(self) -> List[str]:
        """Extract capabilities from agent tools."""
        capabilities = []
        if hasattr(self.agent, "tools") and self.agent.tools:
            capabilities = [tool.name for tool in self.agent.tools if hasattr(tool, "name")]
        return capabilities

    # Session Management

    def _initialize_session(self, session_id: str) -> None:
        """Initialize session if it doesn't exist.

        Args:
            session_id: Unique session identifier
        """
        if not session_id:
            return

        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": [], "agent_state": {}}

    def _store_user_message(self, session_id: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Store user message in session history.

        Args:
            session_id: Session identifier
            message: User message content
            extra_data: Additional message data
        """
        if not session_id:
            return

        self._initialize_session(session_id)

        history_entry = {"role": MessageRole.USER, "content": message}

        if extra_data:
            history_entry.update(extra_data)

        self.sessions[session_id]["history"].append(history_entry)

    # Response handling

    def _extract_response(self, result: Dict[str, Any]) -> tuple:
        """Extract content and messages from Agno response.

        Args:
            result: Raw response from Agno agent

        Returns:
            Tuple of (response_content, messages)
        """
        response_content = result.get("content", "")
        messages = result.get("messages", [])
        return response_content, messages

    def _create_response(self, session_id: str, response_content: str, messages: List[Dict[str, Any]]) -> AgentResponse:
        """Create response and update session history.

        Args:
            session_id: Session identifier
            response_content: Text response content
            messages: Additional message data

        Returns:
            Formatted agent response
        """
        if session_id:
            self._initialize_session(session_id)
            # Store the response in session history
            self.sessions[session_id]["history"].append({"role": MessageRole.AGENT, "content": response_content})

        # Create and return the response
        return AgentResponse(
            agent_id=uuid.UUID(self.agent_id),
            session_id=uuid.UUID(session_id) if session_id else uuid.uuid4(),
            content=response_content,
            role=MessageRole.AGENT,
            metadata={"messages": messages},
            status="success",
        )

    # Media utilities

    def _download_content_from_url(self, url: str) -> bytes:
        """Download content from a URL.

        Args:
            url: URL to download content from

        Returns:
            Downloaded content as bytes

        Raises:
            Exception: If download fails
        """
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    def _decode_base64(self, base64_str: str) -> bytes:
        """Decode base64 string to bytes."""
        if base64_str is None:
            raise ValueError("Base64 string is empty")
        return base64.b64decode(base64_str)

    # Context management

    def apply_user_context(self, user_id: str) -> None:
        """Apply user-specific context to the agent.

        Args:
            user_id: ID of the user to apply context for
        """
        # Store original context to restore after request
        self._original_context = self.agent.context.copy() if hasattr(self.agent, "context") else {}

        if not user_id or user_id not in self.user_contexts:
            logger.warning(f"No specific context found for user {user_id}")
            return

        # Apply user-specific context
        for key, context_item in self.user_contexts[user_id].items():
            self.agent.context[key] = context_item["value"]

        logger.info(f"Applied context for user {user_id}")

    def reset_context(self) -> None:
        """Reset to original context after processing a user request."""
        if hasattr(self, "_original_context"):
            self.agent.context = self._original_context
            delattr(self, "_original_context")
            logger.info("Agent context reset to original state")

    # Context protocol handlers

    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Context protocol (add/update/delete operations).

        Args:
            params: Operation parameters

        Returns:
            Protocol response
        """
        request_id = params.get("id", str(uuid.uuid4()))
        operation = params.get("operation", "").lower()
        key = params.get("key")
        user_id = params.get("user_id")  # Optional user ID for user-specific context

        # Validate required parameters
        if not key:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message="Key is required for Context operations",
            )

        if operation not in ["add", "update", "delete"]:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message=f"Invalid operation '{operation}'. Must be one of: add, update, delete",
            )

        # Initialize user context if needed and this is a user-specific operation
        if user_id and user_id not in self.user_contexts:
            self.user_contexts[user_id] = {}

        # Execute the requested operation
        context_ops = {
            "add": self._handle_add,
            "update": self._handle_update,
            "delete": self._handle_delete,
        }

        return context_ops[operation](request_id, key, params, user_id)

    def _handle_add(
        self,
        request_id: str,
        key: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle add operation for context.

        Args:
            request_id: Request identifier
            key: Context key
            params: Operation parameters
            user_id: Optional user identifier

        Returns:
            Protocol response
        """
        value = params.get("value")
        if not value:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message="Value is required for add operation",
            )

        # Store context with optional metadata
        context_data = {"value": value, "metadata": params.get("metadata", {})}

        if user_id:
            # Store in user-specific context
            self.user_contexts[user_id][key] = context_data
            logger.info(f"Added context key '{key}' for user {user_id}")
        else:
            # Store in global context and inject into Agno agent
            if hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
                self.agent.context[key] = value
            logger.info(f"Added global context key '{key}'")

        return self.protocol.create_response(
            request_id=request_id,
            result={
                "key": key,
                "status": "success",
                "message": f"Context added successfully{f' for user {user_id}' if user_id else ''}",
            },
        )

    def _handle_update(
        self,
        request_id: str,
        key: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle update operation for context.

        Args:
            request_id: Request identifier
            key: Context key
            params: Operation parameters
            user_id: Optional user identifier

        Returns:
            Protocol response
        """
        context_store = self.user_contexts.get(user_id, {}) if user_id else self.agent.context

        if key not in context_store:
            return self.protocol.create_error(
                request_id=request_id,
                code=404,
                message=f"Context with key '{key}' not found" + (f" for user {user_id}" if user_id else ""),
            )

        value = params.get("value")
        if value is None:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message="Value is required for update operation",
            )

        # Update context
        context_store[key]["value"] = value
        if "metadata" in params:
            context_store[key]["metadata"] = params["metadata"]

        # If global context, update in Agno agent if possible
        if not user_id and hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
            self.agent.context[key] = value

        logger.info(f"Updated context key '{key}'{f' for user {user_id}' if user_id else ''}")

        return self.protocol.create_response(
            request_id=request_id,
            result={
                "key": key,
                "status": "success",
                "message": f"Context updated successfully{f' for user {user_id}' if user_id else ''}",
            },
        )

    def _handle_delete(
        self,
        request_id: str,
        key: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle delete operation for context.

        Args:
            request_id: Request identifier
            key: Context key
            params: Operation parameters
            user_id: Optional user identifier

        Returns:
            Protocol response
        """
        context_store = self.user_contexts.get(user_id, {}) if user_id else self.agent.context

        if key not in context_store:
            return self.protocol.create_error(
                request_id=request_id,
                code=404,
                message=f"Context with key '{key}' not found" + (f" for user {user_id}" if user_id else ""),
            )

        # Delete context
        del context_store[key]

        # If global context, remove from Agno agent if possible
        if (
            not user_id
            and hasattr(self.agent, "context")
            and isinstance(self.agent.context, dict)
            and key in self.agent.context
        ):
            del self.agent.context[key]

        logger.warning(f"Deleted context key '{key}'{f' for user {user_id}' if user_id else ''}")

        return self.protocol.create_response(
            request_id=request_id,
            result={
                "key": key,
                "status": "success",
                "message": f"Context deleted successfully{f' for user {user_id}' if user_id else ''}",
            },
        )

    # Main interaction methods

    def act(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """Process a text request and generate a response.

        Args:
            message: The text message to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        # Store request in session history
        session_id_safe = session_id or str(uuid.uuid4())
        self._store_user_message(session_id_safe, message)

        try:
            # Process the request
            result = self.agent.run(message=message, session_id=session_id, user_id=user_id).to_dict()
            response_content, messages = self._extract_response(result)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            response_content = f"Error processing request: {str(e)}"
            messages = []

        # Create and return the response
        return self._create_response(session_id_safe, response_content, messages)

    def listen(
        self,
        message: str,
        audio: AudioArtifact,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """Process audio input with optional text.

        Args:
            message: The text message to process
            audio: The audio input to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        # Store the request in session history with audio reference
        session_id_safe = session_id or str(uuid.uuid4())
        self._store_user_message(session_id_safe, message, {"has_audio": True})

        try:
            # Import Agno's Audio class
            from agno.media import Audio

            # Create Audio object based on input type
            if not audio.url and not audio.base64_audio:
                raise ValueError("Either URL or base64 audio content must be provided")

            if audio.url:
                # Agno's Audio class supports direct URL handling
                # Add timeout to prevent potential DoS vulnerabilities
                audio_data = requests.get(audio.url, timeout=10).content
                format = audio.url.split(".")[-1]
                agno_audio = Audio(content=audio_data, format=format)
            elif audio.base64_audio:
                audio_bytes = self._decode_base64(audio.base64_audio)
                agno_audio = Audio(content=audio_bytes)

            result = self.agent.run(
                message=message, audio=[agno_audio], session_id=session_id, user_id=user_id
            ).to_dict()
            response_content, messages = self._extract_response(result)

        except Exception as e:
            logger.error(f"Error processing audio request: {str(e)}")
            response_content = f"Error processing audio request: {str(e)}"
            messages = []

        return self._create_response(session_id_safe, response_content, messages)

    def view(
        self,
        message: str,
        media: Union[VideoArtifact, ImageArtifact],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentResponse:
        """Process visual media input with optional text.

        Args:
            message: The text message to process
            media: The media input (image or video) to process
            session_id: Session identifier for conversation continuity
            user_id: User identifier for user-specific context

        Returns:
            AgentResponse with the agent's reply
        """
        # Store the request in session history with media reference
        session_id_safe = session_id or str(uuid.uuid4())
        self._store_user_message(session_id_safe, message, {"has_media": True})

        try:
            # Import Agno's media classes
            from agno.media import Image as AgnoImage
            from agno.media import Video as AgnoVideo

            # Configure media processing based on type with proper variable typing
            AgnoMediaClass = None  # Initialize with None for type safety
            if isinstance(media, ImageArtifact):
                media_type = "image"
                AgnoMediaClass = AgnoImage
                media_param_name = "images"
                url_attr = "url"
                base64_attr = "base64_image"
            elif isinstance(media, VideoArtifact):
                media_type = "video"
                AgnoMediaClass = AgnoVideo
                media_param_name = "videos"
                url_attr = "url"
                base64_attr = "base64_video"
            else:
                raise TypeError(f"Unsupported media type: {type(media)}")

            # Get data from appropriate attributes
            url = getattr(media, url_attr, None)
            base64_content = getattr(media, base64_attr, None)

            if not url and not base64_content:
                raise ValueError(f"Either URL or base64 {media_type} content must be provided")

            # Process content based on source
            if url and AgnoMediaClass is not None:  # Add null check
                try:
                    content_bytes = self._download_content_from_url(url)
                except Exception as e:
                    return self._create_response(
                        session_id_safe,
                        f"Error downloading {media_type} from URL: {str(e)}",
                        [],
                    )
            else:
                try:
                    # Ensure base64_content is not None before decoding
                    if not base64_content:
                        raise ValueError(f"Base64 {media_type} content is empty")
                    content_bytes = self._decode_base64(base64_content)
                except Exception as e:
                    return self._create_response(
                        session_id_safe,
                        f"Error decoding base64 {media_type}: {str(e)}",
                        [],
                    )
            agno_media = AgnoMediaClass(content=content_bytes)

            # Set up kwargs with the appropriate media parameter
            media_param = {media_param_name: [agno_media]}  # Pass as a sequence

            # Run the agent
            result = self.agent.run(
                message=message,
                session_id=session_id,
                user_id=user_id,
                **media_param,
            ).to_dict()
            response_content, messages = self._extract_response(result)

        except Exception as e:
            logger.error(f"Error processing media request: {str(e)}")
            response_content = f"Error processing media request: {str(e)}"
            messages = []

        return self._create_response(session_id_safe, response_content, messages)
