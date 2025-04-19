# Pebble

<h1 align="center">Agent-to-Agent Communication Made Simple 🪨</h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/YOUR_DISCORD)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.pebbling.ai)

🪨 Pebble is the easiest way to enable seamless, secure communication between autonomous AI agents.

💡 Built on **JSON-RPC 2.0** over **mutual TLS (mTLS)**, Pebble provides a lightweight yet powerful protocol framework for the next generation of collaborative AI systems.

## Quick Start

With pip (Python>=3.12):

```bash
pip install pebble
```

Set up your agent communication server:

```python
from pebble import PebbleServer
import asyncio

async def main():
    # Create a Pebble server
    server = PebbleServer()
    
    # Start the server
    await server.start()
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Gracefully shut down the server
        await server.stop()

asyncio.run(main())
```

Connect an agent to another agent:

```python
from pebble import Agent
import asyncio

async def main():
    # Create a Pebble agent
    agent = Agent(
        agent_id="agent-001",
        name="Assistant Agent",
        server_url="https://localhost:8000",
    )
    
    # Add context to another agent
    await agent.add_context(
        destination_agent_id="agent-002",
        key="UserPreference",
        value="Dark mode",
        metadata={"priority": "medium"}
    )
    
    # Send a message to another agent
    await agent.send_message(
        destination_agent_id="agent-002",
        content="Hello from Agent 001!",
        message_type="greeting"
    )

asyncio.run(main())
```

## Features

### Secure by Design

- **Mutual TLS (mTLS)** for encrypted agent-to-agent communication
- **JSON-RPC 2.0** for lightweight, structured message exchange
- **Authentication** built-in for agent identity verification

### Seamless Integration

- **Agno Compatibility** - Easily connect with Agno agents through our adapter
- **Cognitive Capabilities** - Support for vision, audio, and other cognitive functions
- **Media Handling** - Process images and videos with built-in adapters

### Powerful Context Management

- **Dynamic Context** - Add, update, or delete context between agents
- **Memory Integration** - Preserve important context across agent interactions
- **Structured Protocols** - Clear, standardized methods for complex interactions

## Example Use Cases

- **Customer Service Handoff** - Transfer context between specialized support agents
- **Multi-Agent Collaboration** - Enable teams of agents to work together on complex tasks
- **Cross-Platform Integration** - Connect agents running on different platforms or frameworks

## Vision

Pebble aims to be the universal protocol for agent-to-agent communication. Our roadmap includes:

- **Extended Protocol Support** - Additional methods for specialized agent interactions
- **Distributed Systems** - Scale to thousands of communicating agents
- **Cross-Framework Interoperability** - Connect agents built with different AI frameworks
- **Enterprise-Grade Security** - Advanced authentication and permission models

## Contributing

We welcome contributions from the community! Check out our [contributing guide](CONTRIBUTING.md) to get started.

### Local Setup

```bash
# Clone the repository
git clone https://github.com/Pebbling-ai/pebble.git
cd pebble

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

Pebble is released under the [MIT License](LICENSE).