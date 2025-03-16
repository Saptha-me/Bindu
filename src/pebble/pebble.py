from __future__ import annotations

from typing import Optional, Union, Dict, Any, List
from dataclasses import dataclass

from .protocol.protocol import Protocol, Message, MessageType, AgentType
from .protocol.coordinator import ProtocolCoordinator
from .protocol.adapters import SmolAdapter, AgnoAdapter, CrewAdapter

# Type aliases for agent types
SmolAgentType = Any  # Replace with actual SmolAgent type when available
AgnoAgentType = Any  # Replace with actual AgnoAgent type when available 
CrewAgentType = Any  # Replace with actual CrewAgent type when available

@dataclass
class pebble:
    """Main pebble class that provides a simplified interface to the protocol components."""
    
    def __init__(
        self,
        agent: Optional[Union[SmolAgentType, AgnoAgentType, CrewAgentType]] = None,
        debug_mode: bool = False,
    ):
        self.agent = agent
        self.debug_mode = debug_mode
        self.protocol = Protocol()
        self.coordinator = ProtocolCoordinator()
        self.agent_id = None
        
        # Register the agent if provided
        if self.agent is not None:
            self.agent_id = self.register_agent(self.agent)
    
    def register_agent(self, agent: Union[SmolAgentType, AgnoAgentType, CrewAgentType], agent_name: Optional[str] = None) -> str:
        """Register an agent with the coordinator.
        
        Args:
            agent: The agent to register
            agent_name: Optional name for the agent
            
        Returns:
            The agent_id assigned to the registered agent
        """
        agent_id = self.coordinator.register_agent(agent, agent_name)
        return agent_id
    
    async def send_message(self, content: Any, receiver_id: str, message_type: MessageType = MessageType.TEXT, metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """Send a message from the registered agent to another agent.
        
        Args:
            content: The content of the message
            receiver_id: The ID of the agent to receive the message
            message_type: The type of message to send
            metadata: Optional metadata to include with the message
            
        Returns:
            The response message if one is received
        """
        if self.agent_id is None:
            raise ValueError("No agent has been registered with this pebble instance")
            
        return await self.coordinator.send_message(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            metadata=metadata
        )
    
    async def broadcast_message(self, content: Any, message_type: MessageType = MessageType.TEXT, metadata: Optional[Dict[str, Any]] = None, exclude_ids: Optional[List[str]] = None) -> Dict[str, Optional[Message]]:
        """Broadcast a message from the registered agent to all other registered agents.
        
        Args:
            content: The content of the message
            message_type: The type of message to send
            metadata: Optional metadata to include with the message
            exclude_ids: Optional list of agent IDs to exclude from the broadcast
            
        Returns:
            Dictionary mapping agent IDs to their response messages
        """
        if self.agent_id is None:
            raise ValueError("No agent has been registered with this pebble instance")
            
        return await self.coordinator.broadcast_message(
            sender_id=self.agent_id,
            content=content,
            message_type=message_type,
            metadata=metadata,
            exclude_ids=exclude_ids
        )
    
    def get_registered_agents(self) -> List[str]:
        """Get a list of all registered agent IDs.
        
        Returns:
            List of agent IDs
        """
        return self.coordinator.get_registered_agents()
