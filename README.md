# Pebble

<div align="center">
  <h3>A universal communication protocol for AI agents</h3>
</div>

Pebble is a powerful communication protocol library that enables seamless interaction between different AI agent frameworks in Python. It provides a standardized way for agents from various frameworks (such as SmolagentAI, AgnoAI, and CrewAI) to exchange messages, share context, and collaborate effectively.

## ✨ Features

- **Universal Agent Protocol**: Standardized communication interface that works across agent frameworks
- **Multi-Framework Support**: Seamless integration with SmolagentAI, AgnoAI, CrewAI, and easily extensible to others
- **Cognitive Capabilities**: Enhanced agent interactions with cognitive functions (act, listen, see, think)
- **Persistent State Management**: Store and retrieve agent states across sessions
- **Model Context Protocol (MCP)**: Support for the MCP standard for LLM interaction
- **Flexible Message Routing**: Central coordinator for managing agent communication
- **Extensible Architecture**: Easily adapt new agent frameworks into the ecosystem

## 🚀 Installation

```bash
pip install pebble
```

Or if you prefer using uv:

```bash
uv pip install pebble
```

## 🏁 Quick Start

### Basic Agent Communication

```python
from pebble import ProtocolCoordinator
from pebble.adapters import SmolAdapter, AgnoAdapter, CrewAdapter
from pebble.schemas.models import MessageType

# Import agents from their respective frameworks
from smolagents import Agent as SmolAgent
from agno.agent import Agent as AgnoAgent
from crewai import Agent as CrewAgent

# Initialize your agents
smol_agent = SmolAgent(...)
agno_agent = AgnoAgent(...)
crew_agent = CrewAgent(...)

# Create a protocol coordinator
coordinator = ProtocolCoordinator()

# Register agents with the coordinator
smol_id = coordinator.register_agent(smol_agent, "smol-researcher")
agno_id = coordinator.register_agent(agno_agent, "agno-coder")
crew_id = coordinator.register_agent(crew_agent, "crew-reviewer")

# Send a message from one agent to another
response = await coordinator.send_message(
    sender_id=smol_id,
    receiver_id=agno_id,
    content="Here's the research data for the implementation.",
    message_type=MessageType.TEXT
)

# Print the response
print(response.content)
```

### Enhanced Cognitive Agents

```python
from pebble.adapters.agno_cognitive_adapter import AgnoCognitiveAdapter
from pebble.schemas.models import CognitiveRequest, StimulusType
from agno.agent import Agent as AgnoAgent

# Create an agent with the Agno framework
agent = AgnoAgent(
    name="Research Assistant",
    model="gpt-4o",
    description="A helpful research assistant that finds relevant information.",
    instructions=["Find accurate information", "Summarize findings clearly"]
)

# Wrap with cognitive capabilities
cognitive_agent = AgnoCognitiveAdapter(
    agent=agent,
    name="Research Assistant",
    cognitive_capabilities=["act", "listen", "think", "see"]
)

# Use cognitive capabilities
response = cognitive_agent.think(CognitiveRequest(
    session_id="session-123",
    content="How should I approach researching quantum computing trends?",
    stimulus_type=StimulusType.THOUGHT
))

print(f"Agent thought process: {response.content}")
```

### Model Context Protocol (MCP) Integration

```python
from pebble.mcp.client import MCPClientAdapter
from pebble.mcp.utils import create_mcp_client
from pebble.schemas.models import ActionRequest, MessageRole

# Create an MCP client
mcp_client = create_mcp_client(
    transport_type="stdio",
    name="Pebble MCP Client",
    capabilities=["resources", "tools", "prompts", "sampling"],
    metadata={"model": {"name": "claude-3-opus"}}
)

# Process an action
request = ActionRequest(
    agent_id=mcp_client.agent_id,
    session_id="session-456",
    message="What are the latest breakthroughs in AI?",
    role=MessageRole.USER
)

response = await mcp_client.process_action(request)
print(f"MCP Response: {response.message}")
```

## 🧩 Core Components

### Agent Protocol

The base protocol that standardizes agent communication, providing methods for action processing and status reporting.

```python
from pebble.core.protocol import AgentProtocol

# Create a custom agent adapter
class MyCustomAdapter(AgentProtocol):
    def process_action(self, request):
        # Custom implementation for your agent framework
        response = self.agent.execute(request.message)
        return ActionResponse(
            agent_id=self.agent_id,
            message=response,
            status=AgentStatus.COMPLETED
        )
```

