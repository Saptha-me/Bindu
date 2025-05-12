import uuid
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pebbling.server.schemas.model import (
    HealthResponse, 
    ErrorResponse, 
    AgentRequest, 
    AgentResponse,
    MessageRole,
    ListenRequest,
    ViewRequest
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
    
    @rest_app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Check the health of the agent server"""
        try:
            agent_status = getattr(protocol_handler.agent, "get_status", lambda: "healthy")()
            return HealthResponse(
                status_code=200,
                status=agent_status,
                message="Service is running",
                timestamp=str(uuid.uuid4())
            )
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Health check failed: {str(e)}"
            )

    @rest_app.post("/act", response_model=AgentResponse)
    async def act_agent(request_data: AgentRequest):
        """Run the agent with the provided input"""
        try:
            if not request_data.input.strip():
                # Return a JSONResponse directly to bypass response_model validation
                return JSONResponse(
                    status_code=400,
                    content={
                        "status_code": 400,
                        "status": "error",
                        "message": "Input text is required"
                    }
                )

            session_id = request_data.session_id or str(uuid.uuid4())
            user_id = request_data.user_id or "user_" + str(uuid.uuid4())
            
            protocol_handler._initialize_session(session_id)
            
            # Apply user-specific context if user_id is provided
            if request_data.user_id and hasattr(protocol_handler, "apply_user_context"):
                protocol_handler.apply_user_context(request_data.user_id)
            
            # Execute the agent
            
            result = protocol_handler.act(
                message=request_data.input,
                session_id=session_id,
                user_id=user_id)

            if not isinstance(result, AgentResponse):
                # Convert to AgentResponse if it's not already
                return AgentResponse(
                    agent_id=protocol_handler.agent_id,
                    session_id=session_id,
                    role=MessageRole.AGENT,
                    status="success",
                    content=str(result),
                    metrics={}
                )
            return result
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}"
            )
    
    @rest_app.post("/act1", response_model=AgentResponse)
    async def act1(request_data: AgentRequest):
        """Run the agent with the provided input"""
        try:
            if not request_data.input.strip():
                # Return a JSONResponse directly to bypass response_model validation
                return JSONResponse(
                    status_code=400,
                    content={
                        "status_code": 400,
                        "status": "error",
                        "message": "Input text is required"
                    }
                )

            # Generate session ID if not provided
            session_id = request_data.session_id or str(uuid.uuid4())
            user_id = request_data.user_id or "user_" + str(uuid.uuid4())
            
            # Apply user-specific context if user_id is provided
            if request_data.user_id and hasattr(protocol_handler, "apply_user_context"):
                protocol_handler.apply_user_context(user_id)

            protocol_handler._initialize_session(session_id, request_data.stream)

            result = protocol_handler.agent.run(
                session_id=session_id,
                message=request_data.input).to_dict()
            
            # Execute the agent with simplified parameters
            result = protocol_handler.act(
                message=request_data.input,
                session_id=session_id,
                stream=request_data.stream
            )
            
            # Ensure we're returning an AgentResponse
            if not isinstance(result, AgentResponse):
                # Convert to AgentResponse if it's not already
                return AgentResponse(
                    agent_id=protocol_handler.agent_id,
                    session_id=session_id,
                    role=MessageRole.AGENT,
                    status="success",
                    content=str(result),
                    metrics={}
                )
            return result
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}"
            )

    @rest_app.post("/listen", response_model=AgentResponse)
    async def listen_agent(listen_request: ListenRequest):
        """Run the agent with the provided input"""
        try:
            if not listen_request.audio:
                # Return a JSONResponse directly to bypass response_model validation
                return JSONResponse(
                    status_code=400,
                    content={
                        "status_code": 400,
                        "status": "error",
                        "message": "Input text is required"
                    }
                )

            # Generate session ID if not provided
            session_id = listen_request.session_id or str(uuid.uuid4())
            user_id = listen_request.user_id or "user_" + str(uuid.uuid4())

            # Apply user-specific context if user_id is provided
            if listen_request.user_id and hasattr(protocol_handler, "apply_user_context"):
                protocol_handler.apply_user_context(user_id)

            protocol_handler._initialize_session(session_id)

            # Execute the agent with all required parameters
            result = protocol_handler.listen(
                audio=listen_request.audio,
                session_id=session_id
            )

            # Ensure we're returning an AgentResponse
            if not isinstance(result, AgentResponse):
                # Convert to AgentResponse if it's not already
                return AgentResponse(
                    agent_id=protocol_handler.agent_id,
                    session_id=session_id,
                    role=MessageRole.AGENT,
                    status="success",
                    content=str(result),
                    metrics={}
                )
            return result
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}"
            ) 
    
    @rest_app.post("/view", response_model=AgentResponse)
    async def view_agent(view_request: ViewRequest):
        """Run the agent with the provided input"""
        try:
            if not view_request.media:
                # Return a JSONResponse directly to bypass response_model validation
                return JSONResponse(
                    status_code=400,
                    content={
                        "status_code": 400,
                        "status": "error",
                        "message": "Input text is required"
                    }
                )

            # Generate session ID if not provided
            session_id = view_request.session_id or str(uuid.uuid4())
            user_id = view_request.user_id or "user_" + str(uuid.uuid4())

            # Apply user-specific context if user_id is provided
            if view_request.user_id and hasattr(protocol_handler, "apply_user_context"):
                protocol_handler.apply_user_context(user_id)

            protocol_handler._initialize_session(session_id)

            # Execute the agent with all required parameters
            result = protocol_handler.view(
                message=view_request.input,  # Pass input as message parameter
                media=view_request.media,
                session_id=session_id,
                user_id=user_id
            )

            # Ensure we're returning an AgentResponse
            if not isinstance(result, AgentResponse):
                # Convert to AgentResponse if it's not already
                return AgentResponse(
                    agent_id=protocol_handler.agent_id,
                    session_id=session_id,
                    role=MessageRole.AGENT,
                    status="success",
                    content=str(result),
                    metrics={}
                )
            return result
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}"
            ) 
    
    # Return the FastAPI app
    return rest_app