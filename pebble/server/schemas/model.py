"""
Response Models for Pebble Server

This module defines Pydantic models for standardized request and response formats
used by the Pebble REST API server.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field(..., description="Current status of the agent")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Timestamp of the health check")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")


class AgentRequest(BaseModel):
    """Agent run request model"""
    input: str = Field(..., description="Input text for the agent")


class AgentResponse(BaseModel):
    """Agent run response model"""
    status_code: int = Field(..., description="HTTP status code")
    status: str = Field("success", description="Success status")
    content: str = Field(..., description="Agent response content")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Messages exchanged")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


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


class JsonRpcErrorDetail(BaseModel):
    """JSON-RPC error detail model"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")


class JsonRpcError(BaseModel):
    """JSON-RPC error response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version") 
    id: Optional[str] = Field(None, description="Request ID")
    error: JsonRpcErrorDetail = Field(..., description="Error details")


class JsonRpcResponse(BaseModel):
    """JSON-RPC success response model"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request ID")
    result: Dict[str, Any] = Field(..., description="Response result")