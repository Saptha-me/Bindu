"""REST server implementation for pebbling."""

import uuid
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebbling.server.schemas.model import (
    AgentRequest,
    AgentResponse,
    ErrorResponse,
    HealthResponse,
    ListenRequest,
    MessageRole,
    ViewRequest,
)


def create_rest_server(protocol_handler: Optional[Any] = None) -> FastAPI:
    """Create a REST API server for user interaction."""
    rest_app = FastAPI(title="pebbling User API")

    # Configure CORS
    rest_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _prepare_session(user_id: Optional[str], session_id: Optional[str]) -> Dict[str, str]:
        """Prepare session and user IDs, apply context if needed.

        Args:
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            Dictionary with finalized session and user IDs
        """
        # Generate IDs if not provided
        final_session_id = session_id or str(uuid.uuid4())
        final_user_id = user_id or f"user_{str(uuid.uuid4())}"

        # Apply user-specific context if needed
        if protocol_handler is not None and user_id and hasattr(protocol_handler, "apply_user_context"):
            protocol_handler.apply_user_context(final_user_id)

        # Initialize session
        if protocol_handler is not None and hasattr(protocol_handler, "_initialize_session"):
            protocol_handler._initialize_session(final_session_id)

        return {"session_id": final_session_id, "user_id": final_user_id}

    def _cleanup_context():
        """Reset context after request processing if supported."""
        if protocol_handler is not None and hasattr(protocol_handler, "reset_context"):
            protocol_handler.reset_context()

    def _ensure_agent_response(result: Any, session_id: str) -> AgentResponse:
        """Ensure the result is an AgentResponse.

        Args:
            result: Result from protocol handler
            session_id: Session identifier

        Returns:
            AgentResponse instance
        """
        if isinstance(result, AgentResponse):
            return result

        # Convert to AgentResponse if it's not already
        return AgentResponse(
            agent_id=(protocol_handler.agent_id if protocol_handler is not None else None),
            session_id=session_id,
            role=MessageRole.AGENT,
            status="success",
            content=str(result),
            metrics={},
        )

    @rest_app.get("/health", response_model=HealthResponse)
    async def health_check() -> Union[HealthResponse, ErrorResponse]:
        """Check the health of the agent server."""
        try:
            agent_status = (
                getattr(protocol_handler.agent, "get_status", lambda: "healthy")()
                if protocol_handler is not None
                else "healthy"
            )
            return HealthResponse(
                status_code=200,
                status=agent_status,
                message="Service is running",
                timestamp=str(uuid.uuid4()),
            )
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Health check failed: {str(e)}",
            )

    @rest_app.post("/act", response_model=AgentResponse)
    async def act(
        request_data: AgentRequest,
    ) -> Union[AgentResponse, ErrorResponse, JSONResponse]:
        """Process a text request with the agent."""
        try:
            # Validate input
            if not request_data.input.strip():
                return JSONResponse(
                    status_code=400,
                    content={
                        "status_code": 400,
                        "status": "error",
                        "message": "Input text is required",
                    },
                )

            # Prepare session and context
            session_info = _prepare_session(user_id=request_data.user_id, session_id=request_data.session_id)

            # Execute the agent
            result = (
                protocol_handler.act(
                    message=request_data.input,
                    session_id=session_info["session_id"],
                    user_id=session_info["user_id"],
                )
                if protocol_handler is not None
                else None
            )

            # Ensure correct response type
            return _ensure_agent_response(result, session_info["session_id"])

        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}",
            )

    @rest_app.post("/listen", response_model=AgentResponse)
    async def listen(
        listen_request: ListenRequest,
    ) -> Union[AgentResponse, ErrorResponse, JSONResponse]:
        """Process an audio request with the agent."""
        if not listen_request.audio:
            return JSONResponse(
                status_code=400,
                content={
                    "status_code": 400,
                    "status": "error",
                    "message": "Audio input is required",
                },
            )

        # Prepare session and context
        session_info = _prepare_session(user_id=listen_request.user_id, session_id=listen_request.session_id)

        try:
            # Execute the agent
            result = (
                protocol_handler.listen(
                    message=listen_request.input,
                    audio=listen_request.audio,
                    session_id=session_info["session_id"],
                    user_id=session_info["user_id"],
                )
                if protocol_handler is not None
                else None
            )

            # Ensure correct response type
            return _ensure_agent_response(result, session_info["session_id"])

        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Audio processing failed: {str(e)}",
            )

    @rest_app.post("/view", response_model=AgentResponse)
    async def view(
        view_request: ViewRequest,
    ) -> Union[AgentResponse, ErrorResponse, JSONResponse]:
        """Process a media request with the agent."""
        # Validate input
        if not view_request.media:
            return JSONResponse(
                status_code=400,
                content={
                    "status_code": 400,
                    "status": "error",
                    "message": "Media input is required",
                },
            )

        # Prepare session and context
        session_info = _prepare_session(user_id=view_request.user_id, session_id=view_request.session_id)

        try:
            # Execute the agent
            result = (
                protocol_handler.view(
                    message=view_request.input,
                    media=view_request.media,
                    session_id=session_info["session_id"],
                    user_id=session_info["user_id"],
                )
                if protocol_handler is not None
                else None
            )

            # Ensure correct response type
            return _ensure_agent_response(result, session_info["session_id"])

        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Media processing failed: {str(e)}",
            )

    return rest_app
