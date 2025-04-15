"""
Example script to test both gRPC and JSON-RPC agent protocols.

This script:
1. Creates a simple protocol agent that directly implements the protocol methods
2. Starts both gRPC and JSON-RPC servers with the same implementation
3. Handles all required media processing and method implementations
"""

import argparse
import logging
import threading
import time
import uuid
from typing import Dict, Any, List, Optional

# Import the protocol classes
from pebble.core.protocol import AgentProtocol
from pebble.core.grpc_protocol import GrpcAgentProtocol
from pebble.core.jsonrpc_protocol import JsonRpcAgentProtocol

# Import the model classes
from pebble.schemas.models import (
    ActionRequest, 
    ActionResponse, 
    AgentStatus,
    ListenRequest,
    ViewRequest,
    StatusResponse,
    MessageRole
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProtocolTestAgent(AgentProtocol):
    """Direct implementation of the AgentProtocol for testing."""
    
    def __init__(self, name="TestAgent"):
        """Initialize the agent protocol implementation."""
        # Create agent_id
        agent_id = uuid.uuid4()
        
        # Initialize the base protocol with ourselves as the agent
        super().__init__(
            agent=None,  # We directly implement the protocol, no wrapped agent
            agent_id=agent_id,
            name=name,
            framework="test",
            capabilities=["text", "image", "video", "audio"],
            metadata={"version": "1.0.0"}
        )
        
        # Ensure the status is ready
        self.status = AgentStatus.READY
    
    def get_status(self) -> StatusResponse:
        """Get the current status of the agent."""
        return StatusResponse(
            agent_id=self.agent_id,
            name=self.name,
            framework=self.framework,
            status=self.status,
            capabilities=self.capabilities,
            metadata=self.metadata
        )
    
    def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process a standard text action."""
        # Echo the input with a timestamp
        response = f"[{time.strftime('%H:%M:%S')}] Received: {request.message}"
        
        # Return formatted response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=response,
            role=MessageRole.AGENT,
            metadata={"request_id": str(uuid.uuid4())}
        )
    
    def listen(self, request: ListenRequest) -> ActionResponse:
        """Process an audio input."""
        # Check if we have audio data
        if not hasattr(request, 'audio') or not request.audio:
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=uuid.uuid4(),
                message="Error: No audio data provided",
                role=MessageRole.AGENT
            )
        
        # Build response based on audio source
        if hasattr(request.audio, 'url') and request.audio.url:
            message = f"Processed audio from URL: {request.audio.url}"
        elif hasattr(request.audio, 'base64_audio') and request.audio.base64_audio:
            message = "Processed audio from base64 data"
        else:
            message = "Received audio but no content found"
        
        # Return formatted response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=uuid.uuid4(),
            message=message,
            role=MessageRole.AGENT,
            metadata={"audio_id": str(request.audio.id) if hasattr(request.audio, 'id') else None}
        )
    
    def view(self, request: ViewRequest) -> ActionResponse:
        """Process an image or video input."""
        # Check if we have media data and media type
        if not hasattr(request, 'media') or not request.media:
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=uuid.uuid4(),
                message="Error: No media data provided",
                role=MessageRole.AGENT
            )
        
        if not hasattr(request, 'media_type'):
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=uuid.uuid4(),
                message="Error: No media type specified",
                role=MessageRole.AGENT
            )
        
        # Get the media type
        media_type = request.media_type.lower()
        
        # Build response based on media source
        if hasattr(request.media, 'url') and request.media.url:
            message = f"Processed {media_type} from URL: {request.media.url}"
        elif (hasattr(request.media, 'base64_image') and request.media.base64_image) or \
             (hasattr(request.media, 'base64_video') and request.media.base64_video):
            message = f"Processed {media_type} from base64 data"
        else:
            message = f"Received {media_type} but no content found"
        
        # Add media dimensions if available
        if hasattr(request.media, 'width') and request.media.width and \
           hasattr(request.media, 'height') and request.media.height:
            message += f" (Dimensions: {request.media.width}x{request.media.height})"
        
        # Add duration for videos
        if media_type == "video" and hasattr(request.media, 'duration') and request.media.duration:
            message += f" (Duration: {request.media.duration}s)"
        
        # Return formatted response
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=uuid.uuid4(),
            message=message,
            role=MessageRole.AGENT,
            metadata={"media_id": str(request.media.id) if hasattr(request.media, 'id') else None}
        )


def start_grpc_server(agent, port, host="0.0.0.0"):
    """Start the gRPC server."""
    try:
        grpc_protocol = GrpcAgentProtocol(
            agent=agent,
            name=agent.name,
            port=port,
            host=host
        )
        logger.info(f"Starting gRPC server on {host}:{port}")
        grpc_protocol.start_server()
    except Exception as e:
        logger.error(f"Error starting gRPC server: {e}")


def start_jsonrpc_server(agent, port, host="0.0.0.0"):
    """Start the JSON-RPC server."""
    try:
        jsonrpc_protocol = JsonRpcAgentProtocol(
            agent=agent,
            name=agent.name,
            port=port,
            host=host
        )
        logger.info(f"Starting JSON-RPC server on {host}:{port}")
        jsonrpc_protocol.start_server()
    except Exception as e:
        logger.error(f"Error starting JSON-RPC server: {e}")


def main():
    """Main entry point for the protocol test server."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test agent protocol servers")
    parser.add_argument("--grpc-port", type=int, default=50051, help="Port for gRPC server")
    parser.add_argument("--jsonrpc-port", type=int, default=8020, help="Port for JSON-RPC server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind servers to")
    parser.add_argument("--mode", choices=["grpc", "jsonrpc", "both"], default="both", 
                      help="Which server(s) to start")
    args = parser.parse_args()
    
    # Create the protocol agent
    agent = ProtocolTestAgent(name="TestAgent")
    logger.info(f"Created test agent with ID {agent.agent_id}")
    
    # Start servers based on mode
    if args.mode in ["grpc", "both"]:
        grpc_thread = threading.Thread(
            target=start_grpc_server,
            args=(agent, args.grpc_port, args.host),
            daemon=True
        )
        grpc_thread.start()
    
    if args.mode in ["jsonrpc", "both"]:
        jsonrpc_thread = threading.Thread(
            target=start_jsonrpc_server,
            args=(agent, args.jsonrpc_port, args.host),
            daemon=True
        )
        jsonrpc_thread.start()
    
    # Keep the main thread alive until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")


if __name__ == "__main__":
    main()