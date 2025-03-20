# Pebble Examples

This directory contains examples demonstrating how to deploy AI agents using the Pebble framework with a unified protocol for standardized communication.

## Example Files

### 1. `deploy_agno_agent.py`

Basic example of deploying an Agno agent with Pebble:

- Initializing an Agno agent with custom parameters
- Deploying the agent with the standard protocol
- Accessing the agent via API endpoints 

To run:
```bash
python examples/deploy_agno_agent.py
```

### 2. `deploy_agno_agent_with_auth.py`

Shows how to deploy an Agno agent with authentication:

- Setting up an Agno agent for customer support
- Configuring authentication parameters
- Securing API endpoints with API key authentication
- Using the AgnoAdapter for more control

To run:
```bash
python examples/deploy_agno_agent_with_auth.py
```

### 3. `deploy_crew_agent.py`

Demonstrates deploying a CrewAI agent:

- Creating a CrewAI agent with custom tools
- Deploying with the standard protocol
- Using a different port and configuration
- Examples of API interaction

To run:
```bash
python examples/deploy_crew_agent.py
```

### 4. `client_example.py`

Complete client example for interacting with deployed agents:

- Connecting to a deployed Pebble agent
- Fetching agent status information
- Sending messages to the agent
- Creating conversational sessions
- Handling tool calls in responses

To run:
```bash
python examples/client_example.py --url http://localhost:8000 --api-key <your-api-key>
```

## Protocol Features

The Pebble framework provides a standardized protocol for agent communication with these features:

1. **Unified API Interface**: Consistent API endpoints regardless of the underlying agent framework
2. **Authentication**: Secure token-based authentication for API access
3. **Session Management**: Track conversation history with session IDs
4. **Agent Status Tracking**: Standardized status reporting across agent types
5. **Tool Call Handling**: Consistent format for agent tool calls
6. **Framework Adaptation**: Automatic adaptation between different agent frameworks
7. **Metadata Support**: Extensible metadata for customization

## Using with Your Own Agents

To use the Pebble framework with your own agents:

1. **Select the appropriate adapter**: Use `AgnoAdapter` for Agno agents, `CrewAdapter` for CrewAI agents
2. **Configure deployment**: Use the `DeploymentConfig` class to customize your deployment
3. **Deploy with `pebblify.deploy()`**: Pass your agent and configuration to deploy

Example:
```python
from pebble import pebblify
from pebble.pebblify import DeploymentConfig

# Initialize your agent with its native framework
my_agent = YourAgentFramework(...)

# Configure deployment
config = DeploymentConfig(
    port=8000,
    require_auth=True
)

# Deploy
pebblify.deploy(my_agent, config)
```

## Integration Notes

1. **Agent Compatibility**: The framework automatically detects the agent type and applies the appropriate adapter
2. **Authentication**: API keys are generated on startup when authentication is enabled
3. **CORS**: Cross-origin resource sharing is enabled by default but can be configured
4. **Documentation**: Swagger API docs are available at `/docs` when enabled
5. **Tool Support**: Tools from both Agno and CrewAI are supported and exposed in a standardized format
