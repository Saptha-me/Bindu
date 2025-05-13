"""JSON-RPC server implementation for pebbling."""

import json
from typing import Any, List, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebbling.core.protocol import ProtocolMethod, pebblingProtocol
from pebbling.server.schemas.model import (
    JsonRpcError,
    JsonRpcErrorDetail,
    JsonRpcResponse,
)


def create_jsonrpc_server(
    protocol: pebblingProtocol,
    protocol_handler: Any,
    supported_methods: List[Union[str, ProtocolMethod]],
) -> FastAPI:
    """Create a JSON-RPC server for agent-to-agent communication."""
    jsonrpc_app = FastAPI(title="pebbling JSON-RPC API")

    jsonrpc_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    supported_method_names = [
        method.value if isinstance(method, ProtocolMethod) else method for method in supported_methods
    ]

    @jsonrpc_app.post("/")
    async def handle_jsonrpc(request: Request):
        """Handle JSON-RPC requests."""
        try:
            request_id = None
            data = await request.json()

            # Validate request is a dictionary
            if not isinstance(data, dict):
                return JsonRpcError(error=JsonRpcErrorDetail(code=-32600, message="Invalid Request"))

            request_id = data.get("id")

            # Validate JSON-RPC version
            if data.get("jsonrpc") != protocol.JSONRPC_VERSION:
                return JsonRpcError(
                    id=str(request_id) if request_id is not None else "null",
                    error=JsonRpcErrorDetail(
                        code=-32600,
                        message=f"Invalid Request: jsonrpc must be {protocol.JSONRPC_VERSION}",
                    ),
                )

            # Validate method
            method = data.get("method")
            if not method or method not in supported_method_names:
                return JsonRpcError(
                    id=str(request_id) if request_id is not None else "null",
                    error=JsonRpcErrorDetail(
                        code=-32601,
                        message=f"Method not found or not supported: {method}",
                    ),
                )

            # Get parameters
            params = data.get("params", {})

            # Dispatch to handler method
            handler_method_name = f"handle_{method}"
            handler_method = getattr(protocol_handler, handler_method_name, None)

            if not handler_method:
                return JsonRpcError(
                    id=str(request_id) if request_id is not None else "null",
                    error=JsonRpcErrorDetail(code=-32601, message=f"Method handler not implemented: {method}"),
                )

            # Call handler and return result
            result = await handler_method(params)

            # Create response
            response = JsonRpcResponse(id=str(request_id) if request_id is not None else "null", result=result)
            return JSONResponse(content=response.model_dump())

        except json.JSONDecodeError:
            return JsonRpcError(
                id=str(request_id) if request_id is not None else "null",
                error=JsonRpcErrorDetail(code=-32700, message="Parse error: Invalid JSON"),
            )

        except Exception as e:
            return JsonRpcError(
                id=str(request_id) if request_id is not None else "null",
                error=JsonRpcErrorDetail(code=-32603, message=f"Internal error: {str(e)}"),
            )

    return jsonrpc_app
