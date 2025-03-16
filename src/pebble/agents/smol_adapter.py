"""
Adapter for SmolAgent integration with Pebble protocol.
"""
from typing import Any, Dict, List, Optional, Union

from smolagents import CodeAgent

from ..protocol.schemas.agent import AgentCapability, AgentType
from ..protocol.schemas.message import BaseMessage, TextMessage, CommandMessage, ResponseMessage
from .base import BaseAgentAdapter


class SmolAgentAdapter(BaseAgentAdapter):
    """
    Adapter for SmolAgent integration with the Pebble protocol.
    
    This adapter provides the necessary translation layer between
    SmolAgent's API and the standardized Pebble communication protocol.
    """
    
    def __init__(self, agent: CodeAgent):
        """
        Initialize the adapter with a SmolAgent instance.
        
        Args:
            agent: The SmolAgent instance to adapt
        """
        super().__init__(agent)
        self.agent_id = getattr(agent, 'id', None) or id(agent)
        self.agent_name = getattr(agent, 'name', 'SmolAgent')
    
    async def send_message(self, message: BaseMessage) -> Optional[BaseMessage]:
        """
        Send a message to the SmolAgent and return any response.
        
        Args:
            message: The message to send to the agent
            
        Returns:
            Optional[BaseMessage]: The agent's response if any
        """
        if isinstance(message, TextMessage):
            # Convert protocol message to SmolAgent-compatible format
            response_content = await self.agent.chat(message.content)
            
            # Create response message
            return ResponseMessage(
                sender_id=str(self.agent_id),
                receiver_id=message.sender_id,
                in_response_to=message.message_id,
                status="success",
                content=response_content
            )
        
        elif isinstance(message, CommandMessage):
            # Handle commands based on the specific command
            if message.command == "execute_task":
                task = message.arguments.get("task")
                context = message.arguments.get("context", {})
                
                try:
                    response_content = await self.agent.execute_task(task, **context)
                    status = "success"
                except Exception as e:
                    response_content = str(e)
                    status = "failure"
                
                return ResponseMessage(
                    sender_id=str(self.agent_id),
                    receiver_id=message.sender_id,
                    in_response_to=message.message_id,
                    status=status,
                    content=response_content
                )
        
        return None
    
    async def receive_message(self, message: BaseMessage) -> None:
        """
        Process a received message from another agent.
        
        Args:
            message: The message received from another agent
        """
        # SmolAgent doesn't have a specific message queue,
        # so we'll just log the message for now
        print(f"SmolAgent {self.agent_name} received message: {message}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the adapted SmolAgent.
        
        Returns:
            Dict[str, Any]: Information about the agent
        """
        return {
            "agent_id": str(self.agent_id),
            "name": self.agent_name,
            "agent_type": AgentType.SMOL,
            "capabilities": self.get_capabilities(),
            "supported_protocols": ["json", "text"],
            "description": getattr(self.agent, 'description', None) or "SmolAgent adapted for Pebble protocol"
        }
    
    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities of the SmolAgent.
        
        Returns:
            List[str]: List of capability identifiers
        """
        capabilities = [
            AgentCapability.TEXT_GENERATION,
            AgentCapability.CODE_GENERATION,
            AgentCapability.REASONING
        ]
        
        # Check if the agent has additional capabilities
        if hasattr(self.agent, 'has_tool_use') and self.agent.has_tool_use:
            capabilities.append(AgentCapability.TOOL_USAGE)
        
        if hasattr(self.agent, 'memory') and self.agent.memory:
            capabilities.append(AgentCapability.MEMORY)
        
        return capabilities
    
    def supports_protocol(self, protocol_name: str) -> bool:
        """
        Check if the SmolAgent supports a specific protocol.
        
        Args:
            protocol_name: The name of the protocol to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return protocol_name.lower() in ["json", "text"]
