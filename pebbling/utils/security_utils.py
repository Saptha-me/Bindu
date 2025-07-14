"""Security utilities for JSON-RPC server."""

from typing import Any, Dict, Optional
from loguru import logger

from pebbling.server.server_security import SecurityMiddleware
from pebbling.security.mtls.certificate_manager import CertificateManager


async def verify_security_requirements(
    method: str,
    params: Dict[str, Any],
    security_middleware: Optional[SecurityMiddleware],
    certificate_manager: Optional[CertificateManager]
) -> bool:
    """Check if a method meets all security requirements.
    
    Args:
        method: The method name to check
        params: Method parameters
        security_middleware: The DID-based security middleware
        certificate_manager: The certificate manager for mTLS security
        
    Returns:
        True if security is satisfied, False otherwise
    """
    # Only certain methods require full security
    if method in ["act"]:  # Add other secure methods as needed
        source_agent_id = params.get("source_agent_id")
        
        # Check DID verification
        if not security_middleware or not security_middleware.is_agent_verified(source_agent_id):
            logger.warning(f"DID verification failed for agent {source_agent_id}")
            return False
            
        # Check mTLS verification
        if not certificate_manager or not certificate_manager.is_connection_verified(source_agent_id):
            logger.warning(f"mTLS verification failed for agent {source_agent_id}")
            return False
            
    return True


def needs_security_check(
    request: Dict[str, Any],
    security_middleware: Optional[SecurityMiddleware],
    certificate_manager: Optional[CertificateManager]
) -> bool:
    """Determine if a request needs security verification.
    
    Args:
        request: JSON-RPC request object
        security_middleware: The DID-based security middleware
        certificate_manager: The certificate manager for mTLS security
        
    Returns:
        True if security check is needed, False otherwise
    """
    security_methods = ["exchange_did", "verify_identity", "exchange_certificates", "verify_connection"]
    return (
        security_middleware and 
        certificate_manager and 
        request.get("method") not in security_methods
    )


def create_security_failure_response(request_id: Any) -> Dict[str, Any]:
    """Create a response for failed security verification.
    
    Args:
        request_id: The request ID for response
        
    Returns:
        Error response object
    """
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32600,
            "message": "Request signature verification failed"
        },
        "id": request_id
    }


def register_security_handlers(
    security_middleware: Optional[SecurityMiddleware],
    certificate_manager: Optional[CertificateManager]
) -> Dict[str, Any]:
    """Register security method handlers based on available middleware.
    
    Args:
        security_middleware: The DID-based security middleware
        certificate_manager: The certificate manager for mTLS security
        
    Returns:
        Dictionary mapping method names to handler functions
    """
    security_handlers = {}
    
    # If security middleware is provided, register security method handlers
    if security_middleware:
        security_handlers.update({
            "exchange_did": security_middleware.handle_exchange_did,
            "verify_identity": security_middleware.handle_verify_identity,
        })
        
    # If certificate manager is provided, register mTLS method handlers
    if certificate_manager:
        security_handlers.update({
            "exchange_certificates": certificate_manager.handle_exchange_certificates,
            "verify_connection": certificate_manager.handle_verify_connection,
        })
        
    return security_handlers
