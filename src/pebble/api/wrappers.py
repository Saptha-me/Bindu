"""API wrappers for agent frameworks.

This module provides a unified API interface for interacting with different agent types,
enabling seamless communication between Agno, SmolaAgents, and CrewAI agents within
the pebble framework.

Example:
    ```python
    # Create agents
    agno_agent = AgnoAgent()
    smol_agent = SmolAgent()
    
    # Wrap them
    agno_wrapper = AgentAPIWrapper(agent=agno_agent)
    smol_wrapper = AgentAPIWrapper(agent=smol_agent)
    
    # Use common interface
    response = await agno_wrapper.act("What is life?")
    print(response.content)
    ```
"""

from loguru import logger
import traceback
import asyncio
import inspect
from functools import wraps
from contextlib import contextmanager
from typing import Optional, Union, Dict, Any, List, Callable, Type, Tuple, cast, Generator, ClassVar
from .handlers import AgnoAgentHandler, SmolAgentHandler, CrewAgentHandler
from enum import Enum
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field, validator, root_validator

# Configure Loguru logging
import sys

# Configure Loguru with a custom format that includes time, level, module, and message
logger.remove()  # Remove default handler
logger.configure(
    handlers=[
        {
            "sink": sys.stdout,
            "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> {extra}",
            "level": "INFO",
            "colorize": True,
        },
    ],
    extra={"agent_type": "", "action": "", "method": ""},  # Default context values
)

# Import agent types
from agno.agent import Agent as AgnoAgent
from smolagents import MultiStepAgent as SmolAgent
from crewai.agents.agent_builder.base_agent import BaseAgent as CrewAIAgent

# Import centralized agent type enum
from ..constants import AgentType

# Add helper function to determine agent type
def determine_agent_type(agent: Any) -> AgentType:
    """Determine agent type from an agent instance.
    
    Args:
        agent: An instance of an agent from any supported framework
        
    Returns:
        AgentType: The detected agent type
        
    Raises:
        ValueError: If the agent type is not supported
    """
    from agno.agent import Agent as AgnoAgent
    from smolagents import MultiStepAgent as SmolAgent
    from crewai.agents.agent_builder.base_agent import BaseAgent as CrewAIAgent
    
    if isinstance(agent, AgnoAgent):
        return AgentType.AGNO
    elif isinstance(agent, SmolAgent):
        return AgentType.SMOL
    elif isinstance(agent, CrewAIAgent):
        return AgentType.CREW
    else:
        raise ValueError(f"Unsupported agent type: {type(agent).__name__}")

class AgentResponse(BaseModel):
    """Standardized response model for all agent types.
    
    This model provides a unified structure for responses from different agent types,
    ensuring consistent handling of agent outputs throughout the application.
    
    Attributes:
        content: The main response content from the agent
        metadata: Additional information about the response and agent state
        agent_type: The type of agent that generated this response
        success: Whether the agent action completed successfully
        error: Error message if the action failed
        response_id: Unique identifier for this response
        timestamp: When this response was generated
    """
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    agent_type: AgentType
    success: bool = True
    error: Optional[str] = None
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('error')
    def log_errors(cls, v, values):
        """Log errors when they occur."""
        if v is not None:
            agent_type = values.get('agent_type', 'unknown')
            logger.error(f"Agent error ({agent_type}): {v}")
        return v
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to a dictionary suitable for JSON serialization."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "success": self.success,
            "error": self.error,
            "response_id": self.response_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

