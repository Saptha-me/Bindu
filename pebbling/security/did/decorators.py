"""Decorators for adding security features to agents."""

import os
import functools
import uuid
import inspect
from typing import Any, Optional, Callable

from pebbling.security.did.manager import DIDManager

def with_did(
    key_path: Optional[str] = None, 
    endpoint: Optional[str] = None
) -> Callable:
    """
    Decorator to add DID capabilities to an agent.
    
    This decorator automatically:
    1. Generates a key pair (or loads existing)
    2. Creates a DID document
    
    Can be used either directly on an agent object or on a function that returns an agent.
    
    Args:
        key_path: Optional path to save/load the key file
        endpoint: Optional service endpoint to include in the DID document
        
    Returns:
        Decorated agent with DID capabilities
    """
    def decorator(obj: Any) -> Any:
        # Check if obj is a function (agent factory) or an agent object
        if inspect.isfunction(obj):
            # It's a function that returns an agent, create a wrapper
            @functools.wraps(obj)
            def wrapper(*args, **kwargs):
                # Get the agent from the original function
                agent = obj(*args, **kwargs)
                
                # Apply DID capabilities to the returned agent
                return _apply_did_to_agent(agent, key_path, endpoint)
                
            return wrapper
        else:
            # It's already an agent object
            return _apply_did_to_agent(obj, key_path, endpoint)
    
    return decorator

def _apply_did_to_agent(agent: Any, key_path: Optional[str], endpoint: Optional[str]) -> Any:
    """Apply DID capabilities to an agent object."""
    # Generate a unique key path if not provided
    if key_path is None:
        # Create keys directory if it doesn't exist
        os.makedirs('keys', exist_ok=True)
        
        # Generate agent-specific filename
        agent_id = getattr(agent, 'name', str(uuid.uuid4()))
        key_path = f"keys/{agent_id}_key.json"
    
    # Create and attach the DID manager
    did_manager = DIDManager(key_path=key_path, endpoint=endpoint)
    
    setattr(agent, 'pebble_did_manager', did_manager)
    setattr(agent, 'pebble_did', did_manager.get_did())
    setattr(agent, 'pebble_did_document', did_manager.get_did_document())
    
    return agent