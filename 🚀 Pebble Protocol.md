The agent-to-agent communication protocol provides a **secure**, **lightweight**, and **expressive** framework enabling autonomous AI agents to collaborate effectively. Powered by **JSON-RPC 2.0** over **mutual TLS (mTLS)**, agents leverage structured tasks, dynamic personas, seamless memory integration, and sophisticated conversational actions.

## Message Envelope (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "MethodName",
  "source_agent_id": "agent-uuid-sender",
  "destination_agent_id": "agent-uuid-receiver",
  "timestamp": "2025-04-17T11:00:00Z",
  "params": {
    /* method-specific parameters */
  }
}
```

## ** Context Management (1 Protocol)

Enable agents to share and manage context, ensuring clear and context-aware interactions:

 **Context** - A unified protocol for managing context (add, update, delete) in the agent's memory. The operation is specified in the `operation` parameter.

### Add Context Operation

```json
{
  "jsonrpc": "2.0",
  "id": "context-001",
  "method": "Context",
  "source_agent_id": "agent-uuid-sender",
  "destination_agent_id": "agent-uuid-receiver",
  "timestamp": "2025-04-17T11:01:00Z",
  "params": {
    "operation": "add",
    "key": "FoodAllergies",
    "value": "Shrimp",
    "metadata": {
      "priority": "high"
    }
  }
}
```

### Update Context Operation

```json
{
  "jsonrpc": "2.0",
  "id": "context-002",
  "method": "Context",
  "source_agent_id": "agent-uuid-sender",
  "destination_agent_id": "agent-uuid-receiver",
  "timestamp": "2025-04-17T11:01:00Z",
  "params": {
    "operation": "update",
    "key": "FoodAllergies",
    "value": "Shellfish",
    "metadata": {
      "priority": "high"
    }
  }
}
```

### Delete Context Operation

```json
{
  "jsonrpc": "2.0",
  "id": "context-003",
  "method": "Context",
  "source_agent_id": "agent-uuid-sender",
  "destination_agent_id": "agent-uuid-receiver",
  "timestamp": "2025-04-17T11:01:00Z",
  "params": {
    "operation": "delete",
    "key": "FoodAllergies"
  }
}
```

### TaskAdd Operation
