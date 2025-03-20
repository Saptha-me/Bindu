"""
MCP client adapter for Pebble.

This module provides an adapter that allows Pebble agents to interact with
MCP-compatible servers, enabling access to standardized tools, resources, and prompts.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pebble.core.protocol import AgentProtocol
from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.mcp.transport import MCPTransport, TransportType
from pebble.schemas.models import (
    ActionRequest,
    ActionResponse,
    CognitiveRequest,
    CognitiveResponse,
    MessageRole,
    StimulusType
)

logger = logging.getLogger(__name__)


class MCPClientAdapter(AgentProtocol):
    """Adapter for MCP clients to use external MCP servers."""
    
    def __init__(
        self,
        transport: MCPTransport,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize the MCP client adapter.
        
        Args:
            transport: The MCP transport to use for communication
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
        """
        # Default MCP capabilities
        mcp_capabilities = capabilities or ["resources", "tools", "prompts", "sampling"]
        
        super().__init__(
            agent=None,  # No underlying agent - using MCP servers instead
            agent_id=agent_id,
            name=name or "MCP Client",
            framework="mcp",
            capabilities=mcp_capabilities,
            metadata=metadata or {}
        )
        
        self.transport = transport
        self.sessions = {}
    
    async def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process an action request by forwarding to an MCP server.
        
        Args:
            request: The action request to process
            
        Returns:
            ActionResponse: The response from the MCP server
        """
        session_id = request.session_id
        
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "context": {}
            }
        
        # Store the request message in session history
        self.sessions[session_id]["history"].append({
            "role": request.role.value.lower(),  # Convert to lowercase for MCP compatibility
            "content": request.message
        })
        
        # Create MCP sampling request
        mcp_request = {
            "messages": self.sessions[session_id]["history"],
            "model": self.metadata.get("model", {}),
            "stream": request.stream if hasattr(request, "stream") else False
        }
        
        # Add context references if available
        if "context" in self.sessions[session_id] and self.sessions[session_id]["context"]:
            mcp_request["context"] = self.sessions[session_id]["context"]
        
        try:
            # Send sampling request to MCP server
            result = await self.transport.send_request(
                "sampling/complete",
                mcp_request,
                dict
            )
            
            # Extract response from MCP result
            if "message" in result:
                response_content = result["message"].get("content", "")
                response_role = result["message"].get("role", "assistant")
            else:
                response_content = str(result)
                response_role = "assistant"
            
            # Store the response in session history
            self.sessions[session_id]["history"].append({
                "role": response_role,
                "content": response_content
            })
            
            # Extract tool calls if present
            tool_calls = None
            if "tool_calls" in result:
                tool_calls = result["tool_calls"]
            
            # Create and return the response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=session_id,
                message=response_content,
                role=MessageRole.AGENT,
                metadata=request.metadata,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            logger.error(f"Error processing request with MCP server: {e}")
            
            # Return error response
            return ActionResponse(
                agent_id=self.agent_id,
                session_id=session_id,
                message=f"Error communicating with MCP server: {str(e)}",
                role=MessageRole.AGENT,
                metadata=request.metadata
            )
    
    async def execute_tool(self, session_id: str, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server.
        
        Args:
            session_id: The session ID
            tool_name: The name of the tool to execute
            parameters: The parameters for the tool
            
        Returns:
            The result of the tool execution
        """
        try:
            # Send tool execution request to MCP server
            result = await self.transport.send_request(
                "tools/execute",
                {
                    "name": tool_name,
                    "parameters": parameters,
                    "session_id": session_id
                },
                dict
            )
            
            return result.get("result")
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            raise
    
    async def read_resource(self, uri: str, position: Optional[int] = None, length: Optional[int] = None) -> Dict[str, Any]:
        """Read a resource from the MCP server.
        
        Args:
            uri: The URI of the resource to read
            position: Optional position to start reading from
            length: Optional length to read
            
        Returns:
            The resource content
        """
        try:
            # Prepare request parameters
            params = {"uri": uri}
            if position is not None:
                params["position"] = position
            if length is not None:
                params["length"] = length
            
            # Send resource read request to MCP server
            result = await self.transport.send_request(
                "resources/read",
                params,
                dict
            )
            
            return result
        except Exception as e:
            logger.error(f"Error reading resource '{uri}': {e}")
            raise
    
    async def get_prompts(self) -> List[Dict[str, Any]]:
        """Get available prompts from the MCP server.
        
        Returns:
            List of available prompts
        """
        try:
            # Send prompts list request to MCP server
            result = await self.transport.send_request(
                "prompts/list",
                {},
                dict
            )
            
            return result.get("prompts", [])
        except Exception as e:
            logger.error(f"Error getting prompts: {e}")
            raise
    
    async def use_prompt(self, session_id: str, prompt_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Use a prompt from the MCP server.
        
        Args:
            session_id: The session ID
            prompt_name: The name of the prompt to use
            parameters: The parameters for the prompt
            
        Returns:
            The result of using the prompt
        """
        try:
            # Send prompt use request to MCP server
            result = await self.transport.send_request(
                "prompts/use",
                {
                    "name": prompt_name,
                    "parameters": parameters,
                    "session_id": session_id
                },
                dict
            )
            
            # Update session history with the prompt result
            if session_id in self.sessions and "message" in result:
                self.sessions[session_id]["history"].append({
                    "role": result["message"].get("role", "assistant"),
                    "content": result["message"].get("content", "")
                })
            
            return result
        except Exception as e:
            logger.error(f"Error using prompt '{prompt_name}': {e}")
            raise


class MCPCognitiveAdapter(CognitiveAgentProtocol):
    """Cognitive adapter for MCP communication."""
    
    def __init__(
        self,
        transport: MCPTransport,
        agent_id: Optional[UUID] = None,
        name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cognitive_capabilities: Optional[List[str]] = None
    ):
        """Initialize the MCP cognitive adapter.
        
        Args:
            transport: The MCP transport to use for communication
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Name of the agent
            capabilities: List of capabilities the agent has
            metadata: Additional metadata about the agent
            cognitive_capabilities: List of cognitive capabilities the agent has
        """
        # Default MCP capabilities
        mcp_capabilities = capabilities or ["resources", "tools", "prompts", "sampling"]
        
        # Default cognitive capabilities
        cog_capabilities = cognitive_capabilities or ["act", "listen", "think"]
        
        super().__init__(
            agent=None,  # No underlying agent - using MCP servers instead
            agent_id=agent_id,
            name=name or "MCP Cognitive Agent",
            framework="mcp",
            capabilities=mcp_capabilities,
            metadata=metadata or {},
            cognitive_capabilities=cog_capabilities
        )
        
        self.transport = transport
        self.mcp_client = MCPClientAdapter(
            transport=transport,
            agent_id=agent_id,
            name=name,
            capabilities=capabilities,
            metadata=metadata
        )
    
    async def act(self, request: CognitiveRequest) -> CognitiveResponse:
        """Acts in the environment using MCP and updates internal cognitive state.
        
        Args:
            request: The cognitive request containing context and parameters
            
        Returns:
            CognitiveResponse: The response with action results and updated state
        """
        # Update cognitive state with request context
        self._update_cognitive_state(request)
        
        # Prepare action context for MCP
        action_context = {
            "current_state": self.cognitive_state,
            "instruction": request.content,
            "stimulus_type": StimulusType.ACTION.value
        }
        
        # Create action request for MCP client
        action_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=json.dumps(action_context),
            role=MessageRole.SYSTEM,
            metadata=request.metadata
        )
        
        # Process with MCP client
        action_response = await self.mcp_client.process_action(action_request)
        
        # Update cognitive state with action results
        self._update_cognitive_state_from_response(action_response)
        
        # Return cognitive response
        return CognitiveResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=action_response.message,
            stimulus_type=StimulusType.ACTION,
            cognitive_state=self.cognitive_state,
            metadata=request.metadata
        )
    
    async def listen(self, request: CognitiveRequest) -> CognitiveResponse:
        """Listens to another agent using MCP and updates internal cognitive state.
        
        Args:
            request: The cognitive request containing the verbal input
            
        Returns:
            CognitiveResponse: The response with listening results and updated state
        """
        # Update cognitive state with request context
        self._update_cognitive_state(request)
        
        # Prepare listen context for MCP
        listen_context = {
            "current_state": self.cognitive_state,
            "instruction": request.content,
            "stimulus_type": StimulusType.VERBAL.value
        }
        
        # Create action request for MCP client
        action_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=json.dumps(listen_context),
            role=MessageRole.USER,
            metadata=request.metadata
        )
        
        # Process with MCP client
        action_response = await self.mcp_client.process_action(action_request)
        
        # Update cognitive state with listening results
        self._update_cognitive_state_from_response(action_response)
        
        # Return cognitive response
        return CognitiveResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=action_response.message,
            stimulus_type=StimulusType.VERBAL,
            cognitive_state=self.cognitive_state,
            metadata=request.metadata
        )
    
    async def think(self, request: CognitiveRequest) -> CognitiveResponse:
        """Thinks about a situation using MCP and updates internal cognitive state.
        
        Args:
            request: The cognitive request containing the situation to think about
            
        Returns:
            CognitiveResponse: The response with thinking results and updated state
        """
        # Update cognitive state with request context
        self._update_cognitive_state(request)
        
        # Prepare think context for MCP
        think_context = {
            "current_state": self.cognitive_state,
            "instruction": request.content,
            "stimulus_type": StimulusType.COGNITIVE.value
        }
        
        # Use a prompt for thinking if available
        try:
            prompt_result = await self.mcp_client.use_prompt(
                session_id=request.session_id,
                prompt_name="cognitive_thinking",
                parameters={
                    "context": think_context,
                    "instruction": request.content
                }
            )
            
            thinking_content = prompt_result.get("message", {}).get("content", "")
        except Exception:
            # Fall back to standard sampling if prompt is not available
            action_request = ActionRequest(
                agent_id=self.agent_id,
                session_id=request.session_id,
                message=json.dumps(think_context),
                role=MessageRole.SYSTEM,
                metadata=request.metadata
            )
            
            # Process with MCP client
            action_response = await self.mcp_client.process_action(action_request)
            thinking_content = action_response.message
        
        # Update cognitive state with thinking results
        self.cognitive_state["mental_state"]["last_thought"] = thinking_content
        
        # Add to episodic memory
        self.cognitive_state["episodic_memory"].append({
            "type": "thought",
            "content": thinking_content,
            "timestamp": request.metadata.get("timestamp", None)
        })
        
        # Return cognitive response
        return CognitiveResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=thinking_content,
            stimulus_type=StimulusType.COGNITIVE,
            cognitive_state=self.cognitive_state,
            metadata=request.metadata
        )
    
    async def see(self, request: CognitiveRequest) -> CognitiveResponse:
        """Interprets visual input using MCP and updates internal cognitive state.
        
        Args:
            request: The cognitive request containing the visual input
            
        Returns:
            CognitiveResponse: The response with visual interpretation and updated state
        """
        # Check if visual input is included
        if not request.content:
            return CognitiveResponse(
                agent_id=self.agent_id,
                session_id=request.session_id,
                content="No visual input provided",
                stimulus_type=StimulusType.VISUAL,
                cognitive_state=self.cognitive_state,
                metadata=request.metadata
            )
        
        # Update cognitive state with request context
        self._update_cognitive_state(request)
        
        # For visual input, we need to store the content as a resource
        # This typically would involve uploading the content to the MCP server
        # For now, we'll simulate this by passing the content directly
        
        # Prepare see context for MCP
        see_context = {
            "current_state": self.cognitive_state,
            "visual_input": request.content,
            "stimulus_type": StimulusType.VISUAL.value
        }
        
        # Create action request for MCP client
        action_request = ActionRequest(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=json.dumps(see_context),
            role=MessageRole.SYSTEM,
            metadata=request.metadata
        )
        
        # Process with MCP client
        action_response = await self.mcp_client.process_action(action_request)
        
        # Update cognitive state with visual results
        self._update_cognitive_state_from_response(action_response)
        
        # Return cognitive response
        return CognitiveResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            content=action_response.message,
            stimulus_type=StimulusType.VISUAL,
            cognitive_state=self.cognitive_state,
            metadata=request.metadata
        )
