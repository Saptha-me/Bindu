"""
MCP server implementation for Pebble.

This module provides a server that exposes Pebble agents as MCP-compatible servers,
enabling external MCP clients to interact with Pebble agents.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

import aiohttp
from aiohttp import web

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


class MCPResource:
    """Represents a resource that can be accessed by MCP clients."""
    
    def __init__(
        self,
        uri: str,
        content_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize the MCP resource.
        
        Args:
            uri: The URI of the resource
            content_type: The content type of the resource
            content: The content of the resource
            metadata: Additional metadata about the resource
        """
        self.uri = uri
        self.content_type = content_type
        self.content = content
        self.metadata = metadata or {}


class MCPTool:
    """Represents a tool that can be executed by MCP clients."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        """Initialize the MCP tool.
        
        Args:
            name: The name of the tool
            description: The description of the tool
            parameters: The parameters schema for the tool
            handler: The handler function for the tool
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler


class MCPPrompt:
    """Represents a prompt that can be used by MCP clients."""
    
    def __init__(
        self,
        name: str,
        description: str,
        template: str,
        parameters: Dict[str, Any]
    ):
        """Initialize the MCP prompt.
        
        Args:
            name: The name of the prompt
            description: The description of the prompt
            template: The template for the prompt
            parameters: The parameters schema for the prompt
        """
        self.name = name
        self.description = description
        self.template = template
        self.parameters = parameters