### Cognitive Protocol

Extends the base protocol with cognitive capabilities inspired by human cognition models.

```python
from pebble.core.cognitive_protocol import CognitiveAgentProtocol

# Cognitive methods available:
# - act(): Take actions in the environment
# - listen(): Process verbal input
# - see(): Process visual information
# - think(): Internal reasoning and planning
```

### Framework Adapters

Built-in adapters for popular agent frameworks:

- **SmolAdapter**: For the Hugging Face SmolagentAI framework
- **AgnoAdapter**: For the AgnoAI framework
- **CrewAdapter**: For the CrewAI framework
- **AgnoCognitiveAdapter**: Adds cognitive capabilities to AgnoAI agents

### Protocol Coordinator

Centralized manager for agent registration and message routing.

```python
coordinator = ProtocolCoordinator()
agent_id = coordinator.register_agent(my_agent, "agent-name")
```

### Model Context Protocol (MCP)

Support for the Model Context Protocol standard for LLM interaction:

- **MCPServer**: Expose agents through the MCP interface
- **MCPClientAdapter**: Connect to external MCP servers
- **MCPCognitiveAdapter**: Add cognitive capabilities to MCP clients

## 🛠️ Advanced Usage

### Multi-framework Agent Collaboration

Pebble enables agents from different frameworks to work together seamlessly:

```python
# Set up a collaborative workflow between different agent types
researcher = SmolAdapter(smol_agent, name="Data Researcher")
analyst = AgnoAdapter(agno_agent, name="Data Analyst")
implementer = CrewAdapter(crew_agent, name="Solution Implementer")

# Register all agents
r_id = coordinator.register_agent(researcher)
a_id = coordinator.register_agent(analyst)
i_id = coordinator.register_agent(implementer)

# Create a workflow
await coordinator.send_message(sender_id=r_id, receiver_id=a_id, 
                              content="Here's the research data.")
await coordinator.send_message(sender_id=a_id, receiver_id=i_id, 
                              content="Here's my analysis and recommendations.")
```

### Persistent State Management

Store and retrieve cognitive states across sessions:

```python
from pebble.db.storage import PostgresStateProvider

# Initialize storage provider
storage = PostgresStateProvider(connection_string="postgresql://...")

# Use with cognitive agent
response = cognitive_agent.act(CognitiveRequest(
    session_id="persistent-session",
    content="Remember this information for later: The meeting is at 3 PM.",
    metadata={"storage_provider": storage}
))

# Later, in another session, the state will be automatically loaded
```

## 📖 Documentation

For more detailed documentation and examples, please visit the [Pebble Documentation](https://github.com/yourusername/pebble/wiki).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Analysis from Multiple Perspectives

### From an Industry Expert's Perspective:

Pebble addresses a critical gap in the current AI agent ecosystem: interoperability. As the proliferation of specialized agent frameworks continues, the need for standardized communication becomes paramount. Pebble's adapter-based architecture and protocol standards follow industry best practices for creating middleware solutions.

The implementation of the Model Context Protocol (MCP) integration shows foresight, as MCP is gaining adoption among major AI providers as a standard for LLM interaction. The cognitive capabilities layer adds significant value by providing a standardized approach to more sophisticated agent behaviors beyond simple request-response patterns.

### From a Data-Driven Researcher's Perspective:

Pebble's approach to standardizing agent communication aligns with empirical findings on multi-agent systems. The cognitive protocol's design with distinct capabilities (act, listen, see, think) mirrors cognitive science models of human information processing, which have proven effective in agent design.

The persistent state management capability is particularly important for longitudinal agent interactions, as research shows that contextual awareness significantly improves agent performance over time. The ability to store and retrieve agent states across sessions enables more coherent and consistent agent behavior.

### From a Contrarian Innovator's Perspective:

While Pebble offers a valuable abstraction layer, it's essential to acknowledge the trade-offs in adopting a middleware solution. Each additional layer introduces potential latency and complexity. Future iterations should consider:

1. Lightweight protocol options for resource-constrained environments
2. Benchmarking tools to measure the performance impact of the abstraction layer
3. Federation capabilities to allow agent communities to form and collaborate across organizational boundaries

Pebble's greatest strength might also be its challenge: abstracting away framework differences could potentially mask framework-specific optimizations. Maintaining the right balance between standardization and framework-specific capabilities will be crucial.
