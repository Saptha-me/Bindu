"""
Transport layer for MCP communication.

This module provides the transport mechanisms for communication between
Pebble agents and MCP-compatible applications through standard protocols.
"""

import asyncio
import json
import logging
import uuid
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

import aiohttp
from aiohttp import web

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransportType(str, Enum):
    """Supported MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"


class MCPError(Exception):
    """Exception raised for MCP protocol errors."""
    
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


class MCPTransport:
    """Base transport class for MCP communication."""
    
    def __init__(self, transport_type: TransportType = TransportType.STDIO, endpoint: Optional[str] = None):
        """Initialize the MCP transport.
        
        Args:
            transport_type: The type of transport to use (stdio or sse)
            endpoint: The endpoint URL for SSE transport (ignored for stdio)
        """
        self.transport_type = transport_type
        self.endpoint = endpoint
        self.request_handlers = {}
        self.notification_handlers = {}
        self.pending_requests = {}
        self.next_id = 1
    
    async def connect(self) -> None:
        """Connect to the MCP server or client."""
        raise NotImplementedError("Subclasses must implement connect()")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server or client."""
        raise NotImplementedError("Subclasses must implement disconnect()")
    
    async def send_request(self, method: str, params: Dict[str, Any], result_type: Type[T]) -> T:
        """Send a request and wait for a response.
        
        Args:
            method: The method name for the request
            params: The parameters for the request
            result_type: The expected type of the result
            
        Returns:
            The response data converted to the expected type
            
        Raises:
            MCPError: If the response contains an error
        """
        request_id = str(self.next_id)
        self.next_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Create a future for the response
        response_future = asyncio.Future()
        self.pending_requests[request_id] = response_future
        
        try:
            await self._send_message(request)
            result = await response_future
            
            if "error" in result:
                error = result["error"]
                raise MCPError(error["code"], error["message"], error.get("data"))
            
            return result["result"]
        finally:
            # Clean up the pending request
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    async def send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a one-way notification.
        
        Args:
            method: The method name for the notification
            params: The parameters for the notification
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        await self._send_message(notification)
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a raw message.
        
        Args:
            message: The message to send
        """
        raise NotImplementedError("Subclasses must implement _send_message()")
    
    async def _receive_message(self, message: Dict[str, Any]) -> None:
        """Process a received message.
        
        Args:
            message: The received message
        """
        if "id" in message:
            if "method" in message:
                # This is a request
                await self._handle_request(message)
            else:
                # This is a response
                await self._handle_response(message)
        else:
            # This is a notification
            await self._handle_notification(message)
    
    async def _handle_request(self, request: Dict[str, Any]) -> None:
        """Handle an incoming request.
        
        Args:
            request: The request message
        """
        request_id = request["id"]
        method = request["method"]
        params = request.get("params", {})
        
        handler = self.request_handlers.get(method)
        if not handler:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
            await self._send_message(error_response)
            return
        
        try:
            result = await handler(params)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            logger.exception(f"Error handling request for method '{method}'")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
            await self._send_message(error_response)
            return
        
        await self._send_message(response)
    
    async def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle an incoming response.
        
        Args:
            response: The response message
        """
        request_id = response["id"]
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(response)
    
    async def _handle_notification(self, notification: Dict[str, Any]) -> None:
        """Handle an incoming notification.
        
        Args:
            notification: The notification message
        """
        method = notification["method"]
        params = notification.get("params", {})
        
        handler = self.notification_handlers.get(method)
        if handler:
            try:
                await handler(params)
            except Exception:
                logger.exception(f"Error handling notification for method '{method}'")
    
    def register_request_handler(self, method: str, handler: Callable) -> None:
        """Register a handler for incoming requests.
        
        Args:
            method: The method name to handle
            handler: The handler function
        """
        self.request_handlers[method] = handler
    
    def register_notification_handler(self, method: str, handler: Callable) -> None:
        """Register a handler for incoming notifications.
        
        Args:
            method: The method name to handle
            handler: The handler function
        """
        self.notification_handlers[method] = handler