# Decorator for method timing
def timed_execution(func):
    """Decorator to time and log execution of agent methods."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        
        # Add function name to logger context
        with logger.contextualize(method=func_name):
            logger.debug(f"Starting execution of {func_name}")
            start_time = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.success(f"Executed in {duration:.3f}s")
                
                # Add execution time to result metadata if applicable
                if hasattr(result, 'metadata') and isinstance(result.metadata, dict):
                    result.metadata['execution_time'] = f"{duration:.3f}s"
                    
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.opt(exception=True).error(f"Failed after {duration:.3f}s: {str(e)}")
                raise
    return wrapper


@contextmanager
def agent_execution_context(agent_type: AgentType, action: str) -> Generator[None, None, None]:
    """Context manager for agent execution, providing consistent logging and error handling.
    
    Args:
        agent_type: The type of agent being executed
        action: The action being performed
        
    Yields:
        None
    """
    # Loguru context variables
    logger_context = {
        "agent_type": agent_type.value,
        "action": action,
    }
    
    with logger.contextualize(**logger_context):
        logger.info("Starting agent action")
        start_time = datetime.now()
        try:
            yield
            duration = (datetime.now() - start_time).total_seconds()
            logger.success(f"Completed agent action in {duration:.3f}s")
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.opt(exception=True).error(f"Error after {duration:.3f}s: {str(e)}")
            raise


class AgentAPIWrapper(BaseModel):
    """Base wrapper class that provides a unified API interface for different agent types.
    
    This class serves as an abstraction layer over different agent implementations,
    providing a consistent interface for interacting with agents regardless of their underlying framework.
    
    Attributes:
        agent: The underlying agent instance
        agent_type: The type of the agent (automatically detected if not provided)
        max_retries: Maximum number of retries for action execution
        timeout: Timeout for agent actions in seconds
        verbose: Whether to log verbose output
        cache_config: Configuration for agent response caching
    """
    
    agent: Union[AgnoAgent, SmolAgent, CrewAIAgent]
    agent_type: Optional[AgentType] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: float = Field(default=60.0, ge=0.1)
    verbose: bool = Field(default=False)
    cache_config: Optional[Dict[str, Any]] = None
    
    # Private attributes
    cache: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    stats: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.agent_type is None:
            self.agent_type = self._detect_agent_type()
            
        # Configure Loguru logging level based on verbosity
        if self.verbose:
            logger.configure(handlers=[{
                "sink": sys.stdout,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> {extra}",
                "level": "DEBUG",
                "colorize": True,
            }])
        else:
            logger.configure(handlers=[{
                "sink": sys.stdout,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> {extra}",
                "level": "INFO",
                "colorize": True,
            }])
            
        # Initialize stats
        self.stats = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "cache_hits": 0
        }
        
        logger.info(f"Initialized {self.agent_type.value} agent wrapper")
        
    def _detect_agent_type(self) -> AgentType:
        """Detect the type of agent based on its class.
        
        Returns:
            AgentType: The detected agent type enum value
        
        Raises:
            ValueError: If the agent type is not supported
        """
        return AgentType.from_agent_instance(self.agent)

    @timed_execution
    async def act(self, prompt: str, **kwargs) -> AgentResponse:
        """Unified action method that works with any agent type.
        
        Args:
            prompt: The input prompt or query for the agent
            **kwargs: Additional arguments specific to the agent type
                - retry_on_error (bool): Whether to retry on error (default: True)
                - cache (bool): Whether to use caching (default: True if cache_config is set)
                - timeout (float): Custom timeout for this action
                - Additional agent-specific parameters
            
        Returns:
            AgentResponse: A standardized response object that works with all agent types
            
        Raises:
            TimeoutError: If the agent action times out
            ValueError: If the agent type is not supported
            Exception: Any exception from the underlying agent action
        """
        # Update stats
        self.stats["calls"] += 1
        
        # Extract general parameters
        retry_on_error = kwargs.pop('retry_on_error', True)
        use_cache = kwargs.pop('cache', self.cache_config is not None)
        custom_timeout = kwargs.pop('timeout', self.timeout)
        
        # Check cache if enabled
        if use_cache:
            cache_key = self._generate_cache_key(prompt, kwargs)
            if cache_key in self._cache:
                self.stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {self.agent_type.value} agent with prompt: {prompt[:50]}...")
                return self.cache[cache_key]
        
        # Execute with retries if enabled
        retries = self.max_retries if retry_on_error else 0
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                with agent_execution_context(self.agent_type, "action"):
                    # Set timeout for the execution
                    response_future = self._dispatch_agent_action(prompt, **kwargs)
                    response = await asyncio.wait_for(response_future, timeout=custom_timeout)
                    
                    # Create standardized response
                    agent_response = AgentResponse(
                        content=response,
                        metadata=self._get_agent_metadata(),
                        agent_type=self.agent_type,
                        success=True
                    )
                    
                    # Add execution metadata
                    agent_response.metadata.update({
                        "attempts": attempt + 1,
                        "prompt_length": len(prompt)
                    })
                    
                    # Update success stats
                    self.stats["successes"] += 1
                    
                    # Cache if enabled
                    if use_cache:
                        self.cache[cache_key] = agent_response
                        
                    return agent_response
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Agent action timed out after {custom_timeout} seconds")
                logger.warning(f"Timeout in {self.agent_type.value} agent action (attempt {attempt+1}/{retries+1})")
            except Exception as e:
                last_error = e
                logger.warning(f"Error in {self.agent_type.value} agent action (attempt {attempt+1}/{retries+1}): {str(e)}")
                
            # Only retry if not on the last attempt
            if attempt < retries:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying after {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
        # If we got here, all attempts failed
        self.stats["failures"] += 1
        
        error_response = AgentResponse(
            content=None,
            metadata={
                "error_type": type(last_error).__name__,
                "error_details": str(last_error),
                "attempts": retries + 1
            },
            agent_type=self.agent_type,
            success=False,
            error=str(last_error)
        )
        
        return error_response
        
    async def _dispatch_agent_action(self, prompt: str, **kwargs) -> Any:
        """Dispatch the action to the appropriate handler based on agent type.
        
        Args:
            prompt: The input prompt for the agent
            **kwargs: Additional parameters specific to the agent type
            
        Returns:
            Any: The raw response from the agent
            
        Raises:
            ValueError: If the agent type is not supported
        """
        # Use the generic handler system
        return await self._handle_action(prompt, **kwargs)
            
    def _generate_cache_key(self, prompt: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for the given prompt and parameters.
        
        Args:
            prompt: The input prompt
            params: The parameters for the action
            
        Returns:
            str: A unique cache key
        """
        # Create a simplified parameter dict with only serializable values
        simple_params = {}
        for k, v in params.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                simple_params[k] = v
                
        # Create a composite key from the agent type, prompt, and serializable params
        import hashlib
        import json
        
        key_parts = [
            self.agent_type.value,
            prompt,
            json.dumps(simple_params, sort_keys=True)
        ]
        
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()

    async def _get_agent_handler(self):
        """Get the appropriate handler for the current agent type.
        
        Returns:
            BaseAgentHandler: Handler instance for the current agent type
            
        Raises:
            ValueError: If the agent type is not supported
        """
        if self.agent_type == AgentType.AGNO:
            return AgnoAgentHandler(self.agent, verbose=self.verbose)
        elif self.agent_type == AgentType.SMOL:
            return SmolAgentHandler(self.agent, verbose=self.verbose)
        elif self.agent_type == AgentType.CREW:
            handler = CrewAgentHandler(self.agent, verbose=self.verbose)
            # Transfer any context from the wrapper to the handler
            if hasattr(self, 'transfer_context'):
                handler.transfer_context = self.transfer_context
            return handler
        else:
            raise ValueError(f"Unsupported agent type: {self.agent_type}")

    async def _handle_action(self, prompt: str, **kwargs) -> Any:
        """Handle an action for the agent using the appropriate handler.
        
        Args:
            prompt: The input prompt for the agent
            **kwargs: Agent-specific parameters
            
        Returns:
            The processed response from the agent
            
        Raises:
            ValueError: If the agent type is not supported
            Exception: Any exception from the underlying agent handler
        """
        handler = await self._get_agent_handler()
        return await handler.handle_action(prompt, **kwargs)

    async def _get_agent_metadata(self) -> Dict[str, Any]:
        """Get metadata specific to each agent type using the appropriate handler.
        
        Returns:
            Dict[str, Any]: A dictionary containing agent-specific metadata
        """
        # Get the handler for this agent type
        handler = await self._get_agent_handler()
        
        # Get the metadata from the handler
        metadata = handler.get_metadata()
        
        return metadata


