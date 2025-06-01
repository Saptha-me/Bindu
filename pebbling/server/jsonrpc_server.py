"""JSON-RPC server for pebbling protocol."""

import json
import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from pebbling.core.protocol import pebblingProtocol
from pebbling.server.server_security import SecurityMiddleware
from pebbling.security.mtls_middleware import MTLSMiddleware

logger = logging.getLogger(__name__)


class JSONRPCServer:
    """JSON-RPC server for pebbling protocol."""

    def __init__(
        self,
        protocol: pebblingProtocol,
        protocol_handler: Any,
        supported_methods: List[str] = None,
        security_middleware: SecurityMiddleware = None,
        mtls_middleware: MTLSMiddleware = None,
    ):
        """Initialize the JSON-RPC server.

        Args:
            protocol: Protocol definition
            protocol_handler: Protocol handler implementation
            supported_methods: List of supported protocol methods
            security_middleware: Optional security middleware
            mtls_middleware: Optional mTLS middleware
        """
        self.protocol = protocol
        self.protocol_handler = protocol_handler
        self.supported_methods = supported_methods or []
        self.security_middleware = security_middleware
        self.mtls_middleware = mtls_middleware
        
        # Security method handlers
        self.security_handlers = {}
        
        # If security middleware is provided, register security method handlers
        if self.security_middleware:
            self.security_handlers.update({
                "exchange_did": self.security_middleware.handle_exchange_did,
                "verify_identity": self.security_middleware.handle_verify_identity,
            })
            
        # If mTLS middleware is provided, register mTLS method handlers
        if self.mtls_middleware:
            self.security_handlers.update({
                "exchange_certificates": self.mtls_middleware.handle_exchange_certificates,
                "verify_connection": self.mtls_middleware.handle_verify_connection,
            })

    async def handle_jsonrpc_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request object
            
        Returns:
            JSON-RPC response object
        """
        try:
            # Extract method and params
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id", None)
            
            # Check if method is supported
            if method not in self.supported_methods:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found or not supported"
                    },
                    "id": request_id
                }
            
            # Handle security-related methods through security middleware
            if method in self.security_handlers:
                handler = self.security_handlers[method]
                result = await handler(params)
            else:
                # For regular methods, call the protocol handler
                handler_method = getattr(self.protocol_handler, f"handle_{method}", None)
                if not handler_method:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"No handler found for method '{method}'"
                        },
                        "id": request_id
                    }
                    
                # Call the handler method
                try:
                    handler_result = await handler_method(**params)
                    return create_success_response(
                        result={
                            "content": handler_result.content,
                            "metadata": handler_result.metadata
                        },
                        request_id=request_id
                    )

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

    async def require_full_security(self, method: str, params: Dict[str, Any]) -> bool:
        """Check if a method requires full security (DID + mTLS).
    
        Returns True if security is satisfied, False otherwise.
        """
        if method == "act":  # Add other secure methods as needed
            source_agent_id = params.get("source_agent_id")
            if not self.security_middleware or not self.security_middleware.is_agent_verified(source_agent_id):
                return False    
            if not self.mtls_middleware or not self.mtls_middleware.is_connection_verified(source_agent_id):
                return False
        return True

    async def handle_request(self, request: Request) -> Response:
        """Handle an HTTP request to the JSON-RPC server.

        Args:
            request: FastAPI request object
            
        Returns:
            FastAPI response object
        """
        try:
            # Parse request body
            body = await request.json()
            
            # Check if the request is a batch request
            is_batch = isinstance(body, list)
            
            if is_batch:
                requests = body
            else:
                requests = [body]
                
            responses = []
            
            # Process each request
            for req in requests:
                # Verify the request signature if security is enabled
                if self.security_middleware and self.mtls_middleware and req.get("method") not in ["exchange_did", "verify_identity", "exchange_certificates", "verify_connection"]:
                    is_secured = await self.require_full_security(req.get("method"), req.get("params"))
                    if not is_secured:
                        responses.append({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32600,
                                "message": "Request signature verification failed"
                            },
                            "id": req.get("id", None)
                        })
                        continue
                
                # Handle the request
                response = await self.handle_jsonrpc_request(req)
                responses.append(response)
                
            # Return single response or batch
            if is_batch:
                return Response(content=json.dumps(responses), media_type="application/json")
            else:
                return Response(content=json.dumps(responses[0]), media_type="application/json")
                
        except json.JSONDecodeError:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    },
                    "id": None
                }),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error handling HTTP request: {str(e)}")
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": None
                }),
                media_type="application/json"
            )


def create_jsonrpc_server(
    protocol: pebblingProtocol,
    protocol_handler: Any,
    supported_methods: List[str] = None,
    security_middleware: SecurityMiddleware = None,
    mtls_middleware: MTLSMiddleware = None,
) -> FastAPI:
    """Create a FastAPI app for the JSON-RPC server.
    
    Args:
        protocol: Protocol definition
        protocol_handler: Protocol handler implementation
        supported_methods: List of supported methods
        security_middleware: Optional security middleware for DID-based security
        mtls_middleware: Optional mTLS middleware for secure connections
        
    Returns:
        FastAPI app
    """
    # Create server
    server = JSONRPCServer(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=supported_methods,
        security_middleware=security_middleware,
        mtls_middleware=mtls_middleware,
    )
    
    # Create FastAPI app
    app = FastAPI(title="Pebbling JSON-RPC Server")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add route
    @app.post("/jsonrpc")
    async def handle_jsonrpc(request: Request) -> Response:
        return await server.handle_request(request)
        
    return app