"""
Simplified gRPC protocol implementation for standardized agent communication.

This module provides a lightweight gRPC adapter for the base AgentProtocol.
"""

import grpc
from concurrent import futures
import base64
from typing import Any, Dict, List, Optional
from uuid import UUID

import logging
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

# Import the generated gRPC stubs
from pebble.protos import agent_pb2, agent_pb2_grpc

logger = logging.getLogger(__name__)


class GrpcAgentProtocol(AgentProtocol):
    """Simplified gRPC implementation of the agent protocol."""
    
    def __init__(
        self,
        agent: Any,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        framework: str = "unknown",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        host: str = "0.0.0.0",
        port: int = 50051,
        max_workers: int = 10
    ):
        """Initialize the gRPC agent protocol."""
        super().__init__(agent, agent_id, name, framework, capabilities, metadata)
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.server = None
        
    def start_server(self):
        """Start the gRPC server."""
        if self.server:
            logger.warning("gRPC server is already running")
            return
            
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
        agent_pb2_grpc.add_AgentServiceServicer_to_server(
            GrpcServicer(self), self.server
        )
        self.server.add_insecure_port(f'{self.host}:{self.port}')
        self.server.start()
        logger.info(f"gRPC server started on {self.host}:{self.port}")
        return self.server
        
    def stop_server(self):
        """Stop the gRPC server."""
        if not self.server:
            logger.warning("gRPC server is not running")
            return
            
        self.server.stop(0)
        logger.info("gRPC server stopped")
        self.server = None


class GrpcServicer(agent_pb2_grpc.AgentServiceServicer):
    """Simplified gRPC servicer implementation."""
    
    def __init__(self, protocol: GrpcAgentProtocol):
        self.protocol = protocol
        
    def GetStatus(self, request, context):
        """Get the current status of the agent."""
        try:
            status = self.protocol.get_status()
            return self._convert_status_to_proto(status)
        except Exception as e:
            logger.error(f"Error in GetStatus: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.StatusResponse()
    
    def ProcessAction(self, request, context):
        """Process an action request."""
        try:
            action_request = self._convert_proto_to_action_request(request)
            response = self.protocol.process_action(action_request)
            return self._convert_action_response_to_proto(response)
        except Exception as e:
            logger.error(f"Error in ProcessAction: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.ActionResponse()
    
    def ProcessRequest(self, request, context):
        """Process a generic request (text, audio, image, or video)."""
        try:
            request_type = request.request_type.lower()
            
            if request_type == "text":
                # Handle text request
                action_request = ActionRequest(
                    agent_id=UUID(request.agent_id),
                    session_id=UUID(request.session_id),
                    message=request.message,
                    role=MessageRole(request.role),
                    stream=request.stream,
                    metadata={k: v for k, v in request.metadata.items()}
                )
                response = self.protocol.process_action(action_request)
                
            elif request_type == "audio":
                # Handle audio request
                audio = self._create_audio_artifact(request)
                listen_request = ListenRequest(audio=audio)
                response = self.protocol.listen(listen_request)
                
            elif request_type in ["image", "video"]:
                # Handle image or video request
                media = self._create_media_artifact(request)
                view_request = ViewRequest(media_type=request_type, media=media)
                response = self.protocol.view(view_request)
                
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unknown request type: {request_type}")
                return agent_pb2.ActionResponse()
                
            return self._convert_action_response_to_proto(response)
            
        except NotImplementedError:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details(f"{request_type} processing not implemented by this adapter")
            return agent_pb2.ActionResponse()
        except Exception as e:
            logger.error(f"Error in ProcessRequest: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agent_pb2.ActionResponse()
    
    def _create_audio_artifact(self, request):
        """Create an AudioArtifact from a GenericRequest."""
        if request.media.HasField("url"):
            url = request.media.url
            content = None
        else:
            url = None
            content = base64.b64encode(request.media.binary).decode('utf-8')
            
        return AudioArtifact(
            id=UUID(),
            url=url,
            base64_audio=content,
            mime_type=request.media.mime_type
        )
    
    def _create_media_artifact(self, request):
        """Create an ImageArtifact or VideoArtifact from a GenericRequest."""
        if request.media.HasField("url"):
            url = request.media.url
            content = None
        else:
            url = None
            content = base64.b64encode(request.media.binary).decode('utf-8')
            
        if request.request_type == "image":
            return ImageArtifact(
                id=UUID(),
                url=url,
                base64_image=content,
                mime_type=request.media.mime_type,
                width=request.width,
                height=request.height,
                alt_text=request.alt_text
            )
        else:
            return VideoArtifact(
                id=UUID(),
                url=url,
                base64_video=content,
                mime_type=request.media.mime_type,
                width=request.width,
                height=request.height,
                duration=request.duration
            )
    
    def _convert_status_to_proto(self, status: StatusResponse) -> agent_pb2.StatusResponse:
        """Convert a Pydantic StatusResponse to a Protocol Buffer message."""
        pb_response = agent_pb2.StatusResponse(
            agent_id=str(status.agent_id),
            name=status.name,
            framework=status.framework,
            status=status.status.value,
            capabilities=status.capabilities
        )
        
        # Convert complex metadata to simple string map
        if status.metadata:
            for k, v in status.metadata.items():
                pb_response.metadata[k] = str(v)
                
        return pb_response
    
    def _convert_proto_to_action_request(self, pb_request) -> ActionRequest:
        """Convert a Protocol Buffer ActionRequest to a Pydantic model."""
        return ActionRequest(
            agent_id=UUID(pb_request.agent_id),
            session_id=UUID(pb_request.session_id),
            message=pb_request.message,
            role=MessageRole(pb_request.role),
            stream=pb_request.stream,
            metadata={k: v for k, v in pb_request.metadata.items()}
        )
    
    def _convert_action_response_to_proto(self, response: ActionResponse) -> agent_pb2.ActionResponse:
        """Convert a Pydantic ActionResponse to a Protocol Buffer message."""
        pb_response = agent_pb2.ActionResponse(
            agent_id=str(response.agent_id),
            session_id=str(response.session_id),
            message=response.message,
            role=response.role.value
        )
        
        # Convert complex metadata to simple string map
        if response.metadata:
            for k, v in response.metadata.items():
                pb_response.metadata[k] = str(v)
        
        # Convert tool calls
        if response.tool_calls:
            for tc in response.tool_calls:
                pb_tool_call = agent_pb2.ToolCall(
                    name=tc.get("name", "")
                )
                
                if "arguments" in tc:
                    for arg_key, arg_value in tc["arguments"].items():
                        pb_tool_call.arguments[arg_key] = str(arg_value)
                        
                pb_response.tool_calls.append(pb_tool_call)
                
        return pb_response