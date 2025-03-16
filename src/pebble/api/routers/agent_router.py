from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union, Callable
from datetime import datetime

from ..wrappers import AgentAPIWrapper, AgentResponse

class ActionRequest(BaseModel):
    """Request model for agent actions."""
    prompt: str
    stream: bool = True
    kwargs: Optional[Dict[str, Any]] = None

def get_agent_wrapper():
    """Dependency to get the agent wrapper.
    This will be overridden at runtime with the actual agent wrapper.
    """
    return None

def create_agent_router() -> APIRouter:
    """Create a router for agent endpoints."""
    router = APIRouter(prefix="/agent", tags=["Agent"])

    @router.post("/act")
    async def act(request: ActionRequest, agent: Any = Depends(get_agent_wrapper)):
        """Execute an action with the agent."""
        try:
            if request.stream:
                return StreamingResponse(
                    agent.act(request.prompt, **request.kwargs or {}),
                    media_type="text/event-stream"
                )
            
            response = await agent.act(
                prompt=request.prompt,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing action: {str(e)}"
            )

    @router.get("/status")
    async def get_status(agent: Any = Depends(get_agent_wrapper)):
        """Get the current status of the agent."""
        return {
            "status": "active",
            "name": agent.agent.name,  # Access name through the agent instance in the handler
            "metadata": agent.get_metadata()
        }

    return router
