"""JSON-RPC server for pebbling protocol."""

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pebbling.core.protocol import pebblingProtocol
from pebbling.server.server_security import SecurityMiddleware
from pebbling.security.mtls.certificate_manager import CertificateManager
from pebbling.utils.jsonrpc_utils import create_success_response, create_error_response
from pebbling.utils.logging_config import configure_logger, get_module_logger
from pebbling.utils.security_utils import (
    verify_security_requirements,
    needs_security_check,
    create_security_failure_response,
    register_security_handlers
)
from pebbling.utils.rpc_handlers import (
    validate_method,
    handle_security_method,
    handle_protocol_method,
    process_jsonrpc_request,
    process_batch_request
)


class JSONRPCServer:
    """JSON-RPC server for pebbling protocol."""

    def __init__(
        self,
        protocol: pebblingProtocol,
        protocol_handler: Any,
        supported_methods: Optional[List[str]] = None,
        security_middleware: Optional[SecurityMiddleware] = None,
        certificate_manager: Optional[CertificateManager] = None,
    ):
        """Initialize the JSON-RPC server.

        Args:
            protocol: Protocol definition
            protocol_handler: Protocol handler implementation
            supported_methods: List of supported protocol methods
            security_middleware: Optional security middleware
            certificate_manager: Optional certificate manager for mTLS
        """
        self.logger = get_module_logger("jsonrpc_server")
        self.logger.debug("Initializing JSONRPCServer")
        
        self.protocol = protocol
        self.protocol_handler = protocol_handler
        self.supported_methods = supported_methods or []
        self.security_middleware = security_middleware
        self.certificate_manager = certificate_manager
        self.security_handlers = register_security_handlers(security_middleware, certificate_manager)
        
        self.logger.debug(f"Registered {len(self.security_handlers)} security handlers")

    async def handle_jsonrpc_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request object
            
        Returns:
            JSON-RPC response object
        """
        return await process_jsonrpc_request(
            request=request,
            supported_methods=self.supported_methods,
            security_handlers=self.security_handlers,
            protocol_handler=self.protocol_handler,
            security_middleware=self.security_middleware
        )

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
            self.logger.info(f"Received JSON-RPC request from {request.client.host if request.client else 'unknown'}")
            
            # Check if the request is a batch request
            is_batch = isinstance(body, list)
            requests = body if is_batch else [body]
            
            # Process requests
            responses = []
            
            for req in requests:
                # Verify the request signature if security is enabled
                if needs_security_check(req, self.security_middleware, self.mtls_middleware):
                    is_secured = await verify_security_requirements(
                        req.get("method"), 
                        req.get("params", {}),
                        self.security_middleware,
                        self.mtls_middleware
                    )
                    if not is_secured:
                        responses.append(create_security_failure_response(req.get("id", None)))
                        continue
                
                # Handle the request
                response = await self.handle_jsonrpc_request(req)
                responses.append(response)
            
            # Return single response or batch
            content = json.dumps(responses if is_batch else responses[0])
            return Response(content=content, media_type="application/json")
                
        except json.JSONDecodeError:
            self.logger.error("JSON decode error in request")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }
            return Response(content=json.dumps(error_response), media_type="application/json")
        except Exception as e:
            import traceback
            self.logger.error(f"Error handling HTTP request: {str(e)}\n{traceback.format_exc()}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            }
            return Response(content=json.dumps(error_response), media_type="application/json")


def create_jsonrpc_server(
    protocol: pebblingProtocol,
    protocol_handler: Any,
    supported_methods: Optional[List[str]] = None,
    security_middleware: Optional[SecurityMiddleware] = None,
    certificate_manager: Optional[CertificateManager] = None,
) -> FastAPI:
    """Create a FastAPI app for the JSON-RPC server.
    
    Args:
        protocol: Protocol definition
        protocol_handler: Protocol handler implementation
        supported_methods: List of supported methods
        security_middleware: Optional security middleware for DID-based security
        certificate_manager: Optional certificate manager for mTLS secure connections
        
    Returns:
        FastAPI app
    """
    # Configure loguru
    configure_logger(
        log_file="logs/jsonrpc_server.log",
        console_level="DEBUG",
        file_level="INFO",
        rotation="10 MB",
        retention="1 week"
    )
    
    logger.info("Initializing JSON-RPC server")
    
    # Create server
    server = JSONRPCServer(
        protocol=protocol,
        protocol_handler=protocol_handler,
        supported_methods=supported_methods,
        security_middleware=security_middleware,
        certificate_manager=certificate_manager,
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
    @app.post("/pebble")
    async def handle_jsonrpc(request: Request) -> Response:
        return await server.handle_request(request)
    
    logger.info("JSON-RPC server initialized successfully 🐧")
    return app
