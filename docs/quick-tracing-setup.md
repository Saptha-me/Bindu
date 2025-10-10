# Quick Tracing Setup Guide

## Problem: No Traces in Jaeger

If you see only Jaeger's internal traces (`/api/services`), your agent traces aren't being sent yet.

## Solution: 3 Steps

### 1. Start Jaeger

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

### 2. Set Environment Variables

**Before starting your agent**, export these:

```bash
# Point to Jaeger's OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"

# Service identification (recommended)
export OTEL_SERVICE_NAME="bindu-agent"
export OTEL_SERVICE_VERSION="1.0.0"
export DEPLOYMENT_ENV="development"  # or production, staging

# Optional: Additional resource attributes
export OTEL_RESOURCE_ATTRIBUTES="team=ai-platform,region=us-west"

# Batch processing (recommended for production)
export OTEL_USE_BATCH_PROCESSOR="true"

# Optional: Tune batch processor (defaults shown)
export OTEL_BSP_MAX_QUEUE_SIZE="2048"          # Max spans in queue
export OTEL_BSP_SCHEDULE_DELAY="5000"          # Export delay (ms)
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="512"    # Spans per batch
export OTEL_BSP_EXPORT_TIMEOUT="30000"         # Export timeout (ms)
```

### 3. Start Your Agent

```bash
python your_agent.py
```

## What Changed

We added automatic observability initialization to `BinduApplication`:

1. **Application Lifespan** (`applications.py:239-245`):
   - Calls `setup_observability()` on startup
   - Initializes OpenTelemetry tracer provider
   - Configures OTLP exporter

2. **Global Tracer Provider** (`openinference.py:184`):
   - Sets tracer provider globally via `trace.set_tracer_provider()`
   - All tracers now use the configured provider

3. **Agent Execution Spans** (`manifest_worker.py:132-158`):
   - Traces agent execution with timing
   - Captures agent DID, name, message count
   - Records errors with context

## Verify It's Working

### Check Logs

You should see:

```
[INFO] Initializing observability...
[INFO] Configured OTLP exporter endpoint=http://localhost:4318/v1/traces batch_mode=True has_headers=False
[INFO] Global tracer provider configured
```

### Check Jaeger UI

1. Open http://localhost:16686
2. Select service: `bindu-agent` (or your service name)
3. Click "Find Traces"
4. You should see traces like:
   - `task_manager.send_message`
   - `task_manager.get_task`
   - `run task`
   - `agent.execute`

### Example Trace

```
task_manager.send_message (250ms)
├─ bindu.operation: "send_message"
├─ bindu.request_id: "req-123"
├─ bindu.task_id: "task-456"
└─ run task (220ms)
   └─ agent.execute (200ms)
      ├─ bindu.agent.name: "my-agent"
      ├─ bindu.agent.did: "did:bindu:user:agent:uuid"
      ├─ bindu.agent.execution_time: 0.200
      └─ Events:
         └─ task.state_changed
            ├─ from_state: "working"
            └─ to_state: "completed"
```

## Troubleshooting

### No Traces Appearing

1. **Check environment variables**:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   ```

2. **Check Jaeger is running**:
   ```bash
   docker ps | grep jaeger
   curl http://localhost:16686
   ```

3. **Check agent logs** for observability initialization

4. **Test OTLP endpoint**:
   ```bash
   curl -X POST http://localhost:4318/v1/traces \
     -H "Content-Type: application/json" \
     -d '{"resourceSpans":[]}'
   ```

### Traces Delayed

- BatchSpanProcessor batches spans before sending (default: 5s delay)
- Set `OTEL_USE_BATCH_PROCESSOR="false"` for immediate sending (dev only)

### Wrong Service Name

- Set `OTEL_SERVICE_NAME` environment variable before starting agent
- Default service name comes from OpenTelemetry SDK

## Alternative: Console Output

To see traces in console instead of Jaeger:

```bash
# Don't set OTEL_EXPORTER_OTLP_ENDPOINT
unset OTEL_EXPORTER_OTLP_ENDPOINT

# Start agent - traces will print to console
python your_agent.py
```

## Next Steps

- See `docs/jaeger-setup.md` for advanced Jaeger configuration
- See `docs/oneuptime-setup.md` for complete observability platform
- See `docs/opentelemetry-tracing.md` for architecture details
