"""
Authentication and agent retrieval utilities for the API routes.

This module provides utilities for API authentication and agent retrieval.
"""

from typing import Dict, Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from pebble.core.protocol import AgentProtocol
from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.security.auth import get_auth_token
from pebble.security.keys import validate_api_key

# Registry of deployed agents by auth token
# This would be populated during agent deployment
agent_registry: Dict[str, Union[AgentProtocol, CognitiveAgentProtocol]] = {}

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def register_agent(token: str, agent: Union[AgentProtocol, CognitiveAgentProtocol]) -> None:
    """Register an agent with an authentication token.
    
    Args:
        token: The authentication token
        agent: The agent to register
    """
    agent_registry[token] = agent


def get_token_from_header(
    api_key: str = Depends(get_auth_token)
) -> str:
    """Get and validate the authentication token.
    
    Args:
        api_key: API key from the auth header
        
    Returns:
        str: The validated token
    """
    return api_key


def get_agent_from_token(
    token: str = Depends(get_token_from_header)
) -> Union[AgentProtocol, CognitiveAgentProtocol]:
    """Get the agent associated with the authentication token.
    
    Args:
        token: The authentication token
        
    Returns:
        Union[AgentProtocol, CognitiveAgentProtocol]: The agent associated with the token
        
    Raises:
        HTTPException: If the token is not associated with an agent
    """
    if token not in agent_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent_registry[token]


def get_cognitive_agent_from_token(
    token: str = Depends(get_token_from_header)
) -> CognitiveAgentProtocol:
    """Get the cognitive agent associated with the authentication token.
    
    Args:
        token: The authentication token
        
    Returns:
        CognitiveAgentProtocol: The cognitive agent associated with the token
        
    Raises:
        HTTPException: If the token is not associated with a cognitive agent
    """
    agent = get_agent_from_token(token)
    
    if not isinstance(agent, CognitiveAgentProtocol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent does not support cognitive protocol"
        )
    
    return agent

# In auth.py
def validate_token_permissions(token, required_operation):
    """Validate that the token has permission for the specified operation."""
    if token not in token_permissions:
        return False
    return required_operation in token_permissions[token]

