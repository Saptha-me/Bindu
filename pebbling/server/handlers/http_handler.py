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
HTTP Handler for acp-style direct execution.

Handles HTTP REST requests with direct execution similar to the ACP project.
Provides simple, straightforward agent interaction patterns.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from pebbling.protocol.types import (
    AgentManifest, Task, TaskState, TaskStatus, Message, Role,
    RunMode
)
from pebbling.server.store import StoreManager

logger = logging.getLogger(__name__)


class HTTPHandler:
    """
    HTTP handler implementing acp-style direct execution.
    
    Provides REST endpoints for simple agent interaction without
    the complexity of JSON-RPC routing.
    """
    
    def __init__(self, store_manager: StoreManager):
        self.store_manager = store_manager
    
    # Agent management endpoints
    async def list_agents(self) -> Dict[str, Any]:
        """List all registered agents."""
        try:
            agents = await self.store_manager.list_agents()
            
            return {
                "agents": [
                    {
                        "id": str(agent.id),
                        "name": agent.name,
                        "description": agent.description,
                        "skills": [skill.model_dump() for skill in agent.skills] if agent.skills else [],
                        "capabilities": agent.capabilities.model_dump() if agent.capabilities else None
                    }
                    for agent in agents
                ]
            }
            
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent by ID."""
        try:
            agent = await self.store_manager.get_agent(agent_id)
            
            if agent is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Agent {agent_id} not found"
                )
            
            return {
                "id": str(agent.id),
                "name": agent.name,
                "description": agent.description,
                "user_id": str(agent.user_id),
                "skills": [skill.model_dump() for skill in agent.skills] if agent.skills else [],
                "capabilities": agent.capabilities.model_dump() if agent.capabilities else None,
                "version": agent.version
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def register_agent(self, manifest: AgentManifest) -> Dict[str, Any]:
        """Register a new agent."""
        try:
            await self.store_manager.register_agent(manifest)
            
            return {
                "id": str(manifest.id),
                "name": manifest.name,
                "status": "registered",
                "message": f"Agent {manifest.name} registered successfully"
            }
            
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Run/Task management endpoints (acp-style)
    async def create_run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create and execute a task (acp-style)."""
        try:
            # Extract request parameters
            agent_name = request.get("agent_name")
            input_data = request.get("input", {})
            session_id = request.get("session_id", str(uuid4()))
            mode = request.get("mode", "sync")  # sync, async, stream
            
            if not agent_name:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="agent_name is required"
                )
            
            # Find the agent
            agent = await self.store_manager.get_agent_by_name(agent_name)
            if agent is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Agent {agent_name} not found"
                )
            
            # Create the task
            task = await self.store_manager.create_task(
                session_id=session_id,
                agent_id=str(agent.id),
                input_data=input_data,
                protocol="http"
            )
            
            # For direct execution, immediately start processing
            # In a real implementation, this would trigger the agent
            task.status.state = TaskState.working
            await self.store_manager.update_task_status(task.id, task.status)
            
            # Return response based on mode
            response = {
                "run_id": task.id,
                "agent_name": agent_name,
                "session_id": session_id,
                "status": task.status.state.value,
                "mode": mode
            }
            
            if mode == "sync":
                # For sync mode, we'd wait for completion
                # For now, just simulate completion
                task.status.state = TaskState.completed
                await self.store_manager.update_task_status(task.id, task.status)
                response["status"] = "completed"
                response["result"] = {"message": "Task completed successfully"}
            
            elif mode == "stream":
                # For streaming mode, return stream URL
                response["stream_url"] = f"/stream/{task.id}"
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating run: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run/task by ID."""
        try:
            task = await self.store_manager.get_task(run_id)
            
            if task is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Run {run_id} not found"
                )
            
            return {
                "run_id": task.id,
                "session_id": str(task.contextId),
                "status": task.status.state.value,
                "created_at": task.status.timestamp,
                "metadata": task.metadata,
                "artifacts": [artifact.model_dump() for artifact in task.artifacts] if task.artifacts else [],
                "history": [msg.model_dump() for msg in task.history] if task.history else []
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting run {run_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def cancel_run(self, run_id: str) -> Dict[str, Any]:
        """Cancel a run/task."""
        try:
            success = await self.store_manager.cancel_task(run_id)
            
            if not success:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Run {run_id} not found or cannot be canceled"
                )
            
            return {
                "run_id": run_id,
                "status": "canceled",
                "message": "Run canceled successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error canceling run {run_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Session management
    async def get_session_runs(self, session_id: str) -> Dict[str, Any]:
        """Get all runs for a session."""
        try:
            tasks = await self.store_manager.get_session_tasks(session_id)
            
            return {
                "session_id": session_id,
                "runs": [
                    {
                        "run_id": task.id,
                        "status": task.status.state.value,
                        "created_at": task.status.timestamp,
                        "agent_id": task.metadata.get("agent_id") if task.metadata else None
                    }
                    for task in tasks
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting session runs: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def cleanup_session(self, session_id: str) -> Dict[str, Any]:
        """Clean up a session and its associated data."""
        try:
            success = await self.store_manager.cleanup_session(session_id)
            
            return {
                "session_id": session_id,
                "status": "cleaned" if success else "not_found",
                "message": "Session cleaned up successfully" if success else "Session not found"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
