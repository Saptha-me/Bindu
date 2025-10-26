# Handlers Package

This package contains all RPC request handlers for the Bindu server, organized by functionality.

## Structure

```
handlers/
├── __init__.py           # Package exports
├── message_handlers.py   # Message sending and streaming
├── task_handlers.py      # Task operations
└── context_handlers.py   # Context management
```

## Components

### MessageHandlers

Handles message-related RPC requests.

**Methods:**
- `send_message()` - Send a message using the A2A protocol
- `stream_message()` - Stream messages using Server-Sent Events (SSE)

**Dependencies:**
- Scheduler (for task execution)
- Storage (for task persistence)
- Manifest (for agent execution)
- Workers (for message history)

**Usage:**
```python
from bindu.server.handlers import MessageHandlers

message_handlers = MessageHandlers(
    scheduler=scheduler,
    storage=storage,
    manifest=manifest,
    workers=workers,
    context_id_parser=parse_context_id
)

response = await message_handlers.send_message(request)
```

### TaskHandlers

Handles task-related RPC requests.

**Methods:**
- `get_task()` - Retrieve a specific task
- `list_tasks()` - List all tasks
- `cancel_task()` - Cancel a running task
- `task_feedback()` - Submit feedback for a completed task

**Dependencies:**
- Scheduler (for task cancellation)
- Storage (for task retrieval)
- Error response creator (for standardized errors)

**Usage:**
```python
from bindu.server.handlers import TaskHandlers

task_handlers = TaskHandlers(
    scheduler=scheduler,
    storage=storage,
    error_response_creator=create_error_response
)

response = await task_handlers.get_task(request)
```

### ContextHandlers

Handles context-related RPC requests.

**Methods:**
- `list_contexts()` - List all contexts
- `clear_context()` - Clear a context and its associated tasks

**Dependencies:**
- Storage (for context operations)
- Error response creator (for standardized errors)

**Usage:**
```python
from bindu.server.handlers import ContextHandlers

context_handlers = ContextHandlers(
    storage=storage,
    error_response_creator=create_error_response
)

response = await context_handlers.list_contexts(request)
```

## Design Principles

### 1. Single Responsibility
Each handler class focuses on one type of operation:
- MessageHandlers → Message operations
- TaskHandlers → Task operations
- ContextHandlers → Context operations

### 2. Dependency Injection
All dependencies are injected through the constructor, making handlers:
- Easy to test
- Flexible to configure
- Clear about their requirements

### 3. Type Safety
All handlers use:
- Type hints for all parameters and return values
- Protocol types from `bindu.common.protocol.types`
- TYPE_CHECKING for circular import prevention

### 4. Telemetry Integration
Handlers use decorators for observability:
- `@trace_task_operation` - Traces task operations
- `@trace_context_operation` - Traces context operations
- `@track_active_task` - Tracks active task metrics

## Error Handling

All handlers use a standardized error response creator that:
- Returns JSON-RPC compliant error responses
- Uses protocol-defined error types (TaskNotFoundError, etc.)
- Provides clear, actionable error messages

## Testing

Each handler can be tested independently:

```python
# Test MessageHandlers
message_handlers = MessageHandlers(
    scheduler=mock_scheduler,
    storage=mock_storage,
    manifest=mock_manifest,
    workers=[],
    context_id_parser=lambda x: uuid.uuid4()
)

response = await message_handlers.send_message(test_request)
assert response["result"]["id"] is not None
```

## Future Enhancements

Potential additions to this package:
- **AgentHandlers** - Agent discovery and management
- **SkillHandlers** - Skill registration and execution
- **AuthHandlers** - Authentication and authorization
- **MetricsHandlers** - Metrics and analytics
