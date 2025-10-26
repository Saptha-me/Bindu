# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Message handlers for Bindu server.

This module handles message-related RPC requests including
sending messages and streaming responses.
"""

from __future__ import annotations

import inspect
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    StreamMessageRequest,
    Task,
    TaskSendParams,
)

from ...utils.task_telemetry import trace_task_operation, track_active_task

if TYPE_CHECKING:
    from ..scheduler import Scheduler
    from ..storage import Storage


@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None
    workers: list[Any] | None = None
    context_id_parser: Any = None

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol."""
        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        task: Task = await self.storage.submit_task(context_id, message)

        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events.

        This method returns a StreamingResponse directly to support SSE,
        which will be handled at the application layer.
        """
        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # similar to the "messages/send flow submit the task to the configured storage"
        task: Task = await self.storage.submit_task(context_id, message)

        async def stream_generator():
            """Generate a consumable stream based on the function which was decorated using pebblify."""
            try:
                await self.storage.update_task(task["id"], state="working")
                # yield the initial status update event to indicate processing of the task has started
                status_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "working",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": False,
                }
                yield f"data: {json.dumps(status_event)}\n\n"

                if self.workers and self.manifest:
                    worker = self.workers[0]
                    message_history = await worker._build_complete_message_history(task)
                    manifest_result = self.manifest.run(message_history)

                    if inspect.isasyncgen(manifest_result):
                        async for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    elif inspect.isgenerator(manifest_result):
                        for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    else:
                        if manifest_result:
                            artifact_event = {
                                "kind": "artifact-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "artifact": {
                                    "artifact_id": str(uuid.uuid4()),
                                    "name": "response",
                                    "parts": [
                                        {"kind": "text", "text": str(manifest_result)}
                                    ],
                                },
                                "last_chunk": True,
                            }
                            yield f"data: {json.dumps(artifact_event)}\n\n"

                # Send completion status
                completion_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "completed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                }
                yield f"data: {json.dumps(completion_event)}\n\n"

                # Update task state in storage
                await self.storage.update_task(task["id"], state="completed")
            except Exception as e:
                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await self.storage.update_task(task["id"], state="failed")

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
