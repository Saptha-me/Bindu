"""REST server implementation for pebbling."""

import os
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebbling.server.schemas.model import (
    AgentResponse,
    ErrorResponse,
    HealthResponse,
    MessageRole
)
from loguru import logger

def create_rest_server(protocol_handler: Optional[Any] = None) -> FastAPI:
    """Create a REST API server for user interaction."""
    # Configure logging
    _configure_logger()
    logger.info("Initializing REST API server")
    
    rest_app = FastAPI(title="pebbling User API")

    # Configure CORS
    rest_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.debug("CORS middleware configured")

    # Create API router with /human prefix
    human_router = APIRouter(prefix="/human")
    logger.debug("Created human API router with /human prefix")

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
        logger.debug(f"Prepared session with ID: {final_session_id} and user ID: {final_user_id}")

        # Apply user-specific context if needed
        if protocol_handler is not None and user_id and hasattr(protocol_handler, "apply_user_context"):
            logger.debug(f"Applying user context for: {final_user_id}")
            protocol_handler.apply_user_context(final_user_id)

        # Initialize session
        if protocol_handler is not None and hasattr(protocol_handler, "_initialize_session"):
            logger.debug(f"Initializing session: {final_session_id}")
            protocol_handler._initialize_session(final_session_id)

        return {"session_id": final_session_id, "user_id": final_user_id}

    def _cleanup_context():
        """Reset context after request processing if supported."""
        if protocol_handler is not None and hasattr(protocol_handler, "reset_context"):
            logger.debug("Resetting protocol handler context")
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
            logger.debug(f"Result already an AgentResponse for session {session_id}")
            return result

        # Convert to AgentResponse if it's not already
        logger.debug(f"Converting result to AgentResponse for session {session_id}")
        agent_id = protocol_handler.agent_id if protocol_handler is not None else None
        
        return AgentResponse(
            agent_id=agent_id,
            session_id=session_id,
            role=MessageRole.AGENT,
            status="success",
            content=str(result),
            metrics={},
        )

    @human_router.get("/health", response_model=HealthResponse)
    async def health_check() -> Union[HealthResponse, ErrorResponse]:
        """Check the health of the agent server."""
        logger.debug("Health check endpoint called")
        try:
            agent_status = (
                getattr(protocol_handler.agent, "get_status", lambda: "healthy")()
                if protocol_handler is not None
                else "healthy"
            )
            logger.info(f"Health check successful, agent status: {agent_status}")
            return HealthResponse(
                status_code=200,
                status=agent_status,
                message="Service is running",
                timestamp=str(uuid.uuid4()),
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Health check failed: {str(e)}",
            )

    @human_router.get("/talk", response_model=HealthResponse)
    async def talk() -> Union[HealthResponse, ErrorResponse]:
        """Check the health of the agent server."""
        logger.debug("Talk endpoint called")
        try:
            agent_status = (
                getattr(protocol_handler.agent, "get_status", lambda: "healthy")()
                if protocol_handler is not None
                else "healthy"
            )
            logger.info(f"Talk endpoint successful, agent status: {agent_status}")
            timestamp = str(uuid.uuid4())
            
            return HealthResponse(
                status_code=200,
                status=agent_status,
                message="Service is running",
                timestamp=timestamp,
            )
        except Exception as e:
            logger.error(f"Talk endpoint failed: {e}")
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Health check failed: {str(e)}",
            )
    

    # Include the human router in the main app
    rest_app.include_router(human_router)
    logger.info("REST API server initialized successfully 🐧")
    
    return rest_app