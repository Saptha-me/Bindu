"""
Agno-specific adapter for the Pebble protocol.

This module provides an adapter for integrating Agno agents with the Pebble protocol.
"""
from typing import Any, Optional, Dict
import uuid

from agno.agent import Agent as AgnoAgent

from pebble.agent.base_adapter import BaseProtocolHandler
from pebble.core.protocol import PebbleProtocol


class AgnoProtocolHandler(BaseProtocolHandler):
    """
    Protocol handler implementation for Agno agents.
    """
    def __init__(self, agent: AgnoAgent, agent_id: Optional[str] = None):
        """
        Initialize with an Agno agent.
        
        Args:
            agent: The Agno agent
            agent_id: Optional agent ID
        """
        super().__init__(agent_id)
        self.agent = agent

        # Initialize agent context if it doesn't exist
        if not hasattr(self.agent, "context") or self.agent.context is None:
            self.agent.context = {}
        self.protocol = PebbleProtocol()
    
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the Context method for Agno agents.
        
        Required params:
            - operation: The operation to perform (add, update, delete)
            - key: The key of the context
            
        Optional params:
            - value: The value of the context
            - metadata: Metadata for the context
        """
        request_id = params.get("id", str(uuid.uuid4()))
        operation = params.get("operation", "").lower()
        key = params.get("key")

        if not key:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message="Key is required for Context operations"
            )

        if operation not in ["add", "update", "delete"]:
            return self.protocol.create_error(
                request_id=request_id,
                code=400,
                message=f"Invalid operation '{operation}'. Must be one of: add, update, delete"
            )

        # Handle add operation
        if operation == "add":
            value = params.get("value")
            if not value:
                return self.protocol.create_error(
                    request_id=request_id,
                    code=400,
                    message="Value is required for add operation"
                )

            # Store context with optional metadata
            self.agent.add_context = True
            self.agent.context[key] = {
                "value": value,
                "metadata": params.get("metadata", {})
            }

            # Inject context into Agno agent if possible
            if hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
                self.agent.context[key] = value
            
            return self.protocol.create_response(
                request_id=request_id,
                result={
                    "key": key,
                    "status": "success",
                    "message": "Context added successfully"
                }
            )

        # Handle update operation
        elif operation == "update":
            if key not in self.context:
                return self.protocol.create_error(
                    request_id=request_id,
                    code=404,
                    message=f"Context with key '{key}' not found"
                )
                
            value = params.get("value")
            if value is None:
                return self.protocol.create_error(
                    request_id=request_id,
                    code=400,
                    message="Value is required for Context update operation"
                )
                
            # Update context
            self.agent.context[key]["value"] = value
            if "metadata" in params:
                self.agent.context[key]["metadata"] = params["metadata"]
                
            # Update in Agno agent if possible
            if hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
                self.agent.context[key] = value
                
            return self.protocol.create_response(
                request_id=request_id,
                result={
                    "key": key,
                    "status": "success",
                    "message": "Context updated successfully"
                }
            )
            
        # Handle delete operation
        elif operation == "delete":
            if key not in self.agent.context:
                return self.protocol.create_error(
                    request_id=request_id,
                    code=404,
                    message=f"Context with key '{key}' not found"
                )
                
            # Delete context
            del self.agent.context[key]
            
            # Remove from Agno agent if possible
            if hasattr(self.agent, "context") and isinstance(self.agent.context, dict) and key in self.agent.context:
                del self.agent.context[key]
            
            return self.protocol.create_response(
                request_id=request_id,
                result={
                    "key": key,
                    "status": "success",
                    "message": "Context deleted successfully"
                }
            )