# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Agent adapter implementation for integrating various agent backends with the Pebbling framework.

This module provides the core adapter classes that bridge between user-defined agent functions
and the Pebbling protocol, supporting the explicit protocol design.
"""

import inspect
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
from uuid import UUID

from pebbling.protocol.types import (
    AgentManifest,
    DataPart,
    Message,
    Part,
    Role,
    TextPart
)
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.adapter")


class PebblingMessage:
    """Convenient wrapper around the protocol Message type."""
    
    def __init__(self, message: Message):
        """Initialize from a protocol Message."""
        self._message = message
    
    @classmethod
    def from_text(
        cls, 
        content: str, 
        role: Role = Role.agent,
        context_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'PebblingMessage':
        """Create a text message."""
        message = Message(
            contextId=context_id or uuid.uuid4(),
            messageId=uuid.uuid4(),
            role=role,
            parts=[Part(root=TextPart(content=content))],
            metadata=metadata
        )
        return cls(message)
    
    @classmethod
    def from_data(
        cls,
        data: Dict[str, Any],
        role: Role = Role.agent,
        context_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'PebblingMessage':
        """Create a data message."""
        message = Message(
            contextId=context_id or uuid.uuid4(),
            messageId=uuid.uuid4(),
            role=role,
            parts=[Part(root=DataPart(content="", data=data))],
            metadata=metadata
        )
        return cls(message)
    
    def get_text(self) -> str:
        """Extract text content from the message."""
        text_parts = []
        for part in self._message.parts:
            if isinstance(part.root, TextPart):
                text_parts.append(part.root.content)
        return "\n".join(text_parts)
    
    def get_data(self) -> List[Dict[str, Any]]:
        """Extract data parts from the message."""
        data_parts = []
        for part in self._message.parts:
            if isinstance(part.root, DataPart):
                data_parts.append(part.root.data)
        return data_parts
    
    @property
    def context_id(self) -> UUID:
        """Get the context ID."""
        return self._message.contextId
    
    @property
    def message_id(self) -> UUID:
        """Get the message ID."""
        return self._message.messageId
    
    @property
    def role(self) -> Role:
        """Get the sender role."""
        return self._message.role
    
    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Get message metadata."""
        return self._message.metadata
    
    @property
    def raw_message(self) -> Message:
        """Get the underlying protocol Message."""
        return self._message


class PebblingContext:
    """Context information for agent execution."""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.agent_id = agent_id
        self.metadata = metadata or {}
        self._history: List[PebblingMessage] = []
    
    def add_to_history(self, message: PebblingMessage):
        """Add a message to the conversation history."""
        self._history.append(message)
    
    @property
    def history(self) -> List[PebblingMessage]:
        """Get the conversation history."""
        return self._history.copy()


class AgentAdapter:
    """
    Adapter that wraps user-defined agent functions to work with the Pebbling protocol.
    
    This class handles the conversion between protocol messages and user function calls,
    supporting both sync and async agent functions with different return types.
    """
    
    def __init__(self, agent_function: Callable, agent_manifest: AgentManifest):
        """
        Initialize the adapter.
        
        Args:
            agent_function: The user-defined agent function
            agent_manifest: The agent manifest with metadata
        """
        self.agent_function = agent_function
        self.agent_manifest = agent_manifest
        self.signature = inspect.signature(agent_function)
        self.is_async = inspect.iscoroutinefunction(agent_function)
        self.is_generator = inspect.isgeneratorfunction(agent_function) or inspect.isasyncgenfunction(agent_function)
        
        # Validate function signature
        self._validate_signature()
        
        logger.debug(f"Created adapter for agent '{agent_manifest.name}' "
                    f"(async={self.is_async}, generator={self.is_generator})")
    
    def _validate_signature(self):
        """Validate that the agent function has the correct signature."""
        params = list(self.signature.parameters.values())
        
        if len(params) < 1:
            raise ValueError("Agent function must have at least 'input' parameter")
        
        if len(params) > 2:
            raise ValueError("Agent function must have only 'input' and optional 'context' parameters")
        
        # Check parameter names
        if params[0].name != "input":
            raise ValueError("First parameter must be named 'input'")
        
        if len(params) == 2 and params[1].name != "context":
            raise ValueError("Second parameter must be named 'context'")
    
    @property
    def has_context_param(self) -> bool:
        """Check if the function accepts a context parameter."""
        return len(self.signature.parameters) == 2
    
    async def execute(
        self, 
        input_message: PebblingMessage, 
        context: PebblingContext
    ) -> AsyncGenerator[PebblingMessage, None]:
        """
        Execute the agent function with the given input and context.
        
        Args:
            input_message: The input message
            context: The execution context
            
        Yields:
            PebblingMessage: Response messages from the agent
        """
        try:
            logger.debug(f"Executing agent '{self.agent_manifest.name}' with input: {input_message.get_text()[:100]}...")
            
            # Prepare function arguments
            args = [input_message]
            if self.has_context_param:
                args.append(context)
            
            # Execute based on function type
            if self.is_async and self.is_generator:
                # Async generator function
                async for result in self.agent_function(*args):
                    yield self._convert_result_to_message(result, context)
            elif self.is_async:
                # Async function
                result = await self.agent_function(*args)
                if hasattr(result, '__aiter__'):
                    # Result is an async generator
                    async for item in result:
                        yield self._convert_result_to_message(item, context)
                else:
                    yield self._convert_result_to_message(result, context)
            elif self.is_generator:
                # Sync generator function
                for result in self.agent_function(*args):
                    yield self._convert_result_to_message(result, context)
            else:
                # Sync function
                result = self.agent_function(*args)
                if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                    # Result is an iterable
                    for item in result:
                        yield self._convert_result_to_message(item, context)
                else:
                    yield self._convert_result_to_message(result, context)
                    
        except Exception as e:
            logger.error(f"Error executing agent '{self.agent_manifest.name}': {e}")
            error_message = PebblingMessage.from_text(
                f"Error: {str(e)}", 
                context_id=input_message.context_id
            )
            yield error_message
    
    def _convert_result_to_message(self, result: Any, context: PebblingContext) -> PebblingMessage:
        """Convert agent function result to PebblingMessage."""
        if isinstance(result, PebblingMessage):
            return result
        elif isinstance(result, str):
            return PebblingMessage.from_text(result)
        elif isinstance(result, dict):
            return PebblingMessage.from_data(result)
        elif hasattr(result, 'content'):
            # Handle objects with content attribute (like Agno RunResponse)
            return PebblingMessage.from_text(str(result.content))
        else:
            # Convert anything else to string
            return PebblingMessage.from_text(str(result))


def create_agent_adapter(agent_function: Callable, agent_manifest: AgentManifest) -> AgentAdapter:
    """
    Create an AgentAdapter for the given function and manifest.
    
    Args:
        agent_function: The user-defined agent function
        agent_manifest: The agent manifest
        
    Returns:
        AgentAdapter: Configured adapter instance
    """
    return AgentAdapter(agent_function, agent_manifest)