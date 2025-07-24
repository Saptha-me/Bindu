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
Pebbling Server Application Factory.

Creates FastAPI applications with unified JSON-RPC and HTTP support,
following the patterns from a2a and acp projects.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from pebbling.protocol.types import (
    PebblingRequest, JSONRPCResponse, JSONRPCErrorResponse,
    AgentManifest, Task, InvalidRequestError
)
from pebbling.server.store import StoreManager
from pebbling.server.handlers import JSONRPCHandler, HTTPHandler, StreamingHandler

logger = logging.getLogger(__name__)


def create_app(
    *,
    title: str = "Pebbling Server",
    description: str = "Unified agent-to-agent communication server",
    version: str = "1.0.0",
    store_manager: Optional[StoreManager] = None,
    **kwargs: Any
) -> FastAPI:
    """
    Create a FastAPI application with Pebbling protocol support.
    
    Args:
        title: Application title
        description: Application description  
        version: Application version
        store_manager: Optional store manager instance
        **kwargs: Additional FastAPI constructor arguments
        
    Returns:
        Configured FastAPI application
    """
    
    # Initialize store manager
    if store_manager is None:
        store_manager = StoreManager()
    
    # Initialize handlers
    jsonrpc_handler = JSONRPCHandler(store_manager)
    http_handler = HTTPHandler(store_manager)
    streaming_handler = StreamingHandler(store_manager)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Application lifespan manager."""
        logger.info("Starting Pebbling Server...")
        
        # Add Pebbling request schema to OpenAPI
        pebbling_request_schema = PebblingRequest.model_json_schema(
            ref_template='#/components/schemas/{model}'
        )
        defs = pebbling_request_schema.pop('$defs', {})
        openapi_schema = app.openapi()
        component_schemas = openapi_schema.setdefault(
            'components', {}
        ).setdefault('schemas', {})
        component_schemas.update(defs)
        component_schemas['PebblingRequest'] = pebbling_request_schema
        
        logger.info("Server startup complete!")
        logger.info("Available endpoints:")
        logger.info("  JSON-RPC: POST /rpc")
        logger.info("  HTTP REST: GET /agents, POST /runs")
        logger.info("  Streaming: GET /stream/{task_id}")
        logger.info("  Health: GET /health")
        
        yield
        
        logger.info("Shutting down Pebbling Server...")
    
    # Create FastAPI app
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        **kwargs
    )
    
    # Add routes
    _add_jsonrpc_routes(app, jsonrpc_handler)
    _add_http_routes(app, http_handler)
    _add_streaming_routes(app, streaming_handler)
    _add_utility_routes(app, store_manager)
    
    # Store references for access
    app.state.store_manager = store_manager
    app.state.jsonrpc_handler = jsonrpc_handler
    app.state.http_handler = http_handler
    app.state.streaming_handler = streaming_handler
    
    return app


def _add_jsonrpc_routes(app: FastAPI, handler: JSONRPCHandler) -> None:
    """Add JSON-RPC routes (a2a-style)."""
    
    @app.post(
        "/rpc",
        response_model=JSONRPCResponse,
        openapi_extra={
            'requestBody': {
                'content': {
                    'application/json': {
                        'schema': {
                            '$ref': '#/components/schemas/PebblingRequest'
                        }
                    }
                },
                'required': True,
                'description': 'Pebbling JSON-RPC Request',
            }
        },
        summary="JSON-RPC Endpoint",
        description="Handle JSON-RPC requests with a2a-style complex routing"
    )
    async def handle_jsonrpc(request: Request) -> JSONResponse:
        """Handle JSON-RPC requests."""
        try:
            body = await request.body()
            raw_request = json.loads(body)
            
            # Validate and parse the request
            pebbling_request = PebblingRequest.model_validate(raw_request)
            
            # Route to JSON-RPC handler
            response = await handler.handle_request(pebbling_request, request)
            
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


def _add_http_routes(app: FastAPI, handler: HTTPHandler) -> None:
    """Add HTTP REST routes (acp-style)."""
    
    @app.get(
        "/agents",
        summary="List Agents",
        description="List all registered agents"
    )
    async def list_agents():
        """List all registered agents."""
        return await handler.list_agents()
    
    @app.get(
        "/agents/{agent_id}",
        summary="Get Agent",
        description="Get agent by ID"
    )
    async def get_agent(agent_id: str):
        """Get agent by ID."""
        return await handler.get_agent(agent_id)
    
    @app.post(
        "/agents",
        summary="Register Agent",
        description="Register a new agent"
    )
    async def register_agent(manifest: AgentManifest):
        """Register a new agent."""
        return await handler.register_agent(manifest)
    
    @app.post(
        "/runs",
        summary="Create Run",
        description="Create and execute a task (acp-style)"
    )
    async def create_run(request: Dict[str, Any]):
        """Create and execute a task."""
        return await handler.create_run(request)
    
    @app.get(
        "/runs/{run_id}",
        summary="Get Run",
        description="Get run/task by ID"
    )
    async def get_run(run_id: str):
        """Get run/task by ID."""
        return await handler.get_run(run_id)
    
    @app.post(
        "/runs/{run_id}/cancel",
        summary="Cancel Run",
        description="Cancel a run/task"
    )
    async def cancel_run(run_id: str):
        """Cancel a run/task."""
        return await handler.cancel_run(run_id)
    
    @app.get(
        "/sessions/{session_id}/runs",
        summary="Get Session Runs",
        description="Get all runs for a session"
    )
    async def get_session_runs(session_id: str):
        """Get all runs for a session."""
        return await handler.get_session_runs(session_id)
    
    @app.delete(
        "/sessions/{session_id}",
        summary="Cleanup Session",
        description="Clean up a session and its associated data"
    )
    async def cleanup_session(session_id: str):
        """Clean up a session."""
        return await handler.cleanup_session(session_id)


def _add_streaming_routes(app: FastAPI, handler: StreamingHandler) -> None:
    """Add streaming routes (SSE)."""
    
    @app.get(
        "/stream/{task_id}",
        summary="Stream Task",
        description="Stream task updates via Server-Sent Events"
    )
    async def stream_task(task_id: str) -> EventSourceResponse:
        """Stream task updates."""
        return await handler.stream_task(task_id)
    
    @app.get(
        "/sessions/{session_id}/stream",
        summary="Stream Session",
        description="Stream all task updates for a session"
    )
    async def stream_session(session_id: str) -> EventSourceResponse:
        """Stream session updates."""
        return await handler.stream_session(session_id)
    
    @app.get(
        "/agents/{agent_id}/sessions/{session_id}/stream",
        summary="Stream Agent Context",
        description="Stream updates for a specific agent context"
    )
    async def stream_agent_context(agent_id: str, session_id: str) -> EventSourceResponse:
        """Stream agent context updates."""
        return await handler.stream_agent_context(session_id, agent_id)


def _add_utility_routes(app: FastAPI, store_manager: StoreManager) -> None:
    """Add utility and health routes."""
    
    @app.get(
        "/health",
        summary="Health Check",
        description="Health check endpoint with server statistics"
    )
    async def health_check():
        """Health check endpoint."""
        stats = await store_manager.get_stats()
        return {
            "status": "healthy",
            "stores": stats,
            "protocols": ["json-rpc", "http"],
            "features": ["streaming", "sessions", "interoperability"]
        }
    
    @app.get(
        "/stats",
        summary="Server Statistics",
        description="Get detailed server statistics"
    )
    async def get_stats():
        """Get server statistics."""
        return await store_manager.get_stats()
    
    @app.get(
        "/",
        summary="Server Info",
        description="Basic server information"
    )
    async def server_info():
        """Basic server information."""
        return {
            "name": "Pebbling Server",
            "description": "Unified agent-to-agent communication server",
            "protocols": {
                "jsonrpc": {
                    "endpoint": "/rpc",
                    "description": "JSON-RPC 2.0 with a2a-style routing"
                },
                "http": {
                    "endpoints": ["/agents", "/runs"],
                    "description": "REST API with acp-style direct execution"
                },
                "streaming": {
                    "endpoints": ["/stream/{task_id}", "/sessions/{session_id}/stream"],
                    "description": "Server-Sent Events for real-time updates"
                }
            },
            "documentation": "/docs"
        }
