#!/usr/bin/env python
"""
Basic Protocol Usage Example

This example demonstrates the basic usage of the pebble Protocol class
for creating, serializing, and deserializing messages.
"""

import json
from datetime import datetime

# Import pebble protocol components
from pebble import Protocol, MessageType, AgentType


def main():
    print("=== Pebble Basic Protocol Usage Example ===\n")
    
    # Create a Protocol instance
    protocol = Protocol()
    
    # Create a message
    message = protocol.create_message(
        message_type=MessageType.TEXT,
        sender="agent-1",
        content="Hello, this is a test message!",
        receiver="agent-2",
        metadata={"priority": "high", "category": "greeting"}
    )
    
    print(f"Created message: ID={message.id}, Type={message.type}")
    print(f"From: {message.sender} -> To: {message.receiver}")
    print(f"Content: {message.content}")
    print(f"Metadata: {message.metadata}")
    print(f"Timestamp: {message.timestamp}")
    print()
    
    # Serialize the message to JSON
    serialized = protocol.serialize(message)
    print(f"Serialized message:\n{serialized}")
    print()
    
    # Deserialize back to a message object
    deserialized = protocol.deserialize(serialized)
    print(f"Deserialized message: ID={deserialized.id}, Type={deserialized.type}")
    print(f"Content: {deserialized.content}")
    print()
    
    # Adapt the message for different agent types
    print("=== Message format for different agent types ===")
    
    # For SmolAgent
    smol_format = protocol.adapt_for_agent_type(message, AgentType.SMOL)
    print(f"SmolAgent format: {json.dumps(smol_format, indent=2)}")
    print()
    
    # For AgnoAgent
    agno_format = protocol.adapt_for_agent_type(message, AgentType.AGNO)
    print(f"AgnoAgent format: {json.dumps(agno_format, indent=2)}")
    print()
    
    # For CrewAgent
    crew_format = protocol.adapt_for_agent_type(message, AgentType.CREW)
    print(f"CrewAgent format: {json.dumps(crew_format, indent=2)}")
    

if __name__ == "__main__":
    main()
