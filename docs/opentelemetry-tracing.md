# OpenTelemetry Tracing in Bindu

## Overview

Bindu implements comprehensive distributed tracing using OpenTelemetry to provide visibility across the entire task execution lifecycle: **TaskManager → Scheduler → Worker → Agent**.

## Architecture

### Trace Propagation Flow

```
1. API Request (TaskManager)
   └─ Span: "task_manager.{operation}"
      └─ Captures: request_id, task_id, context_id

2. Scheduler Dispatch
   └─ Captures current span via get_current_span()
   └─ Stores in _TaskOperation._current_span

3. Worker Execution
   └─ Restores span via use_span()
   └─ Span: "{operation} task"
      └─ Child Span: "agent.execute"
         └─ Captures: agent name, DID, execution time
```

## Key Components

### 1. TaskManager Tracing (`task_telemetry.py`)

**Decorator**: `@trace_task_operation(operation_name)`

**Features**:
- Creates root span for all task operations
- Records metrics (counters, histograms, up/down counters)
- Captures request parameters and results
- Handles success/error status

**Attributes**:
- `bindu.operation`: Operation name (e.g., "get_task", "send_message")
- `bindu.request_id`: JSON-RPC request ID
- `bindu.task_id`: Task UUID
- `bindu.context_id`: Context UUID
- `bindu.component`: "task_manager"
- `bindu.success`: Boolean success flag
- `bindu.error_type`: Exception class name (on error)
- `bindu.error_message`: Error description (on error)

**Metrics**:
- `bindu_tasks_total`: Counter of tasks processed
- `bindu_task_duration_seconds`: Histogram of task durations
- `bindu_active_tasks`: Up/down counter of active tasks
- `bindu_contexts_total`: Counter of contexts managed

### 2. Scheduler Span Propagation (`base.py`, `memory_scheduler.py`)

**Key Structure**:
```python
class _TaskOperation(TypedDict):
    operation: str              # "run", "cancel", "pause", "resume"
    params: dict                # Task parameters
    _current_span: Span         # ⭐ Preserves trace context
```

**How it works**:
1. Scheduler captures active span: `get_current_span()`
2. Stores span in `_TaskOperation._current_span`
3. Sends operation to worker queue
4. Worker restores span to continue trace

**Why it's needed**:
- Async boundaries break automatic context propagation
- Explicit span passing maintains trace continuity
- Enables distributed tracing across process boundaries

### 3. Worker Tracing (`base.py`)

**Span Restoration**:
```python
with use_span(task_operation["_current_span"]):
    with tracer.start_as_current_span(f"{operation} task"):
        await handler(params)
```

**Features**:
- Restores parent span from TaskManager
- Creates child span for worker operation
- Maintains trace hierarchy

### 4. Agent Execution Tracing (`manifest_worker.py`)

**New Enhancement**: Agent-level span with detailed metrics

**Span**: `"agent.execute"`

**Attributes**:
- `bindu.agent.name`: Agent name from manifest
- `bindu.agent.did`: Agent DID identifier
- `bindu.agent.message_count`: Number of messages in conversation
- `bindu.agent.execution_time`: Time spent in agent execution (seconds)
- `bindu.component`: "agent_execution"
- `bindu.agent.error_type`: Error class (on failure)
- `bindu.agent.error_message`: Error description (on failure)

**Span Events** (Timeline markers):
- `task.state_changed`: Emitted on every state transition
  - Attributes: `from_state`, `to_state`, `error` (if applicable)
  - States: working → input-required/auth-required/completed/failed

## Complete Trace Example

### Scenario: User sends a message that requires input

```
task_manager.send_message (250ms)
├─ Attributes:
│  ├─ bindu.operation: "send_message"
│  ├─ bindu.request_id: "req-123"
│  ├─ bindu.task_id: "task-456"
│  └─ bindu.context_id: "ctx-789"
│
└─ run task (220ms)
   ├─ Attributes:
   │  └─ logfire.tags: ["bindu"]
   │
   ├─ Events:
   │  └─ task.state_changed (t=10ms)
   │     └─ to_state: "working"
   │
   └─ agent.execute (200ms)
      ├─ Attributes:
      │  ├─ bindu.agent.name: "travel_agent"
      │  ├─ bindu.agent.did: "did:bindu:user:agent:uuid"
      │  ├─ bindu.agent.message_count: 3
      │  ├─ bindu.agent.execution_time: 0.200
      │  └─ bindu.component: "agent_execution"
      │
      └─ Events:
         └─ task.state_changed (t=200ms)
            ├─ from_state: "working"
            └─ to_state: "input-required"
```

## Observability Benefits

### 1. **Performance Analysis**
- See exactly where time is spent: TaskManager → Worker → Agent
- Identify slow operations and bottlenecks
- Track LLM latency separately from framework overhead

### 2. **Error Debugging**
- Full stack trace across async boundaries
- Error context preserved with span attributes
- Timeline of state transitions leading to failure

### 3. **State Transition Visibility**
- Span events show task lifecycle progression
- Identify where tasks get stuck (e.g., waiting for input)
- Track success/failure rates by state

### 4. **Metrics Correlation**
- Traces linked to metrics via shared attributes
- Analyze performance trends over time
- Alert on anomalies (high latency, error rates)

## Integration with Observability Tools

### Supported Backends
- **Logfire**: Native support (see `logfire.tags` attribute)
- **Jaeger**: Standard OpenTelemetry exporter
- **Zipkin**: Standard OpenTelemetry exporter
- **Grafana Tempo**: Standard OpenTelemetry exporter
- **Any OTLP-compatible backend**

### Configuration
Configure exporters in your observability setup:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Set up tracer provider
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

## Best Practices

### 1. **Consistent Naming**
- All attributes prefixed with `bindu.*`
- Span names follow pattern: `{component}.{operation}`
- Events use descriptive names: `task.state_changed`

### 2. **Attribute Guidelines**
- Use structured data (strings, numbers, booleans)
- Avoid high-cardinality values in metrics labels
- Include error context in error spans

### 3. **Sampling Strategy**
For high-volume production:
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

# Sample 10% of traces
sampler = ParentBasedTraceIdRatioBased(0.1)
```

### 4. **Span Events vs Attributes**
- **Attributes**: Static metadata (task_id, agent_name)
- **Events**: Timeline markers (state changes, checkpoints)

## Future Enhancements

### 1. **External Service Propagation**
Inject trace context into HTTP headers for external API calls:
```python
from opentelemetry.propagate import inject

headers = {}
inject(headers)  # Adds traceparent, tracestate
response = await http_client.get(url, headers=headers)
```

### 2. **Custom Agent Metrics**
Track LLM-specific metrics:
```python
agent_token_usage = meter.create_counter(
    "bindu_agent_tokens_total",
    description="LLM tokens consumed",
    unit="1"
)
```

### 3. **Distributed Tracing with Redis**
For multi-worker deployments, serialize span context:
```python
serializable_task = {
    "operation": "run",
    "params": {...},
    "span_id": str(span.get_span_context().span_id),
    "trace_id": str(span.get_span_context().trace_id),
}
```

## Summary

Bindu's OpenTelemetry implementation provides:
- ✅ **Complete trace coverage**: API → Scheduler → Worker → Agent
- ✅ **Async boundary handling**: Explicit span propagation via `_current_span`
- ✅ **Rich context**: Comprehensive attributes and events
- ✅ **Metrics integration**: Correlated counters and histograms
- ✅ **Production-ready**: Error handling, sampling support
- ✅ **Agent visibility**: Detailed execution metrics and timeline

This enables full observability for debugging, performance optimization, and production monitoring.
