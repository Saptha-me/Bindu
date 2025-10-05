"""DID resolution and agent information endpoints."""

import json
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from ..applications import PebbleApplication


async def did_resolve_endpoint(app: "PebbleApplication", request: Request) -> Response:
    """Resolve DID and return full DID document.
    
    GET /did/resolve?did=did:bindu:user:agent
    POST /did/resolve with JSON body {"did": "did:bindu:user:agent"}
    """
    # Get DID from query param or body
    did = None
    if request.method == "GET":
        did = request.query_params.get("did")
    else:
        data = await request.json()
        did = data.get("did")
    
    if not did:
        return Response(
            content=json.dumps({"error": "Missing 'did' parameter"}),
            status_code=400,
            media_type="application/json"
        )
    
    # Check if this is our DID
    if hasattr(app.manifest, 'did_extension') and app.manifest.did_extension:
        if did == app.manifest.did_extension.did:
            did_document = app.manifest.did_extension.get_did_document()
            return Response(
                content=json.dumps(did_document, indent=2),
                media_type="application/json"
            )
    
    return Response(
        content=json.dumps({"error": f"DID '{did}' not found"}),
        status_code=404,
        media_type="application/json"
    )


async def agent_info_endpoint(app: "PebbleApplication", request: Request) -> Response:
    """Get simplified agent information.
    
    GET /agent/info
    """
    if hasattr(app.manifest, 'did_extension') and app.manifest.did_extension:
        agent_info = app.manifest.did_extension.get_agent_info()
        return Response(
            content=json.dumps(agent_info, indent=2),
            media_type="application/json"
        )
    
    # Fallback if no DID extension
    return Response(
        content=json.dumps({
            "name": app.manifest.name,
            "version": app.manifest.version,
            "description": app.manifest.description,
            "url": app.manifest.url
        }, indent=2),
        media_type="application/json"
    )
