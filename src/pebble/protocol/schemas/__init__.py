"""
Schemas for agent communication protocols.
"""
from .message import (
    BaseMessage,
    TextMessage, 
    CommandMessage,
    ResponseMessage,
    ErrorMessage
)
from .agent import AgentInfo

__all__ = [
    "BaseMessage",
    "TextMessage",
    "CommandMessage",
    "ResponseMessage",
    "ErrorMessage",
    "AgentInfo"
]
