import json
import logging
from typing import Any, Dict, List, Optional, Union

def create_success_response(result: Any, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
    """Create a JSON-RPC success response.
    
    Args:
        result: The result of the method call
        request_id: The request ID to include in the response
        
    Returns:
        JSON-RPC 2.0 success response object
    """
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }


def create_error_response(code: int, message: str, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
    """Create a JSON-RPC error response.
    
    Args:
        code: The error code
        message: The error message
        request_id: The request ID to include in the response
        
    Returns:
        JSON-RPC 2.0 error response object
    """
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": message
        },
        "id": request_id
    }
