import json
from typing import Any, List, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebble.core.protocol import PebbleProtocol, ProtocolMethod
from pebble.server.schemas.model import (
    JsonRpcResponse, 
    JsonRpcError, 
    JsonRpcErrorDetail
)


def create_jsonrpc_server(
    protocol: PebbleProtocol,
    protocol_handler: Any,
    supported_methods: List[Union[str, ProtocolMethod]]
) -> FastAPI:
    """Create a JSON-RPC server for agent-to-agent communication."""
    jsonrpc_app = FastAPI(title="Pebble JSON-RPC API")
    
    jsonrpc_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    supported_method_names = [
        method.value if isinstance(method, ProtocolMethod) else method 
        for method in supported_methods
    ]
    
    @jsonrpc_app.post("/")
    async def handle_jsonrpc(request: Request):
        """Handle JSON-RPC requests"""
        try:
            data = await request.json()
            
            # Validate request is a dictionary
            if not isinstance(data, dict):
                return JsonRpcError(
                    error=JsonRpcErrorDetail(
                        code=-32600, 
                        message="Invalid Request"
                    )
                )
            
            request_id = data.get("id")
            
            # Validate JSON-RPC version
            if data.get("jsonrpc") != protocol.JSONRPC_VERSION:
                return JsonRpcError(
                    id=request_id,
                    error=JsonRpcErrorDetail(
                        code=-32600,
                        message=f"Invalid Request: jsonrpc must be {protocol.JSONRPC_VERSION}"
                    )
                )
            
            # Validate method
            method = data.get("method")
            if not method or method not in supported_method_names:
                return JsonRpcError(
                    id=request_id,
                    error=JsonRpcErrorDetail(
                        code=-32601,
                        message=f"Method not found or not supported: {method}"
                    )
                )
            
            # Get parameters
            params = data.get("params", {})
            
            # Dispatch to handler method
            handler_method_name = f"handle_{method}"
            handler_method = getattr(protocol_handler, handler_method_name, None)
            
            if not handler_method:
                return JsonRpcError(
                    id=request_id,
                    error=JsonRpcErrorDetail(
                        code=-32601,
                        message=f"Method handler not implemented: {method}"
                    )
                )
            
            # Call handler and return result
            result = await handler_method(params)
            
            # Create response
            response = JsonRpcResponse(
                id=request_id,
                result=result
            )
            return JSONResponse(content=response.model_dump())
            
        except json.JSONDecodeError:
            return JsonRpcError(
                id=request_id,
                error=JsonRpcErrorDetail(
                    code=-32700,
                    message="Parse error: Invalid JSON"
                )
            )
            
        except Exception as e:
            return JsonRpcError(
                id=request_id,
                error=JsonRpcErrorDetail(
                    code=-32603,
                    message=f"Internal error: {str(e)}"
                )
            )
    
    return jsonrpc_app