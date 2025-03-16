"""
Coordinator for managing communication between agents via the protocol.
"""
from typing import Any, Dict, List, Optional, Union

from agno.agent import Agent as AgnoAgent
from smolagents import CodeAgent as SmolAgent
from crewai import Agent as CrewAgent

from .protocol import Protocol, Message, MessageType, AgentType
from .adapters.smol_adapter import SmolAdapter
from .adapters.agno_adapter import AgnoAdapter 
from .adapters.crew_adapter import CrewAdapter


class ProtocolCoordinator:
    """
    Coordinator for agent communication via the Pebble protocol.
    
    This class manages the communication between different agent types,
    handling message routing and translation between agent-specific formats.
    """
    
    def __init__(self):
        """Initialize the protocol coordinator."""
        self.agents = {}
        self.protocol = Protocol()
    
    def register_agent(self, agent: Union[SmolAgent, AgnoAgent, CrewAgent], agent_id: Optional[str] = None) -> str:
        """
        Register an agent with the coordinator.
        
        Args:
            agent: The agent instance to register
            agent_id: Optional custom ID for the agent
            
        Returns:
            str: The registered agent's ID
        """
        # Create appropriate adapter for the agent type
        if isinstance(agent, SmolAgent):
            adapter = SmolAdapter(agent)
        elif isinstance(agent, AgnoAgent):
            adapter = AgnoAdapter(agent)
        elif isinstance(agent, CrewAgent):
            adapter = CrewAdapter(agent)
        else:
            raise ValueError(f"Unsupported agent type: {type(agent)}")
        
        # Use provided ID or get from adapter
        agent_id = agent_id or adapter.agent_id
        
        # Register the agent with its adapter
        self.agents[agent_id] = adapter
        
        return agent_id
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the coordinator.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            bool: True if the agent was unregistered, False otherwise
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    def get_registered_agents(self) -> List[str]:
        """
        Get a list of all registered agent IDs.
        
        Returns:
            List[str]: List of agent IDs
        """
        return list(self.agents.keys())
    
    async def send_message(self, 
                          sender_id: str, 
                          receiver_id: str, 
                          content: Any, 
                          message_type: MessageType = MessageType.TEXT,
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Send a message from one agent to another.
        
        Args:
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            content: Message content
            message_type: Type of message (default: TEXT)
            metadata: Additional message metadata (optional)
            
        Returns:
            Optional[Message]: Response message if any
        """
        if sender_id not in self.agents:
            raise ValueError(f"Sender agent not found: {sender_id}")
            
        if receiver_id not in self.agents:
            raise ValueError(f"Receiver agent not found: {receiver_id}")
        
        # Create the message
        message = Protocol.create_message(
            message_type=message_type,
            sender=sender_id,
            receiver=receiver_id, 
            content=content,
            metadata=metadata
        )
        
        # Get receiver's adapter and send the message
        receiver_adapter = self.agents[receiver_id]
        response = await receiver_adapter.send_message(message)
        
        if response:
            # Notify the sender of the response
            sender_adapter = self.agents[sender_id]
            await sender_adapter.receive_message(response)
            
        return response
        
    async def broadcast_message(self,
                              sender_id: str,
                              content: Any,
                              message_type: MessageType = MessageType.TEXT,
                              metadata: Optional[Dict[str, Any]] = None,
                              exclude_ids: Optional[List[str]] = None) -> Dict[str, Optional[Message]]:
        """
        Broadcast a message to all registered agents.
        
        Args:
            sender_id: ID of the sending agent
            content: Message content
            message_type: Type of message (default: TEXT)
            metadata: Additional message metadata (optional)
            exclude_ids: Agent IDs to exclude from broadcast (optional)
            
        Returns:
            Dict[str, Optional[Message]]: Mapping of agent IDs to their responses
        """
        if sender_id not in self.agents:
            raise ValueError(f"Sender agent not found: {sender_id}")
        
        exclude_ids = exclude_ids or []
        exclude_ids.append(sender_id)  # Don't send to self
        
        responses = {}
        
        # Send to all agents except excluded ones
        for agent_id, adapter in self.agents.items():
            if agent_id not in exclude_ids:
                message = Protocol.create_message(
                    message_type=message_type,
                    sender=sender_id,
                    receiver=agent_id,
                    content=content,
                    metadata=metadata
                )
                
                response = await adapter.send_message(message)
                responses[agent_id] = response
                
                if response:
                    # Notify the sender of each response
                    sender_adapter = self.agents[sender_id]
                    await sender_adapter.receive_message(response)
        
        return responses
