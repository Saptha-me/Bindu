"""RPC handler utilities for JSON-RPC server."""

import json
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

from loguru import logger

from pebbling.utils.jsonrpc_utils import create_success_response, create_error_response
from pebbling.server.server_security import SecurityMiddleware


async def validate_method(method: str, supported_methods: List[str], request_id: Any) -> Optional[Dict[str, Any]]:
    """Validate if the requested method is supported.
    
    Args:
        method: The method name to validate
        supported_methods: List of supported methods
        request_id: The request ID for response
        
    Returns:
        Error response if method is not supported, None otherwise
    """
    if method not in supported_methods:
        logger.warning(f"Method '{method}' not found or not supported")
        return create_error_response(
            -32601, 
            f"Method '{method}' not found or not supported", 
            request_id
        )
    return None


async def handle_security_method(
    method: str, 
    params: Dict[str, Any], 
    security_handlers: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle security-related methods through appropriate middleware.
    
    Args:
        method: The security method to handle
        params: Method parameters
        security_handlers: Dictionary of security method handlers
        
    Returns:
        Result of the security method handler
    """
    handler = security_handlers[method]
    return await handler(params)


async def handle_protocol_method(
    method: str, 
    params: Dict[str, Any], 
    request_id: Any,
    protocol_handler: Any
) -> Dict[str, Any]:
    """Handle regular protocol methods through protocol handler.
    
    Args:
        method: The protocol method to handle
        params: Method parameters
        request_id: The request ID for response
        protocol_handler: Handler for protocol methods
        
    Returns:
        Response from the protocol handler
    """
    handler_method = getattr(protocol_handler, f"handle_{method}", None)
    if not handler_method:
        logger.error(f"No handler found for method '{method}'")
        return create_error_response(
            -32601, 
            f"No handler found for method '{method}'", 
            request_id
        )
            
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
        handler_method_name = f"handle_{method}"
        logger.error(f"Error in handler method {handler_method_name}: {e}\n{traceback.format_exc()}")
        return create_error_response(-32603, f"Internal error in handler: {str(e)}", request_id)


async def process_jsonrpc_request(
    request: Dict[str, Any],
    supported_methods: List[str],
    security_handlers: Dict[str, Any],
    protocol_handler: Any,
    security_middleware: Optional[SecurityMiddleware] = None
) -> Dict[str, Any]:
    """Process a single JSON-RPC request.
    
    Args:
        request: JSON-RPC request object
        supported_methods: List of supported methods
        security_handlers: Dictionary of security method handlers
        protocol_handler: Handler for protocol methods
        security_middleware: Optional security middleware for signing responses
        
    Returns:
        JSON-RPC response object
    """
    try:
        # Extract method and params
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id", None)
        
        logger.debug(f"Processing JSON-RPC request: method={method}")
        
        # Check if method is supported
        method_error = await validate_method(method, supported_methods, request_id)
        if method_error:
            return method_error
        
        # Handle security-related methods through security middleware
        if method in security_handlers:
            result = await handle_security_method(method, params, security_handlers)
        else:
            # For regular methods, call the protocol handler
            response = await handle_protocol_method(method, params, request_id, protocol_handler)
            return response

        # Sign successful responses that are not security-related if security middleware is available
        if security_middleware and "result" in result and method not in security_handlers:
            result = await security_middleware.sign_message(result)
        
        # Build response
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        return create_success_response(
            result=response,
            request_id=request_id
        )
        
    except json.JSONDecodeError:
        logger.error("Parse error: Invalid JSON")
        return create_error_response(-32700, "Parse error: Invalid JSON", request_id)
    except Exception as e:
        logger.error(f"Unhandled error in JSON-RPC request processing: {e}\n{traceback.format_exc()}")
        return create_error_response(-32603, f"Internal error: {str(e)}", request_id)


async def process_batch_request(
    requests: List[Dict[str, Any]],
    supported_methods: List[str],
    security_handlers: Dict[str, Any],
    protocol_handler: Any,
    security_middleware: Optional[SecurityMiddleware] = None,
    security_check_func: Optional[callable] = None,
    security_failure_response_func: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """Process a batch of JSON-RPC requests.
    
    Args:
        requests: List of JSON-RPC request objects
        supported_methods: List of supported methods
        security_handlers: Dictionary of security method handlers
        protocol_handler: Handler for protocol methods
        security_middleware: Optional security middleware for signing responses
        security_check_func: Function to check if security verification is needed
        security_failure_response_func: Function to create security failure responses
        
    Returns:
        List of JSON-RPC response objects
    """
    responses = []
    
    for req in requests:
        # Verify the request signature if security is enabled and check function is provided
        if security_check_func and security_check_func(req):
            is_secured = await security_check_func(req.get("method"), req.get("params", {}))
            if not is_secured and security_failure_response_func:
                responses.append(security_failure_response_func(req.get("id", None)))
                continue
        
        # Handle the request
        response = await process_jsonrpc_request(
            req, supported_methods, security_handlers, protocol_handler, security_middleware
        )
        responses.append(response)
        
    return responses
