import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Type, Union
import uuid

from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from agno.agent import Agent, RunResponse

from pebble.core.protocol import PebbleProtocol, ProtocolMethod


def create_rest_server(protocol_handler: Optional[Any] = None) -> FastAPI:
    """
    Create a REST API server for user interaction.
    
    Args:
        protocol_handler: Optional protocol handler instance shared with JSON-RPC server
        
    Returns:
        FastAPI application for REST API
    """
    # Create the REST API app for user interaction
    rest_app = FastAPI(title="Pebble User API")
    
    # Add CORS middleware
    rest_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health endpoint
    @rest_app.get("/health")
    async def health_check():
        """Check the health of the agent server"""
        try:
            # Check basic server health
            agent_status = protocol_handler.agent.get_status() if hasattr(protocol_handler.agent, "get_status") else "healthy"
            return {
                "status": agent_status,
                "message": "Service is running",
                "timestamp": str(uuid.uuid4())
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    # Run endpoint
    @rest_app.post("/run")
    async def run_agent(request_data: Dict[str, Any] = Body(...)):
        """Run the agent with the provided input"""
        try:
            input_text = request_data.get("input", "")
            if not input_text:
                raise HTTPException(status_code=400, detail="Input text is required")
            
            # Execute the agent
            result = protocol_handler.agent.run(input_text).to_dict()

            return {
                "status": "success",
                "content": result["content"],
                "messages": result["messages"],
                "metrics": result["metrics"],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
    return rest_app