class MCPServer:
    """MCP server implementation for Pebble."""
    
    def __init__(
        self,
        agent_protocol: Union[AgentProtocol, CognitiveAgentProtocol],
        transport_type: TransportType = TransportType.STDIO,
        endpoint: Optional[str] = None
    ):
        """Initialize the MCP server.
        
        Args:
            agent_protocol: The agent protocol to expose as an MCP server
            transport_type: The type of transport to use
            endpoint: The endpoint for the server (for SSE transport)
        """
        self.agent_protocol = agent_protocol
        self.transport_type = transport_type
        self.endpoint = endpoint
        
        # Server capabilities
        self.resources = {}  # URI -> MCPResource
        self.tools = {}  # name -> MCPTool
        self.prompts = {}  # name -> MCPPrompt
        
        # Session management
        self.sessions = {}  # session_id -> session_data
        
        # Initialize transport based on type
        if transport_type == TransportType.STDIO:
            self._setup_stdio_server()
        elif transport_type == TransportType.SSE:
            if not endpoint:
                raise ValueError("Endpoint is required for SSE transport")
            self._setup_sse_server()
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
    
    def _setup_stdio_server(self):
        """Set up a stdio-based server."""
        # This will be implemented when the server is started
        pass
    
    def _setup_sse_server(self):
        """Set up an SSE-based server."""
        # This will be implemented when the server is started
        self.app = web.Application()
        self.app.router.add_route('GET', '/events', self._handle_sse_events)
        self.app.router.add_route('POST', '/jsonrpc', self._handle_jsonrpc_post)
    
    async def _handle_sse_events(self, request):
        """Handle SSE events endpoint."""
        # Set up SSE response
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        # Create a queue for sending events
        queue = asyncio.Queue()
        
        # Store the queue for this client
        client_id = str(uuid.uuid4())
        self.sse_clients[client_id] = queue
        
        try:
            # Send events as they come in
            while True:
                event = await queue.get()
                
                if event is None:
                    # None indicates the client should disconnect
                    break
                
                # Format the event
                data = f"event: message\ndata: {json.dumps(event)}\n\n"
                await response.write(data.encode('utf-8'))
                await response.drain()
        finally:
            # Clean up when the client disconnects
            if client_id in self.sse_clients:
                del self.sse_clients[client_id]
        
        return response
    
    async def _handle_jsonrpc_post(self, request):
        """Handle JSON-RPC requests via POST."""
        # Parse the request
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }, status=400)
        
        # Process the request
        if "method" not in data:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                },
                "id": data.get("id")
            }, status=400)
        
        # Check if this is a notification (no id)
        is_notification = "id" not in data
        
        # Process the method
        try:
            result = await self._process_jsonrpc_method(data["method"], data.get("params", {}))
            
            if is_notification:
                # Notifications don't expect a response
                return web.Response(status=202)
            else:
                # Return the result
                return web.json_response({
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": data["id"]
                })
        except Exception as e:
            logger.exception(f"Error processing method '{data['method']}'")
            
            if is_notification:
                # Notifications don't expect a response
                return web.Response(status=202)
            else:
                # Return the error
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    },
                    "id": data["id"]
                }, status=500)
    
    async def _process_jsonrpc_method(self, method: str, params: Dict[str, Any]) -> Any:
        """Process a JSON-RPC method call.
        
        Args:
            method: The method name
            params: The method parameters
            
        Returns:
            The method result
            
        Raises:
            ValueError: If the method is not supported
        """
        if method == "sampling/complete":
            return await self._handle_sampling_complete(params)
        elif method == "tools/execute":
            return await self._handle_tool_execute(params)
        elif method == "resources/read":
            return await self._handle_resource_read(params)
        elif method == "prompts/list":
            return await self._handle_prompts_list(params)
        elif method == "prompts/use":
            return await self._handle_prompt_use(params)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    async def _handle_sampling_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a sampling/complete request.
        
        Args:
            params: The request parameters
            
        Returns:
            The sampling result
        """
        # Extract parameters
        messages = params.get("messages", [])
        session_id = params.get("session_id", str(uuid.uuid4()))
        
        if not messages:
            raise ValueError("No messages provided")
        
        # Get the last message
        last_message = messages[-1]
        
        # Create a Pebble request
        if isinstance(self.agent_protocol, CognitiveAgentProtocol):
            # Use cognitive protocol if available
            request = CognitiveRequest(
                agent_id=self.agent_protocol.agent_id,
                session_id=session_id,
                content=last_message.get("content", ""),
                stimulus_type=StimulusType.VERBAL,
                metadata={}
            )
            
            # Process with cognitive protocol
            response = await self.agent_protocol.listen(request)
            
            result = {
                "message": {
                    "role": "assistant",
                    "content": response.content
                },
                "cognitive_state": response.cognitive_state
            }
        else:
            # Use standard protocol
            request = ActionRequest(
                agent_id=self.agent_protocol.agent_id,
                session_id=session_id,
                message=last_message.get("content", ""),
                role=MessageRole.USER,
                metadata={}
            )
            
            # Process with standard protocol
            response = await self.agent_protocol.process_action(request)
            
            result = {
                "message": {
                    "role": "assistant",
                    "content": response.message
                }
            }
            
            # Include tool calls if available
            if hasattr(response, "tool_calls") and response.tool_calls:
                result["tool_calls"] = response.tool_calls
        
        return result
    
    async def _handle_tool_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tools/execute request.
        
        Args:
            params: The request parameters
            
        Returns:
            The tool execution result
        """
        # Extract parameters
        tool_name = params.get("name")
        tool_params = params.get("parameters", {})
        session_id = params.get("session_id", str(uuid.uuid4()))
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        # Check if the tool exists
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Execute the tool
        tool = self.tools[tool_name]
        result = await tool.handler(session_id, tool_params)
        
        return {"result": result}
    
    async def _handle_resource_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a resources/read request.
        
        Args:
            params: The request parameters
            
        Returns:
            The resource content
        """
        # Extract parameters
        uri = params.get("uri")
        position = params.get("position")
        length = params.get("length")
        
        if not uri:
            raise ValueError("Resource URI is required")
        
        # Check if the resource exists
        if uri not in self.resources:
            raise ValueError(f"Resource '{uri}' not found")
        
        # Get the resource
        resource = self.resources[uri]
        
        # Extract the requested portion
        content = resource.content
        if isinstance(content, str):
            if position is not None:
                if length is not None:
                    content = content[position:position + length]
                else:
                    content = content[position:]
        
        return {
            "uri": uri,
            "content_type": resource.content_type,
            "content": content,
            "metadata": resource.metadata
        }
    
    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a prompts/list request.
        
        Args:
            params: The request parameters
            
        Returns:
            The list of available prompts
        """
        prompts = []
        
        for name, prompt in self.prompts.items():
            prompts.append({
                "name": name,
                "description": prompt.description,
                "parameters": prompt.parameters
            })
        
        return {"prompts": prompts}
    
    async def _handle_prompt_use(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a prompts/use request.
        
        Args:
            params: The request parameters
            
        Returns:
            The result of using the prompt
        """
        # Extract parameters
        prompt_name = params.get("name")
        prompt_params = params.get("parameters", {})
        session_id = params.get("session_id", str(uuid.uuid4()))
        
        if not prompt_name:
            raise ValueError("Prompt name is required")
        
        # Check if the prompt exists
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        # Get the prompt
        prompt = self.prompts[prompt_name]
        
        # Fill the template with parameters
        template = prompt.template
        for param_name, param_value in prompt_params.items():
            template = template.replace(f"{{{param_name}}}", str(param_value))
        
        # Create a Pebble request
        if isinstance(self.agent_protocol, CognitiveAgentProtocol):
            # Use cognitive protocol if available
            request = CognitiveRequest(
                agent_id=self.agent_protocol.agent_id,
                session_id=session_id,
                content=template,
                stimulus_type=StimulusType.VERBAL,
                metadata={}
            )
            
            # Process with cognitive protocol
            response = await self.agent_protocol.act(request)
            
            result = {
                "message": {
                    "role": "assistant",
                    "content": response.content
                },
                "cognitive_state": response.cognitive_state
            }
        else:
            # Use standard protocol
            request = ActionRequest(
                agent_id=self.agent_protocol.agent_id,
                session_id=session_id,
                message=template,
                role=MessageRole.SYSTEM,
                metadata={}
            )
            
            # Process with standard protocol
            response = await self.agent_protocol.process_action(request)
            
            result = {
                "message": {
                    "role": "assistant",
                    "content": response.message
                }
            }
        
        return result
    
    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource that can be accessed by MCP clients.
        
        Args:
            resource: The resource to register
        """
        self.resources[resource.uri] = resource
    
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool that can be executed by MCP clients.
        
        Args:
            tool: The tool to register
        """
        self.tools[tool.name] = tool
    
    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt that can be used by MCP clients.
        
        Args:
            prompt: The prompt to register
        """
        self.prompts[prompt.name] = prompt
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self.transport_type == TransportType.STDIO:
            # For stdio, we read from stdin and write to stdout
            # This is a simple implementation that doesn't handle concurrent requests
            stdin_reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(stdin_reader)
            
            loop = asyncio.get_event_loop()
            
            # Connect stdin
            await loop.connect_read_pipe(lambda: protocol, asyncio.get_event_loop()._make_read_pipe_transport)
            
            # Connect stdout
            stdout_transport, _ = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, asyncio.get_event_loop()._make_write_pipe_transport)
            stdout_writer = asyncio.StreamWriter(stdout_transport, None, stdin_reader, loop)
            
            # Process stdin
            while True:
                # Read the Content-Length header
                header = await stdin_reader.readline()
                header = header.decode('utf-8').strip()
                
                if not header:
                    # End of input
                    break
                
                if not header.startswith("Content-Length: "):
                    continue
                
                # Parse the content length
                content_length = int(header[len("Content-Length: "):])
                
                # Skip the empty line
                await stdin_reader.readline()
                
                # Read the JSON-RPC message
                content = await stdin_reader.readexactly(content_length)
                message = json.loads(content.decode('utf-8'))
                
                # Process the message
                if "method" in message:
                    if "id" in message:
                        # This is a request
                        try:
                            result = await self._process_jsonrpc_method(message["method"], message.get("params", {}))
                            
                            # Send the response
                            response = {
                                "jsonrpc": "2.0",
                                "result": result,
                                "id": message["id"]
                            }
                        except Exception as e:
                            # Send error response
                            response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32000,
                                    "message": str(e)
                                },
                                "id": message["id"]
                            }
                        
                        # Write the response
                        response_json = json.dumps(response)
                        stdout_writer.write(f"Content-Length: {len(response_json)}\r\n\r\n{response_json}".encode('utf-8'))
                        await stdout_writer.drain()
                    else:
                        # This is a notification
                        try:
                            await self._process_jsonrpc_method(message["method"], message.get("params", {}))
                        except Exception as e:
                            logger.exception(f"Error processing notification '{message['method']}': {e}")
        elif self.transport_type == TransportType.SSE:
            # For SSE, we start an HTTP server
            self.sse_clients = {}
            
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, 'localhost', 8080)
            await site.start()
            
            logger.info("MCP server started on http://localhost:8080")
            
            # Keep the server running
            while True:
                await asyncio.sleep(3600)  # Wait for 1 hour
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if self.transport_type == TransportType.SSE:
            # Stop the HTTP server
            await self.app.shutdown()
            
            # Notify all clients
            for client_queue in self.sse_clients.values():
                await client_queue.put(None)
