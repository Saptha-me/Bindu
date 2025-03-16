# Pebble

Pebble is a communication protocol library that enables seamless interaction between different agent types (smolagent, agno, crew) in Python. It provides a standardized way for these agents to exchange messages and collaborate effectively.

## Features

- **Unified Protocol**: Standardized message format for agent communication
- **Multiple Agent Support**: Works with SmolAgent, AgnoAgent, and CrewAI Agent types
- **Flexible Adapters**: Easily extensible to support new agent types
- **Message Coordination**: Central coordinator for message routing between agents

## Installation

```bash
pip install pebble
```

Or if you prefer using uv:

```bash
uv pip install pebble
```

## Quick Start

### Basic Usage

```python
from pebble import Protocol, Message, MessageType, ProtocolCoordinator
from pebble import SmolAdapter, AgnoAdapter, CrewAdapter

# Create agents
from smolagents import CodeAgent
from agno.agent import Agent as AgnoAgent
from crewai import Agent as CrewAgent

# Initialize your agents
smol_agent = CodeAgent(...)
agno_agent = AgnoAgent(...)
crew_agent = CrewAgent(...)

# Create a coordinator
coordinator = ProtocolCoordinator()

# Register agents
smol_id = coordinator.register_agent(smol_agent, "smol-agent-1")
agno_id = coordinator.register_agent(agno_agent, "agno-agent-1")
crew_id = coordinator.register_agent(crew_agent, "crew-agent-1")

# Send a message from one agent to another
response = await coordinator.send_message(
    sender_id=smol_id,
    receiver_id=agno_id,
    content="What's the weather like today?",
    message_type=MessageType.TEXT
)

# Print the response
print(response.content if response else "No response")
```

### Direct Protocol Usage

```python
from pebble import Protocol, Message, MessageType, AgentType

# Create a protocol instance
protocol = Protocol()

# Create a message
message = protocol.create_message(
    message_type=MessageType.TEXT,
    sender="agent-1",
    content="Hello, this is a test message",
    receiver="agent-2"
)

# Serialize the message
serialized = protocol.serialize(message)

# Deserialize the message
deserialized = protocol.deserialize(serialized)

# Adapt for specific agent type
agno_format = protocol.adapt_for_agent_type(message, AgentType.AGNO)
```

## Components

### Protocol

The core component that handles message creation, serialization, and adaptation for different agent types.

### Message

Standardized message format with fields for sender, receiver, content, type, and metadata.

### Adapters

- **SmolAdapter**: Handles communication with SmolAgent instances
- **AgnoAdapter**: Handles communication with AgnoAgent instances
- **CrewAdapter**: Handles communication with CrewAI Agent instances

### ProtocolCoordinator

Manages agent registration and message routing between different agent types.

## License

MIT
