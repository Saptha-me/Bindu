"""
Agno-specific adapter for the Pebble protocol.
"""
from typing import Any, Dict, Optional
import uuid

from agno.agent import Agent as AgnoAgent

from pebble.agent.base_adapter import BaseProtocolHandler
from pebble.core.protocol import PebbleProtocol


class AgnoProtocolHandler(BaseProtocolHandler):
    """Protocol handler implementation for Agno agents."""
    
    def __init__(self, agent: AgnoAgent, agent_id: Optional[str] = None):
        """Initialize with an Agno agent."""
        super().__init__(agent_id)
        self.agent = agent
        
        # Initialize agent context if needed
        if not hasattr(self.agent, "context") or self.agent.context is None:
            self.agent.context = {}
        self.protocol = PebbleProtocol()
    
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Context protocol (add/update/delete operations)."""
        request_id = params.get("id", str(uuid.uuid4()))
        operation = params.get("operation", "").lower()
        key = params.get("key")

        # Validate required parameters
        if not key:
            return self.protocol.create_error(
                request_id=request_id, code=400, 
                message="Key is required for Context operations"
            )

        if operation not in ["add", "update", "delete"]:
            return self.protocol.create_error(
                request_id=request_id, code=400,
                message=f"Invalid operation '{operation}'. Must be one of: add, update, delete"
            )

        # Handle operations
        if operation == "add":
            return self._handle_add(request_id, key, params)
        elif operation == "update":
            return self._handle_update(request_id, key, params)
        else:  # delete
            return self._handle_delete(request_id, key)
            
    def _handle_add(self, request_id: str, key: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add operation."""
        value = params.get("value")
        if not value:
            return self.protocol.create_error(
                request_id=request_id, code=400,
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
            result={"key": key, "status": "success", "message": "Context added successfully"}
        )

    def _handle_update(self, request_id: str, key: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update operation."""
        if key not in self.agent.context:
            return self.protocol.create_error(
                request_id=request_id, code=404,
                message=f"Context with key '{key}' not found"
            )
            
        value = params.get("value")
        if value is None:
            return self.protocol.create_error(
                request_id=request_id, code=400,
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
            result={"key": key, "status": "success", "message": "Context updated successfully"}
        )
        
    def _handle_delete(self, request_id: str, key: str) -> Dict[str, Any]:
        """Handle delete operation."""
        if key not in self.agent.context:
            return self.protocol.create_error(
                request_id=request_id, code=404,
                message=f"Context with key '{key}' not found"
            )
            
        # Delete context
        del self.agent.context[key]
        
        # Remove from Agno agent if possible
        if hasattr(self.agent, "context") and isinstance(self.agent.context, dict) and key in self.agent.context:
            del self.agent.context[key]
        
        return self.protocol.create_response(
            request_id=request_id,
            result={"key": key, "status": "success", "message": "Context deleted successfully"}
        )