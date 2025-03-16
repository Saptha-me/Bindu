#!/usr/bin/env python
"""
Agent Type Usage Example

This example demonstrates how to use the centralized AgentType constants
throughout your code for consistent agent type identification.
"""

from pebble.constants import AgentType
from pebble.protocol.protocol import Protocol, Message, MessageType

def demonstrate_agent_types():
    """Demonstrate the use of AgentType constants."""
    print("Available Agent Types:")
    for agent_type in AgentType:
        print(f"- {agent_type.name}: {agent_type.value}")
    
    print("\nCreating messages for different agent types:")
    
    # Create protocol instance
    protocol = Protocol()
    
    # Create messages for different agent types
    for agent_type in AgentType:
        message = protocol.create_message(
            message_type=MessageType.TEXT,
            sender=f"example_{agent_type.value}_sender",
            content=f"This is a message from an {agent_type.value} agent",
            metadata={"agent_type": agent_type.value}
        )
        
        # Serialize the message
        serialized = protocol.serialize(message)
        print(f"\nMessage for {agent_type.name}:")
        print(f"Serialized: {serialized[:60]}...")
        
        # Adapt for different agent type
        adapted = protocol.adapt_for_agent_type(message, agent_type)
        print(f"Adapted for {agent_type.name}: {adapted}")

if __name__ == "__main__":
    demonstrate_agent_types()
