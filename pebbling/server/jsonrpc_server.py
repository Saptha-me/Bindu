"""JSON-RPC server implementation for pebbling."""

import json
from typing import Any, List, Optional, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebbling.core.protocol import CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod, pebblingProtocol
from pebbling.server.server_security import SecurityMiddleware
from pebbling.server.schemas.model import (
    JsonRpcError,
    JsonRpcErrorDetail,
    JsonRpcResponse,
)


def create_jsonrpc_server(
    protocol: pebblingProtocol,
    protocol_handler: Any,
    supported_methods: List[Union[str, CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod]],
    security_middleware: Optional[SecurityMiddleware] = None,
) -> FastAPI:
    """Create a JSON-RPC server for agent-to-agent communication.
    
    Args:
        protocol: Protocol implementation
        protocol_handler: Handler for protocol methods
        supported_methods: List of supported protocol methods
        security_middleware: Optional security middleware for DID-based verification
        
    Returns:
        FastAPI application
    """
    jsonrpc_app = FastAPI(title="pebbling JSON-RPC API")

    jsonrpc_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Convert enum values to strings for comparison
    supported_method_names = []
    for method in supported_methods:
        if isinstance(method, (CoreProtocolMethod, SecurityProtocolMethod, DiscoveryProtocolMethod)):
            supported_method_names.append(method.value)
        else:
            supported_method_names.append(method)

    @jsonrpc_app.post("/")
    async def handle_jsonrpc(request: Request):
        """Handle JSON-RPC requests."""
        request_id = "null"  # Default ID if none provided
        
        try:
            # Parse request
            data = await request.json()
            
            # Validate request is a dictionary
            if not isinstance(data, dict):
                return create_error_response(-32600, "Invalid Request", request_id)
                
            # Get request ID
            request_id = data.get("id", "null")
            if request_id is None:
                request_id = "null"
            else:
                request_id = str(request_id)
                
            # Validate JSON-RPC version
            if data.get("jsonrpc") != protocol.JSONRPC_VERSION:
                return create_error_response(
                    -32600, 
                    f"Invalid Request: jsonrpc must be {protocol.JSONRPC_VERSION}", 
                    request_id
                )
                
            # Validate method
            method = data.get("method")
            
            # Special handling for DID exchange which is always allowed with security middleware
            is_security_method = method in [m.value for m in SecurityProtocolMethod.__members__.values()]
            is_allowed_security = is_security_method and security_middleware is not None
            
            if not method or (method not in supported_method_names and not is_allowed_security):
                return create_error_response(
                    -32601, 
                    f"Method not found or not supported: {method}", 
                    request_id
                )
                
            # Get parameters
            params = data.get("params", {})
            
            # Process the request
            if security_middleware is not None and is_security_method:
                # Security methods are handled directly by the security middleware
                result = await security_middleware.secure_request_handler(data, None)
                return create_success_response(result, request_id)
            else:
                # Other methods are handled by the protocol handler
                handler_method_name = f"handle_{method}"
                handler_method = getattr(protocol_handler, handler_method_name, None)
                
                if not handler_method:
                    return create_error_response(
                        -32601, 
                        f"Method handler not implemented: {method}", 
                        request_id
                    )
                    
                try:
                    result = await handler_method(params)
                    return create_success_response(result, request_id)
                except Exception as e:
                    import traceback
                    print(f"Error in handler method {handler_method_name}: {e}")
                    print(traceback.format_exc())
                    return create_error_response(-32603, f"Internal error in handler: {str(e)}", request_id)
                    
        except json.JSONDecodeError:
            return create_error_response(-32700, "Parse error: Invalid JSON", request_id)
        except Exception as e:
            import traceback
            print(f"Unhandled error in JSON-RPC server: {e}")
            print(traceback.format_exc())
            return create_error_response(-32603, f"Internal error: {str(e)}", request_id)
            
    def create_error_response(code: int, message: str, request_id: str):
        """Create a standardized error response."""
        error = JsonRpcError(
            id=request_id,
            error=JsonRpcErrorDetail(code=code, message=message)
        )
        return JSONResponse(content=error.model_dump())
        
    def create_success_response(result: Any, request_id: str):
        """Create a standardized success response."""
        response = JsonRpcResponse(id=request_id, result=result)
        return JSONResponse(content=response.model_dump())

    return jsonrpc_app
