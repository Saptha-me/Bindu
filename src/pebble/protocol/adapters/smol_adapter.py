"""
Adapter for SmolAgent integration with Pebble protocol.
"""
from typing import Any, Dict, Optional

from smolagents import CodeAgent

from ..protocol import Protocol, Message, MessageType, AgentType


class SmolAdapter:
    """
    Adapter for SmolAgent integration with the Pebble protocol.
    
    This adapter provides the translation layer between SmolAgent's
    API and the standardized Pebble communication protocol.
    """
    
    def __init__(self, agent: CodeAgent):
        """
        Initialize the adapter with a SmolAgent instance.
        
        Args:
            agent: The SmolAgent instance to adapt
        """
        self.agent = agent
        self.protocol = Protocol()
    
    @property
    def agent_id(self) -> str:
        """Get the agent's unique identifier."""
        return getattr(self.agent, 'id', None) or str(id(self.agent))
    
    @property
    def agent_type(self) -> str:
        """Get the agent's type."""
        return AgentType.SMOL
    
    async def send_message(self, message: Message) -> Optional[Message]:
        """
        Send a message to the SmolAgent and get its response.
        
        Args:
            message: Protocol message to send
            
        Returns:
            Optional[Message]: Response message if any
        """
        # Adapt the message for SmolAgent format
        adapted_message = Protocol.adapt_for_agent_type(message, self.agent_type)
        
        # Process based on message type
        if message.type == MessageType.TEXT:
            # For text messages, use the chat method
            response_content = await self.agent.chat(message.content)
            
            # Create response message
            return self.create_response(message, response_content)
            
        elif message.type == MessageType.COMMAND:
            # Handle command messages based on command content
            command = message.content.get("command") if isinstance(message.content, dict) else None
            args = message.content.get("args", {}) if isinstance(message.content, dict) else {}
            
            if command == "execute_task":
                try:
                    result = await self.agent.execute_task(args.get("task", ""), **args.get("context", {}))
                    return self.create_response(message, {"result": result, "status": "success"})
                except Exception as e:
                    return self.create_response(
                        message, 
                        {"error": str(e), "status": "error"},
                        {"error_type": type(e).__name__}
                    )
                    
        # Default: no response for unsupported message types
        return None
    
    async def receive_message(self, message: Message) -> None:
        """
        Process a message received from another agent.
        
        SmolAgent doesn't have built-in message receiving capabilities,
        so this implementation just acknowledges receipt.
        
        Args:
            message: Protocol message received
        """
        print(f"SmolAgent {getattr(self.agent, 'name', 'Agent')} received message: {message.id}")
    
    def create_response(self, 
                        to_message: Message, 
                        content: Any, 
                        metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Create a response message to another message.
        
        Args:
            to_message: The message being responded to
            content: Response content
            metadata: Additional metadata (optional)
            
        Returns:
            Message: The response message
        """
        meta = {"in_response_to": to_message.id}
        if metadata:
            meta.update(metadata)
            
        return Protocol.create_message(
            message_type=MessageType.RESPONSE,
            sender=self.agent_id,
            receiver=to_message.sender,
            content=content,
            metadata=meta
        )
