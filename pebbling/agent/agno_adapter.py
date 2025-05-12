"""
Agno-specific adapter for the pebbling protocol.
"""
from typing import Any, Dict, Optional, List
from uuid import UUID, uuid4

from agno.agent import Agent as AgnoAgent
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from pebbling.agent.base_adapter import BaseProtocolHandler
from pebbling.core.protocol import pebblingProtocol
from pebbling.server.schemas.model import AudioArtifact, AgentResponse

# Initialize Rich console
console = Console()


class AgnoProtocolHandler(BaseProtocolHandler):
    """Protocol handler implementation for Agno agents."""
    
    def __init__(self, agent: AgnoAgent, agent_id: Optional[str] = None):
        """Initialize with an Agno agent."""
        super().__init__(agent_id)
        self.agent = agent

        capabilities = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, 'name'):
                    capabilities.append(tool.name)
        
        # Initialize agent context if needed
        if not hasattr(self.agent, "context") or self.agent.context is None:
            self.agent.context = {}
        self.protocol = pebblingProtocol()
        
        # Initialize user-specific contexts
        self.user_contexts = {}

        # Store session history for continuity
        self.sessions = {}

    def _initialize_session(self, session_id, stream):
        """Helper to initialize session and set agent properties"""
        # Initialize session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "agent_state": {},
                "stream": stream
            }
            
        # Set stream mode if applicable
        if hasattr(self.agent, 'stream'):
            self.agent.stream = stream

    def _extract_response(self, result):
        """Extract content and tool calls from Agno response"""
        tool_calls = []
        # Extract tool calls if they exist and are visible
        if result and hasattr(self.agent, 'show_tool_calls') and self.agent.show_tool_calls:
            if hasattr(result, 'tool_calls'):
                tool_calls = result.tool_calls
            elif hasattr(result, 'get_tool_calls'):
                tool_calls = result.get_tool_calls()
        
        # Extract the response content
        if result:
            if hasattr(result, 'response'):
                response_content = result.response
            elif hasattr(result, 'content'):
                response_content = result.content
            else:
                response_content = str(result)
        else:
            response_content = "No response generated."
            
        return response_content, tool_calls

    def _create_response(
        self, 
        session_id: UUID,
        response_content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> AgentResponse:
        """Create response and update session history"""
        # Store the response in session history
        self.sessions[session_id]["history"].append({
            "role": MessageRole.AGENT,
            "content": response_content
        })
        
        # Create and return the response
        return AgentResponse(
            agent_id=self.agent_id,
            session_id=session_id,
            content=response_content,
            role=MessageRole.AGENT,
            metadata=request.metadata,
            tool_calls=tool_calls if tool_calls else None
        )
    
    def apply_user_context(self, user_id: str) -> None:
        """
        Apply user-specific context to the agent.
        
        Args:
            user_id: ID of the user to apply context for
        """
        # Store original context to restore after request
        self._original_context = self.agent.context.copy() if hasattr(self.agent, "context") else {}
        
        # Apply user-specific context if it exists
        if user_id in self.user_contexts:
            # Update agent context with user-specific context
            for key, context_item in self.user_contexts[user_id].items():
                self.agent.context[key] = context_item["value"]
                
            # Log with rich formatting
            context_text = Text()
            for key, item in self.user_contexts[user_id].items():
                context_text.append(f"\n  {key}: ", style="bright_cyan")
                context_text.append(f"{item['value']}", style="bright_green")
                if 'metadata' in item and item['metadata']:
                    context_text.append(f" (metadata: {item['metadata']})", style="dim")
            
            console.print(Panel.fit(
                Text(f"🔄 Applied context for user: ", style="bold blue") + 
                Text(user_id, style="bold yellow") + context_text,
                title="[bright_cyan]Context Applied[/bright_cyan]",
                border_style="blue"
            ))
            logger.info(f"Applied context for user {user_id}")
        else:
            console.print(Text(f"⚠️ No specific context found for user: {user_id}", style="yellow"))
            logger.warning(f"No specific context found for user {user_id}")
            
    def reset_context(self) -> None:
        """Reset to original context after processing a user request."""
        if hasattr(self, "_original_context"):
            self.agent.context = self._original_context
            delattr(self, "_original_context")
            console.print(Text("🔄 Context reset to original state", style="bright_green"))
            logger.info("Agent context reset to original state")
            
    async def handle_Context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Context protocol (add/update/delete operations)."""
        request_id = params.get("id", str(uuid.uuid4()))
        operation = params.get("operation", "").lower()
        key = params.get("key")
        user_id = params.get("user_id")  # Optional user ID for user-specific context

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

        # If user_id is provided, manage user-specific context
        if user_id:
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {}
            
            # Redirect to user-specific context operations
            if operation == "add":
                return self._handle_add(request_id, key, params, user_id)
            elif operation == "update":
                return self._handle_update(request_id, key, params, user_id)
            else:  # delete
                return self._handle_delete(request_id, key, user_id)
        else:
            # Handle global context operations (original behavior)
            if operation == "add":
                return self._handle_add(request_id, key, params)
            elif operation == "update":
                return self._handle_update(request_id, key, params)
            else:  # delete
                return self._handle_delete(request_id, key)
            
    def _handle_add(self, request_id: str, key: str, params: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle add operation."""
        value = params.get("value")
        if not value:
            return self.protocol.create_error(
                request_id=request_id, code=400,
                message="Value is required for add operation"
            )

        # Store context with optional metadata
        context_data = {
            "value": value,
            "metadata": params.get("metadata", {})
        }
        
        if user_id:
            # Store in user-specific context
            self.user_contexts[user_id][key] = context_data
            message = f"Context added for user {user_id} successfully"
            console.print(Panel(
                Text(f"✅ Added context key: ", style="bold green") + 
                Text(key, style="bright_cyan") + 
                Text(" for user: ", style="green") + 
                Text(user_id, style="bright_yellow"),
                title="[bright_green]Context Added[/bright_green]",
                border_style="green"
            ))
            logger.success(f"Added context key '{key}' for user {user_id}")
        else:
            # Store in global context
            self.agent.context[key] = context_data
            
            # Inject context into Agno agent if possible
            if hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
                self.agent.context[key] = value
            
            message = "Context added successfully"
            console.print(Panel(
                Text(f"✅ Added global context key: ", style="bold green") + 
                Text(key, style="bright_cyan") + 
                Text(f" with value type: {type(value).__name__}", style="dim"),
                title="[bright_green]Global Context Added[/bright_green]",
                border_style="green"
            ))
            logger.success(f"Added global context key '{key}'")
        
        return self.protocol.create_response(
            request_id=request_id,
            result={"key": key, "status": "success", "message": message}
        )

    def _handle_update(self, request_id: str, key: str, params: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle update operation."""
        context_store = self.user_contexts.get(user_id, {}) if user_id else self.agent.context
        
        if key not in context_store:
            return self.protocol.create_error(
                request_id=request_id, code=404,
                message=f"Context with key '{key}' not found" + (f" for user {user_id}" if user_id else "")
            )
            
        value = params.get("value")
        if value is None:
            return self.protocol.create_error(
                request_id=request_id, code=400,
                message="Value is required for Context update operation"
            )
            
        # Update context
        context_store[key]["value"] = value
        if "metadata" in params:
            context_store[key]["metadata"] = params["metadata"]
            
        # If global context, update in Agno agent if possible
        if not user_id and hasattr(self.agent, "context") and isinstance(self.agent.context, dict):
            self.agent.context[key] = value
            
        message = "Context updated successfully" + (f" for user {user_id}" if user_id else "")
        
        # Log the update with rich formatting
        if user_id:
            console.print(Panel(
                Text(f"🔄 Updated context key: ", style="bold blue") + 
                Text(key, style="bright_cyan") + 
                Text(" for user: ", style="blue") + 
                Text(user_id, style="bright_yellow"),
                title="[bright_blue]Context Updated[/bright_blue]",
                border_style="blue"
            ))
            logger.info(f"Updated context key '{key}' for user {user_id}")
        else:
            console.print(Panel(
                Text(f"🔄 Updated global context key: ", style="bold blue") + 
                Text(key, style="bright_cyan"),
                title="[bright_blue]Global Context Updated[/bright_blue]",
                border_style="blue"
            ))
            logger.info(f"Updated global context key '{key}'")
        return self.protocol.create_response(
            request_id=request_id,
            result={"key": key, "status": "success", "message": message}
        )
        
    def _handle_delete(self, request_id: str, key: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle delete operation."""
        context_store = self.user_contexts.get(user_id, {}) if user_id else self.agent.context
        
        if key not in context_store:
            return self.protocol.create_error(
                request_id=request_id, code=404,
                message=f"Context with key '{key}' not found" + (f" for user {user_id}" if user_id else "")
            )
            
        # Delete context
        del context_store[key]
        
        # If global context, remove from Agno agent if possible
        if not user_id and hasattr(self.agent, "context") and isinstance(self.agent.context, dict) and key in self.agent.context:
            del self.agent.context[key]
        
        message = "Context deleted successfully" + (f" for user {user_id}" if user_id else "")
        
        # Log the deletion with rich formatting
        if user_id:
            console.print(Panel(
                Text(f"🗑️ Deleted context key: ", style="bold red") + 
                Text(key, style="bright_cyan") + 
                Text(" for user: ", style="red") + 
                Text(user_id, style="bright_yellow"),
                title="[bright_red]Context Deleted[/bright_red]",
                border_style="red"
            ))
            logger.warning(f"Deleted context key '{key}' for user {user_id}")
        else:
            console.print(Panel(
                Text(f"🗑️ Deleted global context key: ", style="bold red") + 
                Text(key, style="bright_cyan"),
                title="[bright_red]Global Context Deleted[/bright_red]",
                border_style="red"
            ))
            logger.warning(f"Deleted global context key '{key}'")
        return self.protocol.create_response(
            request_id=request_id,
            result={"key": key, "status": "success", "message": message}
        )

    def act(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process a text request and generate a response
        
        Args:
            message: The text message to process
            session_id: Session identifier for conversation continuity
            
        Returns:
            AgentResponse with the agent's reply
        """
        # Store request in session history
        self.sessions[session_id]["history"].append({
            "role": "user",
            "content": message
        })
            
        try:
            # Process the request
            result = self.agent.run(message)
            response_content, tool_calls = self._extract_response(result)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            response_content = f"Error processing request: {str(e)}"
            tool_calls = []
        finally:
            # Reset context if needed
            if hasattr(self, "reset_context"):
                self.reset_context()
        
        # Create and return the response
        return self._create_response(session_id, response_content, tool_calls)
    
    def listen(self, audio: AudioArtifact, session_id: str = None) -> Dict[str, Any]:
        """
        Acts in the environment and updates its internal cognitive state.
        
        Args:
            audio: The audio input to process
            session_id: Session identifier for conversation continuity
            
        Returns:
            Dict[str, Any]: The response from the agent
        """
        # Store the request in session history with audio reference
        self.sessions[session_id]["history"].append({
            "role": "user",
            "content": "Process this audio input",
            "has_audio": True
        })

        # Import Agno's Audio class
        from agno.media import Audio
        
        # Create Audio object based on input type
        try:
            if audio.url:
                # Agno's Audio class supports direct URL handling
                agno_audio = Audio(url=audio.url)
            elif audio.base64_audio:
                audio_bytes = self._decode_base64(audio.base64_audio)
                agno_audio = Audio(content=audio_bytes)

            result = self.agent.run(agno_audio, **agent_kwargs)
            response_content, tool_calls = self._extract_response(result)

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            response_content = f"Error processing request: {str(e)}"
            tool_calls = []
        finally:
            # Reset context if needed
            if hasattr(self, "reset_context"):
                self.reset_context()
            
        return self._create_response(session_id, response_content, tool_calls)
    