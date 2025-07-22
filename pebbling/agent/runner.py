"""
Framework-agnostic agent runner for Pebbling framework.

This module provides utilities for running agents in different modes (sync, async, streaming)
regardless of their underlying implementation, using the standard Pebbling protocol.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

# Import existing protocol types
from pebbling.protocol.types import DataPart, Message, MessageSendConfiguration, Role, RunMode, TextPart


async def run_agent(
    agent_did: str,
    input_message: Union[str, Dict[str, Any], Message],
    mode: RunMode = RunMode.sync,
    history: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None
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
        
    Returns:
        Based on mode:
        - sync: Complete Message response
        - async: Task ID for later retrieval
        - stream: Generator that yields Message chunks
    """
    # Convert input to protocol Message if needed
    if isinstance(input_message, str):
        # Create a simple text message
        message = Message(
            role=Role.user,
            parts=[TextPart(content=input_message)]
        )
    elif isinstance(input_message, dict):
        # Convert dict to appropriate Message format
        if "content" in input_message:
            parts = [TextPart(content=input_message["content"])]
            if "data" in input_message:
                parts.append(DataPart(content="", data=input_message["data"]))
            message = Message(
                role=Role.user,
                parts=parts
            )
        else:
            # Assume it's already in the correct structure
            message = Message(**input_message)
    else:
        # Already a Message object
        message = input_message
    
    # Create send configuration using protocol types
    config = MessageSendConfiguration(
        acceptedOutputModes=[mode.value],
        blocking=mode == RunMode.sync,
        historyLength=len(history) if history else None
    )
    
    # Dispatch based on mode
    if mode == RunMode.sync:
        # Synchronous call
        return await _run_sync(agent_did, message, config, timeout)
    elif mode == RunMode.async_:
        # Asynchronous call (returns task ID)
        return await _run_async(agent_did, message, config)
    elif mode == RunMode.stream:
        # Streaming call (returns generator)
        return _run_stream(agent_did, message, config)
        
    raise ValueError(f"Unsupported run mode: {mode.value}")

# Implementation of the execution functions (placeholders)
async def _run_sync(agent_did, message, config, timeout):
    """Synchronous execution - waits for complete response"""
    # Implementation would resolve DID to endpoint and call agent
    pass

async def _run_async(agent_did, message, config):
    """Asynchronous execution - returns task ID immediately"""
    # Implementation would submit task and return ID
    pass

async def _run_stream(agent_did, message, config):
    """Streaming execution - yields response chunks as they arrive"""
    # Implementation would stream responses
    pass

# Additional helper functions for task management, result retrieval, etc.