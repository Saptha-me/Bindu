from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from ..wrappers import AgentAPIWrapper
from ...core.cognitive_agent import CognitiveAgent

class BaseRequest(BaseModel):
    """Base request model for cognitive agent endpoints."""
    stream: bool = False
    kwargs: Optional[Dict[str, Any]] = None

class TextRequest(BaseRequest):
    """Request model for text-based inputs."""
    text: str

class VisualRequest(BaseRequest):
    """Request model for visual inputs."""
    visual_input: Union[str, Dict[str, Any]]

class ThoughtRequest(BaseRequest):
    """Request model for thought prompts."""
    thought: str

class GoalRequest(BaseRequest):
    """Request model for goal setting."""
    goal: str

class CognitiveStateUpdateRequest(BaseRequest):
    """Request model for cognitive state updates."""
    updates: Dict[str, Any]

class MemoryQueryRequest(BaseRequest):
    """Request model for memory retrieval."""
    query: Optional[str] = None
    limit: int = 5

def get_cognitive_agent(agent_wrapper: AgentAPIWrapper = Depends()) -> CognitiveAgent:
    """Dependency to get the cognitive agent."""
    if not agent_wrapper or not isinstance(agent_wrapper.agent, CognitiveAgent):
        raise HTTPException(
            status_code=400, 
            detail="Cognitive agent not initialized. Make sure you're using a CognitiveAgent instance."
        )
    return agent_wrapper.agent

def create_cognitive_router() -> APIRouter:
    """Create a router for cognitive agent endpoints."""
    router = APIRouter(prefix="/cognitive", tags=["Cognitive Agent"])

    # === Main API Endpoints ===
    
    @router.post("/act")
    async def act(request: TextRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Execute an action with the cognitive agent."""
        try:
            if request.stream:
                return StreamingResponse(
                    agent.act(request.text, **request.kwargs or {}),
                    media_type="text/event-stream"
                )
            
            response = await agent.act(
                prompt=request.text,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing action: {str(e)}"
            )
    
    @router.post("/listen")
    async def listen(request: TextRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Process input with the listen capability."""
        try:
            response = agent.listen(
                input_text=request.text,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing listen: {str(e)}"
            )
    
    @router.post("/think")
    async def think(request: ThoughtRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Process a thought with the thinking capability."""
        try:
            response = agent.think(
                thought_prompt=request.thought,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing thought: {str(e)}"
            )
    
    @router.post("/see")
    async def see(request: VisualRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Process visual input with the seeing capability."""
        try:
            response = agent.see(
                visual_input=request.visual_input,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing visual input: {str(e)}"
            )
    
    @router.post("/internalize_goal")
    async def internalize_goal(request: GoalRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Set and internalize a new goal."""
        try:
            response = agent.internalize_goal(
                goal=request.goal,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error internalizing goal: {str(e)}"
            )
    
    # === Composite API Endpoints ===
    
    @router.post("/listen_and_act")
    async def listen_and_act(request: TextRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Listen to input and then take action."""
        try:
            response = agent.listen_and_act(
                input_text=request.text,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error in listen and act: {str(e)}"
            )
    
    @router.post("/see_and_act")
    async def see_and_act(request: VisualRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Process visual input and then take action."""
        try:
            response = agent.see_and_act(
                visual_input=request.visual_input,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error in see and act: {str(e)}"
            )
    
    @router.post("/think_and_act")
    async def think_and_act(request: ThoughtRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Think and then take action."""
        try:
            response = agent.think_and_act(
                thought_prompt=request.thought,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error in think and act: {str(e)}"
            )
    
    # === Memory API Endpoints ===
    
    @router.post("/update_cognitive_state")
    async def update_cognitive_state(request: CognitiveStateUpdateRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Update the agent's cognitive state."""
        try:
            response = agent.update_cognitive_state(
                updates=request.updates,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error updating cognitive state: {str(e)}"
            )
    
    @router.post("/retrieve_recent_memories")
    async def retrieve_recent_memories(request: MemoryQueryRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Retrieve recent memories from episodic memory."""
        try:
            response = agent.retrieve_recent_memories(
                limit=request.limit,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving recent memories: {str(e)}"
            )
    
    @router.post("/retrieve_relevant_memories")
    async def retrieve_relevant_memories(request: MemoryQueryRequest, agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Retrieve memories relevant to the query."""
        try:
            if not request.query:
                raise HTTPException(
                    status_code=400,
                    detail="Query parameter is required for relevant memory retrieval"
                )
                
            response = agent.retrieve_relevant_memories(
                query=request.query,
                limit=request.limit,
                **request.kwargs or {}
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving relevant memories: {str(e)}"
            )
    
    @router.get("/state")
    async def get_cognitive_state(agent: CognitiveAgent = Depends(get_cognitive_agent)):
        """Get the current cognitive state of the agent."""
        return {
            "cognitive_state": agent.cognitive_state,
            "current_goal": agent.current_goal,
            "goal_stack": agent.goal_stack,
            "action_buffer_size": len(agent.action_buffer)
        }
    
    return router
