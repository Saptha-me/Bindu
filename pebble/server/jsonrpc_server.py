import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Type, Union
import uuid

from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pebble.core.protocol import PebbleProtocol, ProtocolMethod


def create_jsonrpc_server(
    protocol: PebbleProtocol,
    protocol_handler: Any,
    supported_methods: List[Union[str, ProtocolMethod]]
) -> FastAPI:
    """
    Create a JSON-RPC server for agent-to-agent communication.
    
    Args:
        protocol: The PebbleProtocol instance
        protocol_handler: Handler object with methods for each protocol method
        supported_methods: List of supported protocol methods
        
    Returns:
        FastAPI application for JSON-RPC
    """
    # Create the JSON-RPC app for agent-to-agent communication
    jsonrpc_app = FastAPI(title="Pebble JSON-RPC API")
    
    # Add CORS middleware
    jsonrpc_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Convert any ProtocolMethod enums to strings
    supported_method_names = [
        method.value if isinstance(method, ProtocolMethod) else method 
        for method in supported_methods
    ]
    
    # JSON-RPC endpoint
    @jsonrpc_app.post("/")
    async def handle_jsonrpc(request: Request):
        try:
            # Parse request
            data = await request.json()
            
            # Validate basic JSON-RPC structure
            if not isinstance(data, dict):
                return JSONResponse(
                    status_code=400,
                    content=protocol.create_error(
                        request_id=None, 
                        code=-32600, 
                        message="Invalid Request"
                    )
                )
            
            # Validate jsonrpc version
            jsonrpc_version = data.get("jsonrpc")
            if jsonrpc_version != protocol.JSONRPC_VERSION:
                return JSONResponse(
                    status_code=400,
                    content=protocol.create_error(
                        request_id=data.get("id"), 
                        code=-32600, 
                        message=f"Invalid Request: jsonrpc must be {protocol.JSONRPC_VERSION}"
                    )
                )
            
            # Validate method
            method = data.get("method")
            if not method or method not in supported_method_names:
                return JSONResponse(
                    status_code=400,
                    content=protocol.create_error(
                        request_id=data.get("id"), 
                        code=-32601, 
                        message=f"Method not found or not supported: {method}"
                    )
                )
            
            # Get parameters and request ID
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Dispatch to appropriate handler method
            # The handler object should have methods named handle_<method_name>
            handler_method_name = f"handle_{method}"
            handler_method = getattr(protocol_handler, handler_method_name, None)
            
            if not handler_method:
                return JSONResponse(
                    status_code=400,
                    content=protocol.create_error(
                        request_id=request_id, 
                        code=-32601, 
                        message=f"Method handler not implemented: {method}"
                    )
                )
            
            # Call the handler method
            result = await handler_method(params)
            
            # Return the result
            return protocol.create_response(request_id=request_id, result=result)
            
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content=protocol.create_error(
                    request_id=None, 
                    code=-32700, 
                    message="Parse error: Invalid JSON"
                )
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content=protocol.create_error(
                    request_id=data.get("id") if "data" in locals() else None, 
                    code=-32603, 
                    message=f"Internal error: {str(e)}"
                )
            )
    
    return jsonrpc_app