class StdioTransport(MCPTransport):
    """MCP transport using standard input/output."""
    
    def __init__(self):
        """Initialize the stdio transport."""
        super().__init__(TransportType.STDIO)
        self.stdin_reader = None
        self.stdout_writer = None
        self.read_task = None
    
    async def connect(self) -> None:
        """Connect to stdin/stdout."""
        self.stdin_reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(self.stdin_reader)
        
        loop = asyncio.get_event_loop()
        
        # Connect to stdin
        transport, _ = await loop.connect_read_pipe(
            lambda: reader_protocol, asyncio.get_event_loop()._make_read_pipe_transport)
        
        # Connect to stdout
        self.stdout_writer = asyncio.StreamWriter(
            transport, protocol=None, reader=None, loop=loop)
        
        # Start reading input
        self.read_task = asyncio.create_task(self._read_messages())
    
    async def disconnect(self) -> None:
        """Disconnect from stdin/stdout."""
        if self.read_task:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        
        if self.stdout_writer:
            self.stdout_writer.close()
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to stdout.
        
        Args:
            message: The message to send
        """
        if not self.stdout_writer:
            raise RuntimeError("Not connected")
        
        # Serialize the message
        data = json.dumps(message)
        
        # Format as Content-Length header + JSON-RPC message
        content = f"Content-Length: {len(data)}\r\n\r\n{data}"
        
        # Write to stdout
        self.stdout_writer.write(content.encode('utf-8'))
        await self.stdout_writer.drain()
    
    async def _read_messages(self) -> None:
        """Read and process messages from stdin."""
        if not self.stdin_reader:
            raise RuntimeError("Not connected")
        
        try:
            while True:
                # Read the Content-Length header
                header = await self.stdin_reader.readline()
                if not header:
                    break
                
                header = header.decode('utf-8').strip()
                if not header.startswith("Content-Length: "):
                    continue
                
                # Extract the content length
                content_length = int(header[len("Content-Length: "):])
                
                # Skip the empty line after the header
                await self.stdin_reader.readline()
                
                # Read the JSON-RPC message
                content = await self.stdin_reader.readexactly(content_length)
                message = json.loads(content.decode('utf-8'))
                
                # Process the message
                await self._receive_message(message)
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            logger.exception(f"Error reading messages: {e}")


class SSETransport(MCPTransport):
    """MCP transport using HTTP with Server-Sent Events."""
    
    def __init__(self, endpoint: str):
        """Initialize the SSE transport.
        
        Args:
            endpoint: The endpoint URL for the SSE connection
        """
        super().__init__(TransportType.SSE, endpoint)
        self.session = None
        self.sse_response = None
    
    async def connect(self) -> None:
        """Connect to the SSE endpoint."""
        if not self.endpoint:
            raise ValueError("Endpoint URL is required for SSE transport")
        
        self.session = aiohttp.ClientSession()
        
        # Connect to the SSE endpoint
        self.sse_response = await self.session.get(
            f"{self.endpoint}/events",
            headers={"Accept": "text/event-stream"}
        )
        
        # Start reading events
        asyncio.create_task(self._read_events())
    
    async def disconnect(self) -> None:
        """Disconnect from the SSE endpoint."""
        if self.sse_response:
            self.sse_response.close()
        
        if self.session:
            await self.session.close()
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the HTTP endpoint.
        
        Args:
            message: The message to send
        """
        if not self.session:
            raise RuntimeError("Not connected")
        
        # Send the message as a POST request
        async with self.session.post(
            f"{self.endpoint}/jsonrpc",
            json=message,
            headers={"Content-Type": "application/json"}
        ) as response:
            # For requests that expect a response, we'll get it via SSE
            if "id" not in message:
                # For notifications, we don't expect a response
                if response.status != 202:
                    logger.warning(f"Unexpected status code for notification: {response.status}")
    
    async def _read_events(self) -> None:
        """Read and process events from the SSE connection."""
        if not self.sse_response:
            raise RuntimeError("Not connected")
        
        try:
            # Process SSE events
            buffer = ""
            
            async for line in self.sse_response.content:
                line = line.decode('utf-8')
                
                if line.strip() == "":
                    # Empty line indicates the end of an event
                    if buffer:
                        # Process the event
                        lines = buffer.split("\n")
                        event_type = None
                        data = None
                        
                        for event_line in lines:
                            if event_line.startswith("event: "):
                                event_type = event_line[len("event: "):]
                            elif event_line.startswith("data: "):
                                data = event_line[len("data: "):]
                        
                        if event_type == "message" and data:
                            # Process the JSON-RPC message
                            message = json.loads(data)
                            await self._receive_message(message)
                        
                        buffer = ""
                else:
                    # Add the line to the buffer
                    buffer += line
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            logger.exception(f"Error reading SSE events: {e}")
