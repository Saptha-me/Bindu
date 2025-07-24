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
Streaming Handler for Server-Sent Events.

Handles streaming responses for both JSON-RPC and HTTP protocols
using Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sse_starlette.sse import EventSourceResponse
from starlette.status import HTTP_404_NOT_FOUND

from pebbling.protocol.types import Task, TaskState, TaskStatusUpdateEvent, TaskArtifactUpdateEvent
from pebbling.server.store import StoreManager

logger = logging.getLogger(__name__)


class StreamingHandler:
    """
    Streaming handler for Server-Sent Events.
    
    Provides real-time streaming of task updates and session events
    for both JSON-RPC and HTTP protocols.
    """
    
    def __init__(self, store_manager: StoreManager):
        self.store_manager = store_manager
        self._active_streams: Dict[str, set] = {}  # task_id -> set of stream generators
    
    async def stream_task(self, task_id: str) -> EventSourceResponse:
        """Stream updates for a specific task."""
        try:
            # Verify task exists
            task = await self.store_manager.get_task(task_id)
            if task is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )
            
            # Create the streaming generator
            async def generate_task_events():
                # Send initial task state
                yield {
                    "event": "task-status",
                    "data": json.dumps({
                        "task_id": task_id,
                        "status": task.status.state.value,
                        "timestamp": task.status.timestamp,
                        "initial": True
                    })
                }
                
                # Monitor task for updates
                last_status = task.status.state
                while True:
                    try:
                        # Check for task updates
                        current_task = await self.store_manager.get_task(task_id)
                        if current_task is None:
                            break
                        
                        # Send status update if changed
                        if current_task.status.state != last_status:
                            yield {
                                "event": "task-status",
                                "data": json.dumps({
                                    "task_id": task_id,
                                    "status": current_task.status.state.value,
                                    "timestamp": current_task.status.timestamp,
                                    "previous_status": last_status.value
                                })
                            }
                            last_status = current_task.status.state
                        
                        # Send artifacts if available
                        if current_task.artifacts:
                            for artifact in current_task.artifacts:
                                yield {
                                    "event": "task-artifact",
                                    "data": json.dumps({
                                        "task_id": task_id,
                                        "artifact": artifact.model_dump()
                                    })
                                }
                        
                        # Check if task is in terminal state
                        if current_task.status.state in [
                            TaskState.completed, TaskState.failed, 
                            TaskState.canceled, TaskState.rejected
                        ]:
                            yield {
                                "event": "task-complete",
                                "data": json.dumps({
                                    "task_id": task_id,
                                    "final_status": current_task.status.state.value,
                                    "timestamp": current_task.status.timestamp
                                })
                            }
                            break
                        
                        # Wait before next check
                        await asyncio.sleep(1.0)
                        
                    except Exception as e:
                        logger.error(f"Error in task stream {task_id}: {e}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "task_id": task_id,
                                "error": str(e)
                            })
                        }
                        break
            
            return EventSourceResponse(generate_task_events())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting up task stream: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def stream_session(self, session_id: str) -> EventSourceResponse:
        """Stream updates for all tasks in a session."""
        try:
            # Verify session exists
            session = await self.store_manager.get_or_create_session(session_id)
            
            async def generate_session_events():
                # Send initial session state
                tasks = await self.store_manager.get_session_tasks(session_id)
                yield {
                    "event": "session-init",
                    "data": json.dumps({
                        "session_id": session_id,
                        "active_tasks": len(tasks),
                        "task_ids": [task.id for task in tasks]
                    })
                }
                
                # Track task states
                task_states = {task.id: task.status.state for task in tasks}
                
                while True:
                    try:
                        # Get current tasks
                        current_tasks = await self.store_manager.get_session_tasks(session_id)
                        
                        # Check for new tasks
                        current_task_ids = {task.id for task in current_tasks}
                        previous_task_ids = set(task_states.keys())
                        
                        new_task_ids = current_task_ids - previous_task_ids
                        for task_id in new_task_ids:
                            task = next(t for t in current_tasks if t.id == task_id)
                            task_states[task_id] = task.status.state
                            yield {
                                "event": "task-created",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "task_id": task_id,
                                    "agent_id": task.metadata.get("agent_id") if task.metadata else None,
                                    "status": task.status.state.value
                                })
                            }
                        
                        # Check for task status changes
                        for task in current_tasks:
                            if task.id in task_states and task.status.state != task_states[task.id]:
                                old_state = task_states[task.id]
                                task_states[task.id] = task.status.state
                                
                                yield {
                                    "event": "task-status-change",
                                    "data": json.dumps({
                                        "session_id": session_id,
                                        "task_id": task.id,
                                        "status": task.status.state.value,
                                        "previous_status": old_state.value,
                                        "timestamp": task.status.timestamp
                                    })
                                }
                        
                        # Send periodic heartbeat
                        active_tasks = [
                            task for task in current_tasks 
                            if task.status.state not in [
                                TaskState.completed, TaskState.failed, 
                                TaskState.canceled, TaskState.rejected
                            ]
                        ]
                        
                        yield {
                            "event": "session-heartbeat",
                            "data": json.dumps({
                                "session_id": session_id,
                                "active_tasks": len(active_tasks),
                                "total_tasks": len(current_tasks),
                                "timestamp": str(asyncio.get_event_loop().time())
                            })
                        }
                        
                        # Wait before next check
                        await asyncio.sleep(2.0)
                        
                    except Exception as e:
                        logger.error(f"Error in session stream {session_id}: {e}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "session_id": session_id,
                                "error": str(e)
                            })
                        }
                        break
            
            return EventSourceResponse(generate_session_events())
            
        except Exception as e:
            logger.error(f"Error setting up session stream: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def stream_agent_context(self, session_id: str, agent_id: str) -> EventSourceResponse:
        """Stream updates for a specific agent context within a session."""
        try:
            # Verify agent context exists
            context = await self.store_manager.get_or_create_agent_context(session_id, agent_id)
            
            async def generate_agent_events():
                # Send initial context state
                yield {
                    "event": "agent-context-init",
                    "data": json.dumps({
                        "session_id": session_id,
                        "agent_id": agent_id,
                        "conversation_length": len(context.conversation_history),
                        "task_count": len(context.task_history)
                    })
                }
                
                # Track context changes
                last_conversation_length = len(context.conversation_history)
                last_task_count = len(context.task_history)
                
                while True:
                    try:
                        # Get current context
                        current_context = await self.store_manager.get_agent_context(session_id, agent_id)
                        if current_context is None:
                            break
                        
                        # Check for new messages
                        if len(current_context.conversation_history) > last_conversation_length:
                            new_messages = current_context.conversation_history[last_conversation_length:]
                            for message in new_messages:
                                yield {
                                    "event": "new-message",
                                    "data": json.dumps({
                                        "session_id": session_id,
                                        "agent_id": agent_id,
                                        "message": message.model_dump()
                                    })
                                }
                            last_conversation_length = len(current_context.conversation_history)
                        
                        # Check for new tasks
                        if len(current_context.task_history) > last_task_count:
                            new_task_ids = current_context.task_history[last_task_count:]
                            for task_id in new_task_ids:
                                yield {
                                    "event": "new-task",
                                    "data": json.dumps({
                                        "session_id": session_id,
                                        "agent_id": agent_id,
                                        "task_id": task_id
                                    })
                                }
                            last_task_count = len(current_context.task_history)
                        
                        # Wait before next check
                        await asyncio.sleep(1.5)
                        
                    except Exception as e:
                        logger.error(f"Error in agent context stream: {e}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "error": str(e)
                            })
                        }
                        break
            
            return EventSourceResponse(generate_agent_events())
            
        except Exception as e:
            logger.error(f"Error setting up agent context stream: {e}")
            raise HTTPException(status_code=500, detail=str(e))
