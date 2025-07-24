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
Framework-agnostic agent runner for Pebbling framework.

This module provides utilities for running agents in different modes (sync, async, streaming)
regardless of their underlying implementation, using the standard Pebbling protocol.
"""

import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID

# Import existing protocol types
from pebbling.protocol.types import DataPart, Message, MessageSendConfiguration, Part, Role, RunMode, TextPart
from pebbling.agent.agent_adapter import AgentAdapter, PebblingContext, PebblingMessage
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.runner")

# Global registry of agent adapters by DID
_agent_registry: Dict[str, AgentAdapter] = {}


def register_agent_adapter(agent_did: str, adapter: AgentAdapter):
    """Register an agent adapter with the runner."""
    _agent_registry[agent_did] = adapter
    logger.debug(f"Registered agent adapter for DID: {agent_did}")


def get_agent_adapter(agent_did: str) -> Optional[AgentAdapter]:
    """Get an agent adapter by DID."""
    return _agent_registry.get(agent_did)


async def run_agent(
    agent_did: str,
    input_message: Union[str, Dict[str, Any], Message],
    mode: RunMode = RunMode.sync,
    history: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    context: Optional[PebblingContext] = None
) -> Union[Message, str, AsyncGenerator[Message, None]]:
    """
    Universal runner function for Pebble agents using the standard Pebbling protocol.
    
    Args:
        agent_did: DID of the agent to run
        input_message: String message, dict, or Message object
        mode: Execution mode (sync, async, stream)
        history: Optional conversation history
        metadata: Optional metadata for the request
        timeout: Optional timeout in seconds
        context: Optional execution context
        
    Returns:
        Based on mode:
        - sync: Complete Message response
        - async: Task ID for later retrieval
        - stream: Generator that yields Message chunks
    """
    # Get the agent adapter
    adapter = get_agent_adapter(agent_did)
    if not adapter:
        raise ValueError(f"No agent registered for DID: {agent_did}")
    
    # Convert input to protocol Message if needed
    pebbling_message = _convert_input_to_pebbling_message(input_message)
    
    # Create or use provided context
    if context is None:
        context = PebblingContext(
            agent_id=agent_did,
            metadata=metadata
        )
    
    # Add history to context if provided
    if history:
        for hist_item in history:
            if isinstance(hist_item, dict) and "content" in hist_item:
                hist_msg = PebblingMessage.from_text(hist_item["content"])
                context.add_to_history(hist_msg)
    
    # Dispatch based on mode
    if mode == RunMode.sync:
        # Synchronous call
        return await _run_sync(adapter, pebbling_message, context, timeout)
    elif mode == RunMode.async_:
        # Asynchronous call (returns task ID)
        return await _run_async(adapter, pebbling_message, context)
    elif mode == RunMode.stream:
        # Streaming call (returns generator)
        return _run_stream(adapter, pebbling_message, context)
        
    raise ValueError(f"Unsupported run mode: {mode.value}")


def _convert_input_to_pebbling_message(input_message: Union[str, Dict[str, Any], Message]) -> PebblingMessage:
    """Convert various input types to PebblingMessage."""
    if isinstance(input_message, str):
        # Create a simple text message
        return PebblingMessage.from_text(input_message, role=Role.user)
    elif isinstance(input_message, dict):
        # Convert dict to appropriate Message format
        if "content" in input_message:
            return PebblingMessage.from_text(input_message["content"], role=Role.user)
        elif "data" in input_message:
            return PebblingMessage.from_data(input_message["data"], role=Role.user)
        else:
            # Assume it's already in the correct structure
            message = Message(**input_message)
            return PebblingMessage(message)
    elif isinstance(input_message, Message):
        # Already a Message object
        return PebblingMessage(input_message)
    else:
        # Convert anything else to string
        return PebblingMessage.from_text(str(input_message), role=Role.user)


# Implementation of the execution functions
async def _run_sync(
    adapter: AgentAdapter, 
    message: PebblingMessage, 
    context: PebblingContext, 
    timeout: Optional[float]
) -> Message:
    """Execute request synchronously and wait for complete response."""
    logger.debug(f"Running agent '{adapter.agent_manifest.name}' in sync mode")
    
    # Collect all response messages
    response_parts = []
    
    async for response_msg in adapter.execute(message, context):
        # Extract parts from each response message
        for part in response_msg.raw_message.parts:
            response_parts.append(part)
        
        # Add to context history
        context.add_to_history(response_msg)
    
    # Create final combined message
    final_message = Message(
        contextId=message.context_id,
        messageId=uuid.uuid4(),
        role=Role.agent,
        parts=response_parts,
        metadata={"agent_did": adapter.agent_manifest.did if hasattr(adapter.agent_manifest, 'did') else None}
    )
    
    logger.debug(f"Sync execution completed for agent '{adapter.agent_manifest.name}'")
    return final_message


async def _run_async(
    adapter: AgentAdapter, 
    message: PebblingMessage, 
    context: PebblingContext
) -> str:
    """Execute request asynchronously and return task ID immediately."""
    import asyncio
    
    task_id = str(uuid.uuid4())
    logger.debug(f"Starting async execution for agent '{adapter.agent_manifest.name}' with task ID: {task_id}")
    
    # Store task for later retrieval (in a real implementation, this would use a proper task store)
    async def execute_task():
        try:
            results = []
            async for response_msg in adapter.execute(message, context):
                results.append(response_msg.raw_message)
                context.add_to_history(response_msg)
            
            # Store results for retrieval (placeholder - would use real storage)
            _store_task_result(task_id, results)
            logger.debug(f"Async execution completed for task: {task_id}")
        except Exception as e:
            logger.error(f"Async execution failed for task {task_id}: {e}")
            _store_task_error(task_id, str(e))
    
    # Start the task in the background
    asyncio.create_task(execute_task())
    
    return task_id


async def _run_stream(
    adapter: AgentAdapter, 
    message: PebblingMessage, 
    context: PebblingContext
) -> AsyncGenerator[Message, None]:
    """Stream response chunks as they arrive from the agent."""
    logger.debug(f"Starting stream execution for agent '{adapter.agent_manifest.name}'")
    
    async for response_msg in adapter.execute(message, context):
        # Add to context history
        context.add_to_history(response_msg)
        
        # Yield the raw protocol message
        yield response_msg.raw_message
    
    logger.debug(f"Stream execution completed for agent '{adapter.agent_manifest.name}'")


# Task storage functions (placeholder implementations)
_task_results: Dict[str, Any] = {}
_task_errors: Dict[str, str] = {}


def _store_task_result(task_id: str, results: List[Message]):
    """Store task results for later retrieval."""
    _task_results[task_id] = results


def _store_task_error(task_id: str, error: str):
    """Store task error for later retrieval."""
    _task_errors[task_id] = error


def get_task_result(task_id: str) -> Optional[List[Message]]:
    """Retrieve task results by ID."""
    return _task_results.get(task_id)


def get_task_error(task_id: str) -> Optional[str]:
    """Retrieve task error by ID."""
    return _task_errors.get(task_id)


# Additional helper functions for agent management
def list_registered_agents() -> List[str]:
    """List all registered agent DIDs."""
    return list(_agent_registry.keys())


def unregister_agent(agent_did: str) -> bool:
    """Unregister an agent adapter."""
    if agent_did in _agent_registry:
        del _agent_registry[agent_did]
        logger.debug(f"Unregistered agent adapter for DID: {agent_did}")
        return True
    return False