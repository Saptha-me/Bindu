"""A2A protocol endpoint for agent-to-agent communication."""

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import (
    InternalError,
    JSONParseError,
    MethodNotFoundError,
    a2a_request_ta,
    a2a_response_ta,
)
from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = get_logger("bindu.server.endpoints.a2a_protocol")


async def agent_run_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Handle A2A protocol requests for agent-to-agent communication.

    Protocol Behavior:
    1. The server will always either send a "submitted" or a "failed" on `tasks/send`.
        Never a "completed" on the first message.
    2. There are three possible ends for the task:
        2.1. The task was "completed" successfully.
        2.2. The task was "canceled".
        2.3. The task "failed".
    3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
    """
    client_ip = get_client_ip(request)
    request_id = None

    try:
        data = await request.body()

        try:
            a2a_request = a2a_request_ta.validate_json(data)
        except Exception as e:
            logger.warning(f"Invalid A2A request from {client_ip}: {e}")
            code, message = extract_error_fields(JSONParseError)
            return jsonrpc_error(code, message, str(e))

        method = a2a_request.get("method")
        request_id = a2a_request.get("id")

        logger.debug(f"A2A request from {client_ip}: method={method}, id={request_id}")

        handler_name = app_settings.agent.method_handlers.get(method)
        if handler_name is None:
            logger.warning(f"Unsupported A2A method '{method}' from {client_ip}")
            code, message = extract_error_fields(MethodNotFoundError)
            return jsonrpc_error(
                code, message, f"Method '{method}' is not implemented", request_id, 404
            )

        handler = getattr(app.task_manager, handler_name)
        jsonrpc_response = await handler(a2a_request)

        logger.debug(f"A2A response to {client_ip}: method={method}, id={request_id}")

        resp = Response(
            content=a2a_response_ta.dump_json(
                jsonrpc_response, by_alias=True, serialize_as_any=True
            ),
            media_type="application/json",
        )

        if x402_is_requested(request):
            resp = x402_add_header(resp)

        return resp

    except Exception as e:
        logger.error(
            f"Error processing A2A request from {client_ip}: {e}", exc_info=True
        )
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), request_id, 500)
