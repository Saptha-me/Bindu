"""DID resolution and agent information endpoints."""

import logging
from typing import Optional, TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = logging.getLogger("bindu.server.endpoints.did_endpoints")


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request.
    
    Args:
        request: Starlette request object
        
    Returns:
        Client IP address or "unknown"
    """
    return request.client.host if request.client else "unknown"


def _get_did_extension(app: "BinduApplication") -> Optional[object]:
    """Get DID extension from app manifest if available.
    
    Args:
        app: BinduApplication instance
        
    Returns:
        DID extension or None
    """
    return getattr(app.manifest, 'did_extension', None)


async def did_resolve_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Resolve DID and return full DID document.
    
    GET /did/resolve?did=did:bindu:user:agent
    POST /did/resolve with JSON body {"did": "did:bindu:user:agent"}
    """
    client_ip = _get_client_ip(request)
    
    try:
        # Get DID from query param or body
        did: Optional[str] = None
        if request.method == "GET":
            did = request.query_params.get("did")
        else:
            try:
                data = await request.json()
                did = data.get("did")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid JSON in DID resolve request from {client_ip}: {e}")
                return JSONResponse(
                    content={"error": "Invalid JSON body"},
                    status_code=400
                )
        
        if not did:
            logger.warning(f"DID resolve request missing 'did' parameter from {client_ip}")
            return JSONResponse(
                content={"error": "Missing 'did' parameter"},
                status_code=400
            )
        
        # Check if this is our DID
        did_extension = _get_did_extension(app)
        if not did_extension:
            logger.warning(f"DID not found: {did} (requested by {client_ip}) - no DID extension")
            return JSONResponse(
                content={"error": f"DID '{did}' not found"},
                status_code=404
            )
        
        if did != did_extension.did:
            logger.warning(f"DID not found: {did} (requested by {client_ip})")
            return JSONResponse(
                content={"error": f"DID '{did}' not found"},
                status_code=404
            )
        
        logger.debug(f"Resolving DID {did} for {client_ip}")
        did_document = did_extension.get_did_document()
        return JSONResponse(content=did_document)
        
    except Exception as e:
        logger.error(f"Error resolving DID from {client_ip}: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )


async def agent_info_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Get simplified agent information.
    
    GET /agent/info
    """
    client_ip = _get_client_ip(request)
    
    try:
        did_extension = _get_did_extension(app)
        
        if did_extension:
            logger.debug(f"Serving agent info with DID extension to {client_ip}")
            agent_info = did_extension.get_agent_info()
            return JSONResponse(content=agent_info)
        
        # Fallback if no DID extension
        logger.debug(f"Serving basic agent info (no DID extension) to {client_ip}")
        return JSONResponse(
            content={
                "name": app.manifest.name,
                "version": app.manifest.version,
                "description": app.manifest.description,
                "url": app.manifest.url
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving agent info to {client_ip}: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )
