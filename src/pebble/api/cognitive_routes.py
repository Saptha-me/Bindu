"""
API routes for cognitive agent operations.

This module defines the FastAPI routes for cognitive agent operations
like act, listen, see, and think.
"""

from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from pebble.api.auth import get_cognitive_agent_from_token, get_token_from_header
from pebble.schemas.models import (
    ActionRequest,
    ActionResponse,
    StimulusType
)
from pebble.core.protocol import CognitiveAgentProtocol


# Create API router for cognitive operations
router = APIRouter(
    prefix="/cognitive",
    tags=["cognitive"],
    responses={404: {"description": "Agent not found"}},
)

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@router.post("/act", response_model=ActionResponse)
async def agent_act(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent act in the environment.
    
    This endpoint allows the agent to take action based on its current cognitive state
    and the environmental context provided.
    
    Args:
        request: The action request containing context and parameters
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with action results and updated state
    """
    # Verify the agent has the 'act' capability
    if "act" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have the 'act' capability"
        )
    
    # Set stimulus type for cognitive processing
    if not request.stimulus_type:
        request.stimulus_type = StimulusType.ACTION
    
    # Process the request and return the response
    return agent.act(request)


@router.post("/listen", response_model=ActionResponse)
async def agent_listen(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent listen to verbal input.
    
    This endpoint allows the agent to process verbal input from another agent
    or human and update its cognitive state accordingly.
    
    Args:
        request: The action request containing the verbal input
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with updated cognitive state
    """
    # Verify the agent has the 'listen' capability
    if "listen" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have the 'listen' capability"
        )
    
    # Set stimulus type for cognitive processing
    if not request.stimulus_type:
        request.stimulus_type = StimulusType.AUDIO
    
    # Process the request and return the response
    return agent.listen(request)


@router.post("/see", response_model=ActionResponse)
async def agent_see(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent perceive a visual stimulus.
    
    This endpoint allows the agent to process visual input in the form of
    descriptions and update its cognitive state accordingly.
    
    Args:
        request: The action request containing the visual description
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with updated cognitive state
    """
    # Verify the agent has the 'see' capability
    if "see" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have the 'see' capability"
        )
    
    # Set stimulus type for cognitive processing
    if not request.stimulus_type:
        request.stimulus_type = StimulusType.VISUAL
    
    # Process the request and return the response
    return agent.view(request)


@router.post("/think", response_model=ActionResponse)
async def agent_think(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent think about a topic.
    
    This endpoint allows the agent to perform internal reflection and reasoning
    about a topic without taking external actions.
    
    Args:
        request: The action request containing the thinking topic
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with thinking results and updated state
    """
    # Verify the agent has the 'think' capability
    if "think" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have the 'think' capability"
        )
    
    # Set stimulus type for cognitive processing
    if not request.stimulus_type:
        request.stimulus_type = StimulusType.THOUGHT
    
    # Process the request and return the response
    return agent.think(request)


@router.post("/listen_and_act", response_model=ActionResponse)
async def agent_listen_and_act(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent listen and then act.
    
    This endpoint combines the listen and act methods for convenience.
    
    Args:
        request: The action request containing verbal input and action context
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with action results after listening
    """
    # Verify the agent has the required capabilities
    if "listen" not in agent.cognitive_capabilities or "act" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have both 'listen' and 'act' capabilities"
        )
    
    # Process the request and return the response
    return agent.listen_and_act(request)


@router.post("/see_and_act", response_model=ActionResponse)
async def agent_see_and_act(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent see and then act.
    
    This endpoint combines the see and act methods for convenience.
    
    Args:
        request: The action request containing visual input and action context
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with action results after seeing
    """
    # Verify the agent has the required capabilities
    if "see" not in agent.cognitive_capabilities or "act" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have both 'see' and 'act' capabilities"
        )
    
    # Process the request and return the response
    return agent.see_and_act(request)


@router.post("/think_and_act", response_model=ActionResponse)
async def agent_think_and_act(
    request: ActionRequest,
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> ActionResponse:
    """Make the agent think and then act.
    
    This endpoint combines the think and act methods for convenience.
    
    Args:
        request: The action request containing thinking topic and action context
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        ActionResponse: The response with action results after thinking
    """
    # Verify the agent has the required capabilities
    if "think" not in agent.cognitive_capabilities or "act" not in agent.cognitive_capabilities:
        raise HTTPException(
            status_code=400,
            detail="Agent does not have both 'think' and 'act' capabilities"
        )
    
    # Process the request and return the response
    return agent.think_and_act(request)


@router.get("/state", response_model=Dict[str, Any])
async def get_cognitive_state(
    agent: CognitiveAgentProtocol = Depends(get_cognitive_agent_from_token)
) -> Dict[str, Any]:
    """Get the current cognitive state of the agent.
    
    This endpoint returns the current cognitive state of the agent, including
    mental state, episodic memory, semantic memory, etc.
    
    Args:
        agent: The cognitive agent instance (obtained from auth token)
        
    Returns:
        Dict[str, Any]: The current cognitive state of the agent
    """
    return agent.cognitive_state