class AgentCommunication:
    """Facilitates communication between different agent types.
    
    This class provides methods to transfer information between agents
    of different frameworks, enabling them to work together in a cohesive manner.
    
    The communication methods are implemented as static methods that can be used
    without instantiating the class. Each method provides a specific type of 
    interaction between agents, such as knowledge transfer or message relay.
    """
    
    # Configuration parameters
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    DEFAULT_TIMEOUT = 60.0
    
    @staticmethod
    @timed_execution
    async def transfer_knowledge(source_agent: AgentAPIWrapper, target_agent: AgentAPIWrapper, 
                                query: str, **kwargs) -> AgentResponse:
        """Transfer knowledge from source agent to target agent.
        
        This method queries the source agent with the provided query and transfers
        the resulting knowledge to the target agent in a format appropriate for its type.
        
        Args:
            source_agent: The agent to get knowledge from
            target_agent: The agent to transfer knowledge to
            query: The context or query for knowledge transfer
            **kwargs: Additional options including:
                - max_retries: Maximum number of retries (default: 3)
                - retry_delay: Delay between retries in seconds (default: 1.0)
                - timeout: Timeout for source agent actions (default: 60.0)
                - include_metadata: Whether to include metadata in the transfer (default: True)
                - format_template: Custom template for formatting knowledge (default: None)
            
        Returns:
            AgentResponse: A response object with success/failure status and transfer details
        """
        logger.info(f"Starting knowledge transfer from {source_agent.agent_type.value} to {target_agent.agent_type.value}")
        
        # Extract additional options
        max_retries = kwargs.pop('max_retries', AgentCommunication.MAX_RETRIES)
        retry_delay = kwargs.pop('retry_delay', AgentCommunication.RETRY_DELAY)
        timeout = kwargs.pop('timeout', AgentCommunication.DEFAULT_TIMEOUT)
        include_metadata = kwargs.pop('include_metadata', True)
        format_template = kwargs.pop('format_template', None)
        
        # Create a response object to track the transfer
        transfer_response = AgentResponse(
            content=None,
            metadata={
                "source_agent": source_agent.agent_type.value,
                "target_agent": target_agent.agent_type.value,
                "query": query,
                "transfer_started": datetime.now().isoformat()
            },
            agent_type=target_agent.agent_type,
            success=False,
            error=None
        )
        
        # Track attempts and errors
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Knowledge transfer attempt {attempt+1}/{max_retries+1}")
                
                # Configure source agent query options
                source_options = {
                    'timeout': timeout,
                    'add_references': True,
                    'retry_on_error': True
                }
                source_options.update(kwargs)
                
                # Get response from source agent
                with agent_execution_context(source_agent.agent_type, "knowledge generation"):
                    response = await source_agent.act(query, **source_options)
                
                # Check if the source agent's response was successful
                if not response.success:
                    error_msg = f"Source agent failed: {response.error or 'Unknown error'}"
                    logger.warning(error_msg)
                    
                    # Retry if not on last attempt
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        transfer_response.error = error_msg
                        return transfer_response
                
                # Prepare knowledge for transfer
                knowledge_content = response.content
                
                # Format knowledge if a template is provided
                if format_template:
                    if isinstance(format_template, str):
                        knowledge_content = format_template.format(
                            content=knowledge_content,
                            agent_type=source_agent.agent_type.value,
                            timestamp=datetime.now().isoformat()
                        )
                else:
                    # Default formatting
                    knowledge_content = f"Knowledge from {source_agent.agent_type.value} agent: {knowledge_content}"
                
                # Include metadata if requested
                transfer_metadata = {}
                if include_metadata and response.metadata:
                    transfer_metadata = {
                        f"source_{k}": v for k, v in response.metadata.items()
                    }
                
                # Transfer to target agent based on its type
                with agent_execution_context(target_agent.agent_type, "knowledge reception"):
                    transfer_success = False
                    
                    if target_agent.agent_type == AgentType.AGNO:
                        # For Agno, we can add to context
                        transfer_success = await AgentCommunication._transfer_to_agno(
                            target_agent.agent, knowledge_content, transfer_metadata)
                            
                    elif target_agent.agent_type == AgentType.SMOL:
                        # For Smol, we can add to memory
                        transfer_success = await AgentCommunication._transfer_to_smol(
                            target_agent.agent, knowledge_content, transfer_metadata)
                            
                    elif target_agent.agent_type == AgentType.CREW:
                        # For CrewAI, we set transfer_context
                        transfer_success = await AgentCommunication._transfer_to_crew(
                            target_agent, knowledge_content, transfer_metadata)
                    else:
                        error_msg = f"Unsupported target agent type: {target_agent.agent_type.value}"
                        logger.error(error_msg)
                        transfer_response.error = error_msg
                        return transfer_response
                
                # Update the response
                transfer_response.success = transfer_success
                transfer_response.content = knowledge_content
                transfer_response.metadata.update({
                    "transfer_complete": datetime.now().isoformat(),
                    "attempts": attempt + 1
                })
                
                if transfer_success:
                    logger.info(f"Knowledge successfully transferred to {target_agent.agent_type.value} agent")
                else:
                    logger.warning(f"Knowledge transfer to {target_agent.agent_type.value} agent failed")
                    transfer_response.error = "Failed to transfer knowledge to target agent"
                
                return transfer_response
                
            except Exception as e:
                error_msg = f"Error during knowledge transfer (attempt {attempt+1}): {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                
                # Retry if not on last attempt
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    transfer_response.error = error_msg
                    return transfer_response
        
        # This should not be reached, but just in case
        transfer_response.error = "Maximum retries exceeded"
        return transfer_response
    
    @staticmethod
    async def _transfer_to_agno(agent, knowledge_content: str, metadata: Dict[str, Any]) -> bool:
        """Helper method to transfer knowledge to an Agno agent.
        
        Args:
            agent: The Agno agent instance
            knowledge_content: The knowledge content to transfer
            metadata: Additional metadata to include
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if hasattr(agent, 'context'):
                # Initialize context if needed
                if not agent.context or not isinstance(agent.context, dict):
                    agent.context = {}
                    
                # Add the knowledge to context
                agent.context['transferred_knowledge'] = knowledge_content
                
                # Add metadata if possible
                if metadata and isinstance(metadata, dict):
                    agent.context['knowledge_metadata'] = metadata
                    
                return True
            return False
        except Exception as e:
            logger.error(f"Error transferring to Agno agent: {str(e)}")
            return False
    
    @staticmethod
    async def _transfer_to_smol(agent, knowledge_content: str, metadata: Dict[str, Any]) -> bool:
        """Helper method to transfer knowledge to a Smol agent.
        
        Args:
            agent: The Smol agent instance
            knowledge_content: The knowledge content to transfer
            metadata: Additional metadata to include
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if hasattr(agent, 'memory') and agent.memory is not None:
                try:
                    # Try to import Smol's message models
                    from smolagents.models import ChatMessage, MessageRole
                    
                    # Create content with metadata if available
                    full_content = knowledge_content
                    if metadata:
                        metadata_str = ", ".join([f"{k}: {v}" for k, v in metadata.items()])
                        full_content = f"{knowledge_content}\n\nMetadata: {metadata_str}"
                    
                    # Add as system message
                    agent.memory.add_message(
                        ChatMessage(role=MessageRole.SYSTEM, content=full_content)
                    )
                    return True
                except ImportError:
                    # Fallback if the import fails
                    if hasattr(agent.memory, 'add') and callable(agent.memory.add):
                        agent.memory.add({"role": "system", "content": knowledge_content})
                        return True
            return False
        except Exception as e:
            logger.error(f"Error transferring to Smol agent: {str(e)}")
            return False
    
    @staticmethod
    async def _transfer_to_crew(agent_wrapper, knowledge_content: str, metadata: Dict[str, Any]) -> bool:
        """Helper method to transfer knowledge to a CrewAI agent.
        
        Args:
            agent_wrapper: The CrewAI agent wrapper (not the agent itself)
            knowledge_content: The knowledge content to transfer
            metadata: Additional metadata to include
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For CrewAI, we store the knowledge in the wrapper's transfer_context
            agent_wrapper.transfer_context = knowledge_content
            
            # Store metadata if needed
            if metadata:
                if not hasattr(agent_wrapper, 'transfer_metadata'):
                    agent_wrapper.transfer_metadata = {}
                agent_wrapper.transfer_metadata.update(metadata)
                
            return True
        except Exception as e:
            logger.error(f"Error transferring to CrewAI agent: {str(e)}")
            return False
    
    @staticmethod
    @timed_execution
    async def relay_message(source_agent: AgentAPIWrapper, target_agent: AgentAPIWrapper, 
                           message: str, expect_response: bool = True, **kwargs) -> Optional[AgentResponse]:
        """Relay a message from one agent to another and optionally get a response.
        
        This method sends a message from the source agent to the target agent and,
        if requested, obtains a response from the target agent.
        
        Args:
            source_agent: The agent sending the message
            target_agent: The agent receiving the message
            message: The message to relay
            expect_response: Whether to get a response from the target agent
            **kwargs: Additional options including:
                - timeout: Timeout for the target agent action (default: 60.0)
                - message_template: Template for formatting the relayed message
                - include_source_metadata: Whether to include source agent metadata (default: False)
                - response_prefix: Text to prepend to the target agent's response (default: None)
            
        Returns:
            Optional[AgentResponse]: The response from the target agent if expect_response is True
        """
        logger.info(f"Relaying message from {source_agent.agent_type.value} to {target_agent.agent_type.value}")
        
        # Extract additional options
        timeout = kwargs.pop('timeout', AgentCommunication.DEFAULT_TIMEOUT)
        message_template = kwargs.pop('message_template', None)
        include_source_metadata = kwargs.pop('include_source_metadata', False)
        response_prefix = kwargs.pop('response_prefix', None)
        
        try:
            # Format the message
            if message_template:
                formatted_message = message_template.format(
                    message=message,
                    source=source_agent.agent_type.value,
                    target=target_agent.agent_type.value,
                    timestamp=datetime.now().isoformat()
                )
            else:
                # Default formatting
                formatted_message = f"Message from {source_agent.agent_type.value} agent: {message}"
            
            logger.debug(f"Formatted message: {formatted_message[:100]}...")
            
            # Extra metadata to include with the message
            extra_metadata = {}
            
            # Include source agent metadata if requested
            if include_source_metadata:
                source_metadata = source_agent._get_agent_metadata()
                if source_metadata:
                    extra_metadata.update({
                        f"source_{k}": v for k, v in source_metadata.items()
                    })
            
            # If we don't need a response, just log the message and return
            if not expect_response:
                logger.info(f"Message relayed to {target_agent.agent_type.value} (no response expected)")
                return AgentResponse(
                    content=None,
                    metadata={
                        "source_agent": source_agent.agent_type.value,
                        "target_agent": target_agent.agent_type.value,
                        "original_message": message,
                        "formatted_message": formatted_message,
                        "timestamp": datetime.now().isoformat()
                    },
                    agent_type=target_agent.agent_type,
                    success=True
                )
            
            # Send the message to the target agent and get a response
            with agent_execution_context(target_agent.agent_type, "message response"):
                # Configure target agent options
                target_options = {
                    'timeout': timeout,
                    'retry_on_error': True
                }
                target_options.update(kwargs)
                
                # Get response from target agent
                response = await target_agent.act(formatted_message, **target_options)
                
                # Add extra metadata to the response
                if extra_metadata and response.metadata:
                    response.metadata.update(extra_metadata)
                
                # Add response prefix if provided
                if response_prefix and response.content:
                    if isinstance(response.content, str):
                        response.content = f"{response_prefix} {response.content}"
                    elif isinstance(response.content, dict) and 'message' in response.content:
                        response.content['message'] = f"{response_prefix} {response.content['message']}"
                
                logger.info(f"Message relayed and response received from {target_agent.agent_type.value}")
                return response
                
        except Exception as e:
            error_msg = f"Error relaying message: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            
            return AgentResponse(
                content=None,
                metadata={
                    "source_agent": source_agent.agent_type.value,
                    "target_agent": target_agent.agent_type.value,
                    "original_message": message,
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                },
                agent_type=target_agent.agent_type,
                success=False,
                error=error_msg
            )
        
        if expect_response:
            # Get response from target agent
            return await target_agent.act(formatted_message)
        else:
            # Just deliver the message without expecting response
            await target_agent.act(formatted_message)
            return None
    
    @staticmethod
    @timed_execution
    async def collaborative_task(agents: List[AgentAPIWrapper], task: str, 
                           coordination_strategy: str = "sequential", **kwargs) -> AgentResponse:
        """Execute a task collaboratively using multiple agents.
        
        This method facilitates collaboration between multiple agents to solve a
        complex task. Different coordination strategies determine how the agents
        work together.
        
        Args:
            agents: List of agent wrappers to collaborate
            task: The task to execute collaboratively
            coordination_strategy: How to coordinate between agents:
                - "sequential": Each agent builds on the previous agent's work
                - "specialist": Each agent tackles a different aspect of the task
                - "debate": Agents engage in a discussion to solve the task
                - "consensus": Agents work to reach agreement on the task solution
            **kwargs: Additional options including:
                - timeout: Timeout for each agent action (default: 60.0)
                - max_iterations: Maximum number of iterations for debate/consensus (default: 3)
                - detailed_results: Whether to include detailed step-by-step results (default: False)
                - custom_templates: Templates for agent interactions (default: None)
                - error_handling: How to handle agent errors ("continue", "retry", "fail") (default: "continue")
                - max_retries: Maximum retries per agent action (default: 2)
            
        Returns:
            AgentResponse: A comprehensive response containing the collaborative result
                with metadata about the process and individual agent contributions
        """
        with logger.contextualize(strategy=coordination_strategy, agent_count=len(agents)):
            logger.info("Starting collaborative task")
        
        # Extract additional options
        timeout = kwargs.pop('timeout', AgentCommunication.DEFAULT_TIMEOUT)
        max_iterations = kwargs.pop('max_iterations', 3)
        detailed_results = kwargs.pop('detailed_results', False)
        custom_templates = kwargs.pop('custom_templates', None)
        error_handling = kwargs.pop('error_handling', "continue")
        max_retries = kwargs.pop('max_retries', 2)
        
        # Validate coordination strategy
        valid_strategies = ["sequential", "specialist", "debate", "consensus"]
        if coordination_strategy not in valid_strategies:
            error_msg = f"Invalid coordination strategy: {coordination_strategy}. Must be one of {valid_strategies}"
            logger.error("Invalid coordination strategy", strategy=coordination_strategy, valid_options=valid_strategies)
            return AgentResponse(
                content=None,
                metadata={
                    "task": task[:100] + "..." if len(task) > 100 else task,
                    "strategy": coordination_strategy,
                    "agent_count": len(agents),
                    "error": error_msg
                },
                agent_type=agents[0].agent_type if agents else None,
                success=False,
                error=error_msg
            )
        
        # Prepare result tracking
        results = {}
        context = task
        all_content = ""
        start_time = datetime.now()
        
        try:
            if coordination_strategy == "sequential":
                # Each agent builds on the previous agent's work
                sequential_results = await AgentCommunication._run_sequential_collaboration(
                    agents, task, timeout, max_retries, error_handling, custom_templates, kwargs
                )
                results = sequential_results["results"]
                all_content = sequential_results["combined_content"]
                
            elif coordination_strategy == "specialist":
                # Each agent tackles a different aspect of the task
                specialist_results = await AgentCommunication._run_specialist_collaboration(
                    agents, task, timeout, max_retries, error_handling, custom_templates, kwargs
                )
                results = specialist_results["results"]
                all_content = specialist_results["combined_content"]
                
            elif coordination_strategy == "debate":
                # Agents engage in a discussion to solve the task
                debate_results = await AgentCommunication._run_debate_collaboration(
                    agents, task, timeout, max_iterations, max_retries, error_handling, kwargs
                )
                results = debate_results["results"]
                all_content = debate_results["combined_content"]
                
            elif coordination_strategy == "consensus":
                # Agents work to reach agreement on a solution
                consensus_results = await AgentCommunication._run_consensus_collaboration(
                    agents, task, timeout, max_iterations, max_retries, error_handling, kwargs
                )
                results = consensus_results["results"]
                all_content = consensus_results["combined_content"]
            
            # Prepare the final response
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Create metadata about the collaboration
            collaboration_metadata = {
                "task": task[:100] + "..." if len(task) > 100 else task,
                "strategy": coordination_strategy,
                "agent_count": len(agents),
                "execution_time": execution_time,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            # Include detailed results if requested
            if detailed_results:
                collaboration_metadata["detailed_results"] = results
            else:
                collaboration_metadata["agent_summary"] = {
                    f"agent_{i+1}": {
                        "type": agent.agent_type.value,
                        "success": results.get(f"agent_{i+1}", {}).get("success", False)
                    } for i, agent in enumerate(agents)
                }
            
            logger.success(f"Collaborative task completed in {execution_time:.2f} seconds", execution_time=execution_time)
            
            return AgentResponse(
                content=all_content,
                metadata=collaboration_metadata,
                agent_type=agents[0].agent_type if agents else None,
                success=True
            )
                
        except Exception as e:
            error_msg = f"Error in collaborative task: {str(e)}"
            # Use Loguru's exception handling which automatically includes traceback
            logger.opt(exception=True).error("Collaborative task failed")
            
            return AgentResponse(
                content=None,
                metadata={
                    "task": task[:100] + "..." if len(task) > 100 else task,
                    "strategy": coordination_strategy,
                    "agent_count": len(agents),
                    "error_type": type(e).__name__,
                    "partial_results": results if results else None
                },
                agent_type=agents[0].agent_type if agents else None,
                success=False,
                error=error_msg
            )
