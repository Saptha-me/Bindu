# Jaeger Setup for Bindu Tracing

## Quick Start

### 1. Start Jaeger

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

**Ports**:
- `16686`: Jaeger UI (web interface)
- `4317`: OTLP gRPC receiver
- `4318`: OTLP HTTP receiver

### 2. Configure Bindu

```bash
# HTTP endpoint (recommended for simplicity)
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"

# OR gRPC endpoint (more efficient)
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4317"

# Optional: Enable batch processing for better performance (default: true)
export OTEL_USE_BATCH_PROCESSOR="true"
```

### 3. Run Your Agent

```bash
python your_agent.py
```

### 4. View Traces

Open http://localhost:16686 in your browser

## What You'll See

### Service View
- **Service Name**: Your agent service
- **Operations**: All traced operations
  - `task_manager.send_message`
  - `task_manager.get_task`
  - `task_manager.cancel_task`
  - etc.

### Trace View
Complete request flow with timing:

```
task_manager.send_message (250ms)
└─ run task (220ms)
   └─ agent.execute (200ms)
```

### Span Details

**Attributes** (Tags in Jaeger):
- `bindu.operation`: Operation name
- `bindu.request_id`: Request identifier
- `bindu.task_id`: Task UUID
- `bindu.context_id`: Context UUID
- `bindu.agent.name`: Agent name
- `bindu.agent.did`: Agent DID
- `bindu.agent.execution_time`: Agent execution duration
- `bindu.component`: Component type

**Events** (Logs in Jaeger):
- `task.state_changed`: State transition events
  - `from_state`: Previous state
  - `to_state`: New state
  - `error`: Error message (if failed)

### Search & Filter

**By Service**:
```
Service: bindu-agent
```

**By Operation**:
```
Operation: task_manager.send_message
```

**By Tags**:
```
bindu.task_id = "550e8400-e29b-41d4-a716-446655440000"
bindu.agent.name = "travel_agent"
```

**By Duration**:
```
Min Duration: 100ms
Max Duration: 5s
```

**By Status**:
```
Tags: error=true
```

## Jaeger UI Features

### 1. **Trace Timeline**
- Visual representation of span hierarchy
- Color-coded by service
- Shows parallel vs sequential execution
- Hover for span details

### 2. **Trace Comparison**
- Compare multiple traces side-by-side
- Identify performance regressions
- Spot anomalies

### 3. **Service Dependencies**
- Visualize service interactions
- Identify bottlenecks
- Understand system architecture

### 4. **Statistics**
- Latency percentiles (p50, p95, p99)
- Error rates
- Request volume
- Operation distribution

## Production Deployment

### Using Docker Compose

```yaml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    depends_on:
      - elasticsearch
  
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - esdata:/usr/share/elasticsearch/data

volumes:
  esdata:
```

### Using Kubernetes

```yaml
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  ports:
    - name: ui
      port: 16686
    - name: otlp-grpc
      port: 4317
    - name: otlp-http
      port: 4318
  selector:
    app: jaeger
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        env:
        - name: COLLECTOR_OTLP_ENABLED
          value: "true"
        ports:
        - containerPort: 16686
        - containerPort: 4317
        - containerPort: 4318
```

### Environment Variables for Bindu

```bash
# Production endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4318/v1/traces"

# Enable batch processing (reduces overhead)
export OTEL_USE_BATCH_PROCESSOR="true"

# Optional: Set service name
export OTEL_SERVICE_NAME="bindu-agent-production"

# Optional: Set resource attributes
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production,service.version=1.0.0"
```

## Performance Tuning

### Batch Processor Configuration

The `BatchSpanProcessor` batches spans before sending to reduce overhead:

**Default Settings**:
- Max queue size: 2048 spans
- Max batch size: 512 spans
- Export timeout: 30s
- Schedule delay: 5s

**Custom Configuration** (requires code change):

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint),
    max_queue_size=4096,
    max_export_batch_size=1024,
    export_timeout_millis=30000,
    schedule_delay_millis=2000
)
```

### Sampling

For high-volume production, use sampling to reduce overhead:

```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

# Sample 10% of traces
sampler = ParentBasedTraceIdRatioBased(0.1)
tracer_provider = TracerProvider(sampler=sampler)
```

## Troubleshooting

### Traces Not Appearing

1. **Check Jaeger is running**:
   ```bash
   docker ps | grep jaeger
   ```

2. **Verify endpoint configuration**:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   ```

3. **Check Bindu logs**:
   ```
   Configured OTLP exporter endpoint=http://localhost:4318/v1/traces batch_mode=True
   ```

4. **Test connectivity**:
   ```bash
   curl http://localhost:4318/v1/traces
   ```

### Slow Performance

1. **Enable batch processing**:
   ```bash
   export OTEL_USE_BATCH_PROCESSOR="true"
   ```

2. **Increase batch size** (code change required)

3. **Use sampling** for high-volume scenarios

### Missing Spans

1. **Check span processor type**: BatchSpanProcessor may delay spans
2. **Verify tracer provider is set globally**
3. **Ensure all components use same tracer provider**

## Alternative Backends

While this guide focuses on Jaeger, Bindu supports any OTLP-compatible backend:

### Grafana Tempo
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://tempo:4318/v1/traces"
```

### Zipkin
```bash
# Requires Zipkin exporter instead of OTLP
# Modify openinference.py to use ZipkinExporter
```

### SigNoz
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://signoz:4318/v1/traces"
```

### Honeycomb
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=YOUR_API_KEY"
```

## Summary

Jaeger provides:
- ✅ **Full compatibility** with Bindu's OpenTelemetry implementation
- ✅ **Rich UI** for trace visualization and analysis
- ✅ **Production-ready** with Elasticsearch/Cassandra backends
- ✅ **Easy setup** via Docker or Kubernetes
- ✅ **Standard OTLP** protocol support

Your traces will show:
- Complete request flows (TaskManager → Scheduler → Worker → Agent)
- Detailed timing for each component
- State transitions via span events
- Error context and stack traces
- Agent-specific metrics (DID, execution time, message count)

**Next Steps**: Start Jaeger, set the environment variable, and watch your traces flow in! 🚀
