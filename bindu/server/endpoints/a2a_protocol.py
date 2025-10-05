"""A2A protocol endpoint for agent-to-agent communication."""

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import a2a_request_ta, a2a_response_ta

if TYPE_CHECKING:
    from ..applications import PebbleApplication


async def agent_run_endpoint(app: "PebbleApplication", request: Request) -> Response:
    """Main endpoint for the Pebble server A2A protocol.

    Although the specification allows freedom of choice and implementation, I'm pretty sure about some decisions.

    1. The server will always either send a "submitted" or a "failed" on `tasks/send`.
        Never a "completed" on the first message.
    2. There are three possible ends for the task:
        2.1. The task was "completed" successfully.
        2.2. The task was "canceled".
        2.3. The task "failed".
    3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
    """
    data = await request.body()
    a2a_request = a2a_request_ta.validate_json(data)

    if a2a_request["method"] == "message/send":
        jsonrpc_response = await app.task_manager.send_message(a2a_request)
    elif a2a_request["method"] == "tasks/get":
        jsonrpc_response = await app.task_manager.get_task(a2a_request)
    elif a2a_request["method"] == "tasks/cancel":
        jsonrpc_response = await app.task_manager.cancel_task(a2a_request)
    elif a2a_request["method"] == "tasks/list":
        jsonrpc_response = await app.task_manager.list_tasks(a2a_request)
    elif a2a_request["method"] == "contexts/list":
        jsonrpc_response = await app.task_manager.list_contexts(a2a_request)
    elif a2a_request["method"] == "tasks/clear":
        jsonrpc_response = await app.task_manager.clear_tasks(a2a_request)
    elif a2a_request["method"] == "tasks/feedback":
        jsonrpc_response = await app.task_manager.task_feedback(a2a_request)
    else:
        raise NotImplementedError(f"Method {a2a_request['method']} not implemented.")
    
    return Response(
        content=a2a_response_ta.dump_json(jsonrpc_response, by_alias=True, serialize_as_any=True),
        media_type="application/json",
    )
