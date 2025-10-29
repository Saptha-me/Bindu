# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Context handlers for Bindu server.

This module handles context-related RPC requests including
listing and clearing contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bindu.common.protocol.types import (
    ClearContextsRequest,
    ClearContextsResponse,
    ContextNotFoundError,
    ListContextsRequest,
    ListContextsResponse,
)

from bindu.utils.task_telemetry import trace_context_operation

from bindu.server.storage import Storage


@dataclass
class ContextHandlers:
    """Handles context-related RPC requests."""

    storage: Storage[Any]
    error_response_creator: Any = None

    @trace_context_operation("list_contexts")
    async def list_contexts(self, request: ListContextsRequest) -> ListContextsResponse:
        """List all contexts in storage."""
        contexts = await self.storage.list_contexts(request["params"].get("length"))

        if contexts is None:
            return self.error_response_creator(
                ListContextsResponse,
                request["id"],
                ContextNotFoundError,
                "No contexts found",
            )

        return ListContextsResponse(jsonrpc="2.0", id=request["id"], result=contexts)

    @trace_context_operation("clear_context")
    async def clear_context(
        self, request: ClearContextsRequest
    ) -> ClearContextsResponse:
        """Clear a context from storage."""
        context_id = request["params"].get("context_id")

        try:
            await self.storage.clear_context(context_id)
        except ValueError as e:
            # Context not found
            return self.error_response_creator(
                ClearContextsResponse, request["id"], ContextNotFoundError, str(e)
            )

        return ClearContextsResponse(
            jsonrpc="2.0",
            id=request["id"],
            result={
                "message": f"Context {context_id} and all associated tasks cleared successfully"
            },
        )
