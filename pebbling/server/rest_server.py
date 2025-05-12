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
    #ListenRequest
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
    
    @rest_app.post("/run", response_model=AgentResponse)
    async def run_agent(request_data: AgentRequest):
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
            
            # Apply user-specific context if user_id is provided
            if request_data.user_id and hasattr(protocol_handler, "apply_user_context"):
                protocol_handler.apply_user_context(request_data.user_id)
            
            # Execute the agent
            result = protocol_handler.agent.run(request_data.input).to_dict()

            return AgentResponse(
                status_code=200,
                status="success",
                content=result["content"],
                messages=result["messages"],
                metrics=result["metrics"]
            )
        except Exception as e:
            return ErrorResponse(
                status_code=500,
                status="error",
                message=f"Agent execution failed: {str(e)}"
            )

    # @rest_app.post("/listen", response_model=AgentResponse)
    # async def listen_agent(listen_request: ListenRequest):
    #     """Run the agent with the provided input"""
    #     try:
    #         if not request_data.input.strip():
    #             # Return a JSONResponse directly to bypass response_model validation
    #             return JSONResponse(
    #                 status_code=400,
    #                 content={
    #                     "status_code": 400,
    #                     "status": "error",
    #                     "message": "Input text is required"
    #                 }
    #             )
            
    #         # Apply user-specific context if user_id is provided
    #         if request_data.user_id and hasattr(protocol_handler, "apply_user_context"):
    #             protocol_handler.apply_user_context(request_data.user_id)
            
    #         # Execute the agent
    #         result = protocol_handler.agent.run(request_data.input).to_dict()

    #         return AgentResponse(
    #             status_code=200,
    #             status="success",
    #             content=result["content"],
    #             messages=result["messages"],
    #             metrics=result["metrics"]
    #         )
    #     except Exception as e:
    #         return ErrorResponse(
    #             status_code=500,
    #             status="error",
    #             message=f"Agent execution failed: {str(e)}"
    #         )