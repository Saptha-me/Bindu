"""A2A protocol endpoint for agent-to-agent communication."""

import logging
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import a2a_request_ta, a2a_response_ta
from bindu.server.utils.request_utils import get_client_ip

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = logging.getLogger("bindu.server.endpoints.a2a_protocol")

# Method dispatcher mapping JSON-RPC methods to task_manager handlers
METHOD_HANDLERS = {
    "message/send": "send_message",
    "tasks/get": "get_task",
    "tasks/cancel": "cancel_task",
    "tasks/list": "list_tasks",
    "contexts/list": "list_contexts",
    "tasks/clear": "clear_tasks",
    "tasks/feedback": "task_feedback",
}


def _jsonrpc_error(
    code: int, message: str, data: str | None = None, request_id: str | None = None, status: int = 400
) -> JSONResponse:
    """Create a JSON-RPC error response."""
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message, "data": data},
            "id": request_id,
        },
        status_code=status,
    )


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
            return _jsonrpc_error(-32700, "Parse error", str(e))
        
        method = a2a_request.get("method")
        request_id = a2a_request.get("id")
        
        logger.debug(f"A2A request from {client_ip}: method={method}, id={request_id}")
        
        handler_name = METHOD_HANDLERS.get(method)
        if handler_name is None:
            logger.warning(f"Unsupported A2A method '{method}' from {client_ip}")
            return _jsonrpc_error(-32601, "Method not found", f"Method '{method}' is not implemented", request_id, 404)
        
        handler = getattr(app.task_manager, handler_name)
        jsonrpc_response = await handler(a2a_request)
        
        logger.debug(f"A2A response to {client_ip}: method={method}, id={request_id}")
        
        return Response(
            content=a2a_response_ta.dump_json(jsonrpc_response, by_alias=True, serialize_as_any=True),
            media_type="application/json",
        )
        
    except Exception as e:
        logger.error(f"Error processing A2A request from {client_ip}: {e}", exc_info=True)
        return _jsonrpc_error(-32603, "Internal error", str(e), request_id, 500)
