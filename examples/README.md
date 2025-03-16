# Pebble Examples

This directory contains example code demonstrating how to use the Pebble protocol library to enable communication between different agent types.

## Example Files

### 1. `basic_protocol_usage.py`

Demonstrates the fundamental capabilities of the Pebble Protocol class:

- Creating, serializing, and deserializing messages
- Working with different message types
- Handling message metadata
- Adapting messages to different agent formats

**To adapt**: Replace the example message content and types with your specific use case.

### 2. `agent_communication.py`

Shows direct communication between agents using adapters:

- Creating agent instances of different types
- Setting up adapters for each agent type
- Sending messages between agents
- Handling structured command messages
- Converting messages to agent-specific formats

**To adapt**: 
1. Replace the example agent classes with your actual agent implementations
2. Update the agent configuration parameters to match your agent's requirements
3. Modify the message formats to match your specific communication needs

### 3. `coordinator_example.py`

Demonstrates using the ProtocolCoordinator to manage multiple agents:

- Registering agents with the coordinator
- Sending messages between agents via the coordinator
- Broadcasting messages to multiple agents
- Agent management (adding/removing agents)
- Error handling for coordinator operations

**To adapt**:
1. Replace the agent implementations with your actual agent classes
2. Adjust the agent initialization parameters for your specific use case
3. Customize message content and command structure for your application

### 4. `simple_workflow.py`

Provides a simplified workflow example that's easy to adapt as a starting point:

- Minimal agent implementations focused on the core functionality
- Step-by-step workflow with clear progression
- Basic result tracking between workflow stages
- Ideal starting point for developers new to multi-agent systems

**To adapt**:
1. Replace simplified agent implementations with your actual agents
2. Customize the workflow steps for your specific application
3. Expand the result tracking based on your application's requirements

### 5. `multi_agent_workflow.py`

Shows a practical and comprehensive multi-agent workflow example:

- Setting up multiple agents with different roles
- Coordinating multi-step tasks across agents
- Managing project state across different agent interactions
- Implementing a complete workflow with multiple phases

**To adapt**:
1. Replace mock agent implementations with real agent instances
2. Adjust the workflow steps to match your specific project requirements
3. Customize the project data structure for your application domain

## Running the Examples

To run any example:

```bash
# Install pebble first
pip install pebble

# Run an example
python examples/basic_protocol_usage.py
```

## Integration Tips

1. **Agent Implementations**: Replace the example agent implementations with your actual agent libraries
2. **Error Handling**: Wrap agent communication in try/except blocks to handle potential errors
3. **Async Support**: All examples use async/await - ensure your environment supports this
4. **Configuration**: Adjust agent configurations based on your specific model and parameter requirements
5. **Message Format**: Customize the message content structure to match your application's needs
