from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from ..wrappers import AgentAPIWrapper, AgentResponse

class ActionRequest(BaseModel):
    """Request model for agent actions."""
    prompt: str
    stream: bool = True
    kwargs: Optional[Dict[str, Any]] = None

def get_agent_wrapper(agent_wrapper: AgentAPIWrapper = Depends()):
    if not agent_wrapper:
        raise HTTPException(status_code=400, detail="Agent wrapper not initialized")
    return agent_wrapper

def create_agent_router() -> APIRouter:
    """Create a router for agent endpoints."""
    router = APIRouter(prefix="/agent", tags=["Agent"])

    @router.post("/act", response_model=AgentResponse)
    async def act(request: ActionRequest, agent: AgentAPIWrapper = Depends(get_agent_wrapper)):
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

    @router.get("/info")
    async def get_info(agent: AgentAPIWrapper = Depends(get_agent_wrapper)):
        """Get information about the agent."""
        return {
            "agent_type": agent.agent_type,
            "metadata": agent._get_agent_metadata()
        }

    @router.post("/act", response_model=ActionResponse)
    async def act(request: ActionRequest):
        """Execute an action with the agent."""
        try:
            # Process the action using the agent's core logic
            result = agent.act(
                prompt=request.prompt,
                stream=request.stream,
                context=request.context,
                tools=request.tools,
                memory=request.memory
            )
            
            return ActionResponse(
                status="success" if result["status"] == "success" else "error",
                response=result.get("response"),
                mental_state=result.get("mental_state"),
                error=result.get("error")
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing action: {str(e)}"
            )

    @router.get("/status")
    async def get_status():
        """Get the current status of the agent."""
        return {
            "status": "active",
            "name": agent.name,
            "mental_state": agent.mental_state,
            "action_buffer_size": len(agent.action_buffer)
        }

    return router
