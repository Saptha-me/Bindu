"""DID resolution and agent information endpoints."""

from typing import TYPE_CHECKING, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    InternalError,
    InvalidParamsError,
    JSONParseError,
)
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = get_logger("bindu.server.endpoints.did_endpoints")


def _get_did_extension(app: "BinduApplication") -> Optional[object]:
    """Get DID extension from app manifest if available.

    Args:
        app: BinduApplication instance

    Returns:
        DID extension or None
    """
    return getattr(app.manifest, "did_extension", None)


async def did_resolve_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Resolve DID and return full DID document.

    GET /did/resolve?did=did:bindu:user:agent
    POST /did/resolve with JSON body {"did": "did:bindu:user:agent"}
    """
    client_ip = get_client_ip(request)

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
                logger.warning(
                    f"Invalid JSON in DID resolve request from {client_ip}: {e}"
                )
                code, message = extract_error_fields(JSONParseError)
                return jsonrpc_error(code, message, str(e))

        if not did:
            logger.warning(
                f"DID resolve request missing 'did' parameter from {client_ip}"
            )
            code, message = extract_error_fields(InvalidParamsError)
            return jsonrpc_error(code, message, "Missing 'did' parameter")

        # Check if this is our DID
        did_extension = _get_did_extension(app)
        if not did_extension:
            logger.warning(
                f"DID not found: {did} (requested by {client_ip}) - no DID extension"
            )
            code, message = extract_error_fields(InternalError)
            return jsonrpc_error(code, message, f"DID '{did}' not found", status=404)

        # Type narrowing: did_extension is not None here
        if not hasattr(did_extension, "did"):
            logger.error("DID extension missing 'did' attribute")
            code, message = extract_error_fields(InternalError)
            return jsonrpc_error(code, message, "Invalid DID extension", status=500)

        if did != did_extension.did:
            logger.warning(f"DID not found: {did} (requested by {client_ip})")
            code, message = extract_error_fields(InternalError)
            return jsonrpc_error(code, message, f"DID '{did}' not found", status=404)

        logger.debug(f"Resolving DID {did} for {client_ip}")
        did_document = did_extension.get_did_document()
        return JSONResponse(content=did_document)

    except Exception as e:
        logger.error(f"Error resolving DID from {client_ip}: {e}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), status=500)
