from starlette.requests import Request
from starlette.responses import Response

from pebbling.common.protocol.types import pebble_request_ta, pebble_response_ta


async def agent_run_endpoint(request: Request) -> Response:
    """This is the main endpoint for the Pebble server.

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
    pebble_request = pebble_request_ta.validate_json(data)

    # Access task_manager from the app instance
    task_manager = request.app.task_manager

    if pebble_request["method"] == "message/send":
        jsonrpc_response = await task_manager.send_message(pebble_request)
    elif pebble_request["method"] == "tasks/get":
        jsonrpc_response = await task_manager.get_task(pebble_request)
    elif pebble_request["method"] == "tasks/cancel":
        jsonrpc_response = await task_manager.cancel_task(pebble_request)
    else:
        raise NotImplementedError(f"Method {pebble_request['method']} not implemented.")

    return Response(
        content=pebble_response_ta.dump_json(jsonrpc_response, by_alias=True), media_type="application/json"
    )
