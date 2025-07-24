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
Core Pebbling Server.

Unified server supporting both JSON-RPC (a2a-style) and HTTP (acp-style) protocols
with shared task management, session contexts, and agent registry.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from pebbling.protocol.types import (
    PebblingRequest, JSONRPCResponse, JSONRPCErrorResponse,
    Task, TaskState, TaskStatus, Message, AgentManifest,
    SendMessageRequest, GetTaskRequest, CancelTaskRequest,
    InvalidRequestError, TaskNotFoundError, MethodNotFoundError
)
from pebbling.server.store import StoreManager
from pebbling.server.handlers.jsonrpc_handler import JSONRPCHandler
from pebbling.server.handlers.http_handler import HTTPHandler
from pebbling.server.handlers.streaming_handler import StreamingHandler

logger = logging.getLogger(__name__)


class PebblingServer:
    """
    Unified Pebbling server supporting both JSON-RPC and HTTP protocols.
    
    Features:
    - JSON-RPC endpoint for a2a-style complex routing
    - HTTP REST endpoints for acp-style direct execution
    - Shared task management and session contexts
    - Server-Sent Events streaming for both protocols
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="Pebbling Server",
            description="Unified agent-to-agent communication server",
            version="1.0.0"
        )
        
        # Initialize stores
        self.store_manager = StoreManager()
        
        # Initialize handlers
        self.jsonrpc_handler = JSONRPCHandler(self.store_manager)
        self.http_handler = HTTPHandler(self.store_manager)
        self.streaming_handler = StreamingHandler(self.store_manager)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all server routes."""
        
        # JSON-RPC endpoint (a2a-style)
        @self.app.post("/rpc")
        async def handle_jsonrpc(request: Request) -> JSONResponse:
            """Handle JSON-RPC requests with a2a-style routing."""
            try:
                body = await request.body()
                raw_request = json.loads(body)
                
                # Validate and parse the request
                pebbling_request = PebblingRequest.model_validate(raw_request)
                
                # Route to JSON-RPC handler
                response = await self.jsonrpc_handler.handle_request(pebbling_request, request)
                
                return JSONResponse(content=response.model_dump())
                
            except json.JSONDecodeError:
                error_response = JSONRPCErrorResponse(
                    error=InvalidRequestError(message="Invalid JSON"),
                    id=raw_request.get("id") if 'raw_request' in locals() else None
                )
                return JSONResponse(content=error_response.model_dump())
            
            except Exception as e:
                logger.error(f"JSON-RPC error: {e}")
                error_response = JSONRPCErrorResponse(
                    error=InvalidRequestError(message=str(e)),
                    id=raw_request.get("id") if 'raw_request' in locals() else None
                )
                return JSONResponse(content=error_response.model_dump())
        
        # HTTP REST endpoints (acp-style)
        @self.app.get("/agents")
        async def list_agents():
            """List all registered agents."""
            return await self.http_handler.list_agents()
        
        @self.app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str):
            """Get agent by ID."""
            return await self.http_handler.get_agent(agent_id)
        
        @self.app.post("/agents")
        async def register_agent(manifest: AgentManifest):
            """Register a new agent."""
            return await self.http_handler.register_agent(manifest)
        
        @self.app.post("/runs")
        async def create_run(request: Dict[str, Any]):
            """Create and execute a task (acp-style)."""
            return await self.http_handler.create_run(request)
        
        @self.app.get("/runs/{run_id}")
        async def get_run(run_id: str):
            """Get run/task by ID."""
            return await self.http_handler.get_run(run_id)
        
        @self.app.post("/runs/{run_id}/cancel")
        async def cancel_run(run_id: str):
            """Cancel a run/task."""
            return await self.http_handler.cancel_run(run_id)
        
        # Streaming endpoints (shared by both protocols)
        @self.app.get("/stream/{task_id}")
        async def stream_task(task_id: str):
            """Stream task updates via Server-Sent Events."""
            return await self.streaming_handler.stream_task(task_id)
        
        @self.app.get("/sessions/{session_id}/stream")
        async def stream_session(session_id: str):
            """Stream all task updates for a session."""
            return await self.streaming_handler.stream_session(session_id)
        
        # Health and utility endpoints
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            stats = await self.store_manager.get_stats()
            return {
                "status": "healthy",
                "stores": stats,
                "protocols": ["json-rpc", "http"],
                "features": ["streaming", "sessions", "interoperability"]
            }
        
        @self.app.get("/stats")
        async def get_stats():
            """Get server statistics."""
            return await self.store_manager.get_stats()
    
    async def register_agent(self, manifest: AgentManifest) -> None:
        """Register an agent with the server."""
        await self.store_manager.register_agent(manifest)
        logger.info(f"Registered agent: {manifest.name} ({manifest.id})")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app


# Global server instance
_server_instance: Optional[PebblingServer] = None


def get_server() -> PebblingServer:
    """Get or create the global server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = PebblingServer()
    return _server_instance


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    server = get_server()
    return server.get_app()
