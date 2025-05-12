"""
Response Models for pebbling Server

This module defines Pydantic models for standardized request and response formats
used by the pebbling REST API server.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from uuid import UUID, uuid4
from enum import Enum

class MessageRole(str, Enum):
    """Role of a message sender."""
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"

class HealthResponse(BaseModel):
    """Health check response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field(..., description="Current status of the agent")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Timestamp of the health check")

    class Config:
        schema_extra = {
            "example": {
                "status_code": 200,
                "status": "healthy",
                "message": "Service is running",
                "timestamp": "2023-04-01T12:34:56Z"
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")

    class Config:
        schema_extra = {
            "example": {
                "status_code": 500,
                "status": "error",
                "message": "Internal server error"
            }
        }

class AgentRequest(BaseModel):
    """Agent run request model"""
    input: str = Field(..., description="Input text for the agent", example="Tell me about the latest news in technology")
    user_id: str = Field(..., description="User ID", example="user-123456")
    session_id: str = Field(..., description="Session ID", example="session-789012")
    stream: bool = Field(..., description="Stream the response", example=False)
    
    class Config:
        schema_extra = {
            "example": {
                "input": "What's happening in the stock market today?",
                "user_id": "user-abc123",
                "session_id": "session-xyz456",
                "stream": False
            }
        }


class AgentResponse(BaseModel):
    """Agent run response model"""
    agent_id: UUID = Field(description="Unique identifier for the agent")
    session_id: UUID = Field(description="Session ID for conversation continuity")
    role: MessageRole = Field(default=MessageRole.AGENT, description="Role of the message sender")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata from the agent")
    status: str = Field("success", description="Success status")
    content: str = Field(..., description="Agent response content")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")

    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-123",
                "session_id": "session-xyz456",
                "role": "agent",
                "metadata": {
                    "original_prompt": "What's happening in the stock market today?",
                    "revised_prompt": "What's happening in the stock market today?"
                },
                "status": "success",
                "content": "The stock market is expected to continue its upward trend in the coming weeks.",
                "metrics": {
                    "response_time": "1.234 seconds"
                }
            }
        }


# JSON-RPC Models
class JsonRpcRequest(BaseModel):
    """JSON-RPC request model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request ID")
    method: str = Field(..., description="Method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    source_agent_id: Optional[str] = Field(None, description="Source agent ID")
    destination_agent_id: Optional[str] = Field(None, description="Destination agent ID")
    timestamp: Optional[str] = Field(None, description="Request timestamp")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "act",
                "params": {
                    "input": "What's happening in the stock market today?",
                    "user_id": "user-abc123",
                    "session_id": "session-xyz456"
                },
                "source_agent_id": "agent-123",
                "destination_agent_id": "agent-456",
                "timestamp": "2023-04-01T12:34:56Z"
            }
        }


class JsonRpcErrorDetail(BaseModel):
    """JSON-RPC error detail model"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")

    class Config:
        schema_extra = {
            "example": {
                "code": -32601,
                "message": "Method not found",
                "data": {
                    "original_error": "Method not found"
                }
            }
        }


class JsonRpcError(BaseModel):
    """JSON-RPC error response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version") 
    id: Optional[str] = Field(None, description="Request ID")
    error: JsonRpcErrorDetail = Field(..., description="Error details")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": {
                        "original_error": "Method not found"
                    }
                }
            }
        }


class JsonRpcResponse(BaseModel):
    """JSON-RPC success response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request ID")
    result: Dict[str, Any] = Field(..., description="Response result")

    class Config:
        schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "id": "1",
                "result": {
                    "content": "The stock market is expected to continue its upward trend in the coming weeks.",
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "The stock market is expected to continue its upward trend in the coming weeks."
                        }
                    ],
                    "metrics": {
                        "response_time": "1.234 seconds"
                    }
                }
            }
        }


class Media(BaseModel):
    """Base class for media content."""
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "id": "1",
                "original_prompt": "What's happening in the stock market today?",
                "revised_prompt": "What's happening in the stock market today?"
            }
        }
    

class AudioArtifact(Media):
    """Audio data for agent processing."""
    id: UUID = Field(default_factory=uuid4)  # Unique identifier for the audio artifact
    url: Optional[str] = None  # Remote location for file
    base64_audio: Optional[str] = None  # Base64-encoded audio data
    length: Optional[str] = None
    mime_type: Optional[str] = None

    @model_validator(mode="before")
    def validate_exclusive_audio(cls, data: Any):
        """
        Ensure that either `url` or `base64_audio` is provided, but not both.
        """
        if data.get("url") and data.get("base64_audio"):
            raise ValueError("Provide either `url` or `base64_audio`, not both.")
        if not data.get("url") and not data.get("base64_audio"):
            raise ValueError("Either `url` or `base64_audio` must be provided.")
        return data

    class Config:
        schema_extra = {
            "example": {
                "agent_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "123e4567-e89b-12d3-a456-426614174001",
                "message": "whats the capital of india?",
                "role": "user",
                "metadata": {
                    "source": "mobile_app"
                },
                "stream": False,
                "audio": {
                    "url" : "https://raw.githubusercontent.com/Pebbling-ai/pebble/main/sample_data/audio/sample_audio.mp3"
                }
            }
        }


class ListenRequest(AgentRequest):
    """Combined request for listen endpoint containing both action and audio data."""
    audio: AudioArtifact
