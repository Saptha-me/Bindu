"""
Simplified JSON-RPC protocol implementation for standardized agent communication.

This module provides a lightweight JSON-RPC adapter for the base AgentProtocol.
"""

import json
import base64
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import asyncio

import logging
import uvicorn
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    AgentStatus,
    ListenRequest,
    ViewRequest,
    StatusResponse,
    AudioArtifact,
    ImageArtifact,
    VideoArtifact,
    MessageRole
)

logger = logging.getLogger(__name__)


class JsonRpcAgentProtocol(AgentProtocol):
    """Simplified JSON-RPC implementation of the agent protocol."""
    
    def __init__(
        self,
        agent: Any,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        framework: str = "unknown",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        cors_origins: List[str] = ["*"]
    ):
        """Initialize the JSON-RPC agent protocol."""
        super().__init__(agent, agent_id, name, framework, capabilities, metadata)
        self.host = host
        self.port = port
        self.cors_origins = cors_origins
        self.app = FastAPI(title=f"{name} JSON-RPC API")
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register the JSON-RPC endpoint
        self.app.post("/jsonrpc")(self.handle_jsonrpc)
        
    async def handle_jsonrpc(self, request: Request) -> Response:
        """Handle JSON-RPC requests."""
        try:
            request_data = await request.json()
            
            # Basic JSON-RPC validation
            if not isinstance(request_data, dict) or request_data.get("jsonrpc") != "2.0":
                return self._error_response("Invalid JSON-RPC request", -32600, None)
            
            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")
            
            # Dispatch to appropriate handler
            if method == "get_status":
                result = await self._handle_get_status()
                
            elif method == "process_action":
                result = await self._handle_process_action(params)
                
            elif method == "process_request":
                result = await self._handle_process_request(params)
                
            else:
                return self._error_response(f"Method not found: {method}", -32601, request_id)
                
            return self._success_response(result, request_id)
            
        except json.JSONDecodeError:
            return self._error_response("Parse error", -32700, None)
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            return self._error_response(str(e), -32603, request_data.get("id") if "request_data" in locals() else None)
    
    def _success_response(self, result: Dict[str, Any], request_id: Any) -> Response:
        """Create a successful JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
        return Response(json.dumps(response), media_type="application/json")
    
    def _error_response(self, message: str, code: int, request_id: Any) -> Response:
        """Create an error JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
        return Response(json.dumps(response), media_type="application/json")
    
    async def _handle_get_status(self) -> Dict[str, Any]:
        """Handle get_status method."""
        status = self.get_status()
        return self._convert_status_to_dict(status)
    
    async def _handle_process_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process_action method."""
        try:
            action_request = ActionRequest(
                agent_id=UUID(params["agent_id"]),
                session_id=UUID(params.get("session_id", str(UUID()))),
                message=params["message"],
                role=MessageRole(params.get("role", "user")),
                stream=params.get("stream", False),
                metadata=params.get("metadata", {})
            )
            
            response = self.process_action(action_request)
            return self._convert_action_response_to_dict(response)
            
        except NotImplementedError:
            raise Exception("Action processing not implemented by this adapter")
    
    async def _handle_process_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process_request method - a unified method for all request types."""
        try:
            request_type = params.get("request_type", "").lower()
            
            if request_type == "text":
                # Handle text request using process_action
                action_request = ActionRequest(
                    agent_id=UUID(params["agent_id"]),
                    session_id=UUID(params.get("session_id", str(UUID()))),
                    message=params["message"],
                    role=MessageRole(params.get("role", "user")),
                    stream=params.get("stream", False),
                    metadata=params.get("metadata", {})
                )
                response = self.process_action(action_request)
                
            elif request_type == "audio":
                # Handle audio request using listen
                audio = self._create_audio_artifact(params)
                listen_request = ListenRequest(audio=audio)
                response = self.listen(listen_request)
                
            elif request_type in ["image", "video"]:
                # Handle image or video request using view
                media = self._create_media_artifact(request_type, params)
                view_request = ViewRequest(media_type=request_type, media=media)
                response = self.view(view_request)
                
            else:
                raise ValueError(f"Unknown request type: {request_type}")
                
            return self._convert_action_response_to_dict(response)
            
        except NotImplementedError:
            raise Exception(f"{request_type} processing not implemented by this adapter")
    
    def _create_audio_artifact(self, params: Dict[str, Any]) -> AudioArtifact:
        """Create an AudioArtifact from request parameters."""
        return AudioArtifact(
            id=UUID(),
            url=params.get("url"),
            base64_audio=params.get("content"),
            mime_type=params.get("mime_type")
        )
    
    def _create_media_artifact(self, media_type: str, params: Dict[str, Any]) -> Union[ImageArtifact, VideoArtifact]:
        """Create an ImageArtifact or VideoArtifact from request parameters."""
        if media_type == "image":
            return ImageArtifact(
                id=UUID(),
                url=params.get("url"),
                base64_image=params.get("content"),
                mime_type=params.get("mime_type"),
                width=params.get("width"),
                height=params.get("height"),
                alt_text=params.get("alt_text")
            )
        else:
            return VideoArtifact(
                id=UUID(),
                url=params.get("url"),
                base64_video=params.get("content"),
                mime_type=params.get("mime_type"),
                width=params.get("width"),
                height=params.get("height"),
                duration=params.get("duration")
            )
    
    def _convert_status_to_dict(self, status: StatusResponse) -> Dict[str, Any]:
        """Convert a StatusResponse to a simple dict."""
        result = {
            "agent_id": str(status.agent_id),
            "name": status.name,
            "framework": status.framework,
            "status": status.status.value,
            "capabilities": status.capabilities,
            "metadata": {}
        }
        
        # Convert complex metadata to simple string map
        if status.metadata:
            for k, v in status.metadata.items():
                result["metadata"][k] = str(v)
                
        return result
    
    def _convert_action_response_to_dict(self, response: ActionResponse) -> Dict[str, Any]:
        """Convert an ActionResponse to a simple dict."""
        result = {
            "agent_id": str(response.agent_id),
            "session_id": str(response.session_id),
            "message": response.message,
            "role": response.role.value,
            "metadata": {},
            "tool_calls": []
        }
        
        # Convert complex metadata to simple string map
        if response.metadata:
            for k, v in response.metadata.items():
                result["metadata"][k] = str(v)
        
        # Convert tool calls
        if response.tool_calls:
            for tc in response.tool_calls:
                tool_call = {
                    "name": tc.get("name", ""),
                    "arguments": {}
                }
                
                if "arguments" in tc:
                    for arg_key, arg_value in tc["arguments"].items():
                        tool_call["arguments"][arg_key] = str(arg_value)
                        
                result["tool_calls"].append(tool_call)
                
        return result
    
    def start_server(self):
        """Start the JSON-RPC server."""
        logger.info(f"Starting JSON-RPC server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    def stop_server(self):
        """Stop the JSON-RPC server."""
        logger.info("JSON-RPC server stopped")
        # Uvicorn handles shutdown automatically