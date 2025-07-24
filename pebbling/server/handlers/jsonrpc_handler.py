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
JSON-RPC Handler for a2a-style complex routing.

Handles JSON-RPC requests with sophisticated routing similar to the a2a project.
Supports message sending, task management, and streaming operations.
"""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request
from pebbling.protocol.types import (
    PebblingRequest, JSONRPCResponse, JSONRPCErrorResponse,
    SendMessageRequest, SendStreamingMessageRequest,
    GetTaskRequest, CancelTaskRequest, TaskResubscriptionRequest,
    TrustVerificationRequest,
    SendMessageSuccessResponse, GetTaskSuccessResponse, CancelTaskSuccessResponse,
    Task, TaskState, TaskStatus, Message, Role,
    MethodNotFoundError, TaskNotFoundError, InvalidParamsError
)
from pebbling.server.store import StoreManager

logger = logging.getLogger(__name__)


class JSONRPCHandler:
    """
    JSON-RPC handler implementing a2a-style complex routing.
    
    Routes requests through method-specific handlers and aggregates results.
    """
    
    def __init__(self, store_manager: StoreManager):
        self.store_manager = store_manager
    
    async def handle_request(self, request: PebblingRequest, http_request: Request) -> JSONRPCResponse:
        """
        Main request handler that routes to appropriate method handlers.
        
        Args:
            request: Validated Pebbling JSON-RPC request
            http_request: Original HTTP request for context
            
        Returns:
            JSON-RPC response (success or error)
        """
        request_obj = request.root
        request_id = getattr(request_obj, 'id', None)
        
        try:
            # Route based on method
            if isinstance(request_obj, SendMessageRequest):
                return await self._handle_message_send(request_obj, http_request)
            
            elif isinstance(request_obj, SendStreamingMessageRequest):
                return await self._handle_streaming_message_send(request_obj, http_request)
            
            elif isinstance(request_obj, GetTaskRequest):
                return await self._handle_get_task(request_obj, http_request)
            
            elif isinstance(request_obj, CancelTaskRequest):
                return await self._handle_cancel_task(request_obj, http_request)
            
            elif isinstance(request_obj, TaskResubscriptionRequest):
                return await self._handle_task_resubscription(request_obj, http_request)
            
            elif isinstance(request_obj, TrustVerificationRequest):
                return await self._handle_trust_verification(request_obj, http_request)
            
            else:
                logger.error(f"Unknown request type: {type(request_obj)}")
                return JSONRPCErrorResponse(
                    id=request_id,
                    error=MethodNotFoundError(message=f"Method not supported: {type(request_obj).__name__}")
                )
        
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            return JSONRPCErrorResponse(
                id=request_id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_message_send(self, request: SendMessageRequest, http_request: Request) -> JSONRPCResponse:
        """Handle message/send requests."""
        try:
            # Extract session from request context or create new one
            session_id = str(request.params.message.contextId)
            
            # Get or create agent context
            # For now, we'll use a default agent ID from the message metadata
            agent_id = request.params.message.metadata.get("agent_id", "default-agent") if request.params.message.metadata else "default-agent"
            
            # Create a task for this message
            task = await self.store_manager.create_task(
                session_id=session_id,
                agent_id=agent_id,
                input_data={
                    "message": request.params.message.model_dump(),
                    "configuration": request.params.configuration.model_dump() if request.params.configuration else None
                },
                protocol="json-rpc"
            )
            
            # Add message to conversation history
            await self.store_manager.add_message_to_context(session_id, agent_id, request.params.message)
            
            # For now, we'll simulate task processing
            # In a real implementation, this would trigger agent execution
            task.status.state = TaskState.working
            await self.store_manager.update_task_status(task.id, task.status)
            
            # Return success response
            return SendMessageSuccessResponse(
                id=request.id,
                result=task
            )
            
        except Exception as e:
            logger.error(f"Error in message_send: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_streaming_message_send(self, request: SendStreamingMessageRequest, http_request: Request) -> JSONRPCResponse:
        """Handle message/stream requests."""
        # For streaming, we'd typically return a different response type
        # For now, treat it similar to regular message send but mark for streaming
        try:
            session_id = str(request.params.message.contextId)
            agent_id = request.params.message.metadata.get("agent_id", "default-agent") if request.params.message.metadata else "default-agent"
            
            task = await self.store_manager.create_task(
                session_id=session_id,
                agent_id=agent_id,
                input_data={
                    "message": request.params.message.model_dump(),
                    "streaming": True
                },
                protocol="json-rpc-stream"
            )
            
            await self.store_manager.add_message_to_context(session_id, agent_id, request.params.message)
            
            return SendMessageSuccessResponse(
                id=request.id,
                result=task
            )
            
        except Exception as e:
            logger.error(f"Error in streaming_message_send: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_get_task(self, request: GetTaskRequest, http_request: Request) -> JSONRPCResponse:
        """Handle tasks/get requests."""
        try:
            task = await self.store_manager.get_task(str(request.params.id))
            
            if task is None:
                return JSONRPCErrorResponse(
                    id=request.id,
                    error=TaskNotFoundError(message=f"Task {request.params.id} not found")
                )
            
            return GetTaskSuccessResponse(
                id=request.id,
                result=task
            )
            
        except Exception as e:
            logger.error(f"Error in get_task: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_cancel_task(self, request: CancelTaskRequest, http_request: Request) -> JSONRPCResponse:
        """Handle tasks/cancel requests."""
        try:
            task_id = str(request.params.id)
            success = await self.store_manager.cancel_task(task_id)
            
            if not success:
                return JSONRPCErrorResponse(
                    id=request.id,
                    error=TaskNotFoundError(message=f"Task {task_id} not found or cannot be canceled")
                )
            
            # Get the updated task
            task = await self.store_manager.get_task(task_id)
            
            return CancelTaskSuccessResponse(
                id=request.id,
                result=task
            )
            
        except Exception as e:
            logger.error(f"Error in cancel_task: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_task_resubscription(self, request: TaskResubscriptionRequest, http_request: Request) -> JSONRPCResponse:
        """Handle tasks/resubscribe requests."""
        # This would typically set up streaming for existing tasks
        # For now, return a simple success response
        try:
            return JSONRPCErrorResponse(
                id=request.id,
                error=MethodNotFoundError(message="Task resubscription not yet implemented")
            )
            
        except Exception as e:
            logger.error(f"Error in task_resubscription: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
    
    async def _handle_trust_verification(self, request: TrustVerificationRequest, http_request: Request) -> JSONRPCResponse:
        """Handle trust/verify requests."""
        # Trust verification would integrate with your DID system
        # For now, return a placeholder response
        try:
            return JSONRPCErrorResponse(
                id=request.id,
                error=MethodNotFoundError(message="Trust verification not yet implemented")
            )
            
        except Exception as e:
            logger.error(f"Error in trust_verification: {e}")
            return JSONRPCErrorResponse(
                id=request.id,
                error=InvalidParamsError(message=str(e))
            )
