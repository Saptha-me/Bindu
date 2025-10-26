"""DID resolution and agent information endpoints."""

from typing import TYPE_CHECKING, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    InternalError,
    InvalidParamsError,
    JSONParseError,
)
from bindu.utils.did_utils import check_did_match, get_did_extension, validate_did_extension
from bindu.utils.endpoint_utils import handle_endpoint_errors
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = get_logger("bindu.server.endpoints.did_endpoints")


@handle_endpoint_errors("DID resolve")
async def did_resolve_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Resolve DID and return full W3C-compliant DID document."""
    client_ip = get_client_ip(request)

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

    # Validate DID extension
    did_extension = get_did_extension(app)
    is_valid, error_msg = validate_did_extension(did_extension, "did")
    
    if not is_valid:
        logger.warning(f"DID validation failed: {error_msg} (requested by {client_ip})")
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, f"DID '{did}' not found", status=404)

    # Check if requested DID matches our DID
    if not check_did_match(did_extension, did):
        logger.warning(
            f"DID mismatch - requested: {did}, our DID: {did_extension.did} (from {client_ip})"
        )
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, f"DID '{did}' not found", status=404)

    logger.debug(f"Resolving DID {did} for {client_ip}")
    did_document = did_extension.get_did_document()
    return JSONResponse(content=did_document)

