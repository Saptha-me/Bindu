# OpenTelemetry Tracing Configuration

## Configuration Methods

Bindu supports two ways to configure tracing:

1. **Agent Config File** (Recommended) - Set in your agent's JSON config
2. **Environment Variables** - Set as shell environment variables

**Priority**: Agent config parameters take precedence over environment variables.

## Agent Config (Recommended)

Configure tracing directly in your agent config file:

```json
{
  "name": "my-agent",
  "author": "user@example.com",
  "description": "My helpful agent",
  "telemetry": true,
  "oltp": {
    "endpoint": "http://localhost:4318/v1/traces",
    "service_name": "bindu-agent"
  }
}
```

**Benefits**:
- ✅ Configuration lives with your agent code
- ✅ Easy to version control
- ✅ No need to set environment variables
- ✅ Different configs for different agents

**Note**: The `oltp` section is only used when `telemetry: true`.

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP endpoint URL (e.g., `http://localhost:4318/v1/traces`) |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | - | Alternative traces-specific endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | - | Headers for authentication (e.g., `x-api-key=secret`) |

### Service Identification

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SERVICE_NAME` | `bindu-agent` | Service name in traces |
| `OTEL_SERVICE_VERSION` | `1.0.0` | Service version |
| `DEPLOYMENT_ENV` | `development` | Deployment environment (dev/staging/prod) |
| `OTEL_RESOURCE_ATTRIBUTES` | - | Additional attributes (comma-separated `key=value`) |

### Batch Processor Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_USE_BATCH_PROCESSOR` | `true` | Enable batch processing |
| `OTEL_BSP_MAX_QUEUE_SIZE` | `2048` | Maximum spans in queue |
| `OTEL_BSP_SCHEDULE_DELAY` | `5000` | Export delay in milliseconds |
| `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` | `512` | Maximum spans per batch |
| `OTEL_BSP_EXPORT_TIMEOUT` | `30000` | Export timeout in milliseconds |

## Configuration Precedence

When both agent config and environment variables are set:

```json
// agent_config.json
{
  "telemetry": true,
  "oltp": {
    "endpoint": "http://localhost:4318/v1/traces",
    "service_name": "my-agent"
  }
}
```

```bash
# These will be IGNORED because agent config takes precedence
export OTEL_EXPORTER_OTLP_ENDPOINT="http://other-host:4318/v1/traces"
export OTEL_SERVICE_NAME="other-service"
```

**Result**: Uses `http://localhost:4318/v1/traces` and `my-agent` from config.

## Configuration Examples

### Development (Agent Config)

Fast feedback for debugging:

```json
{
  "name": "my-agent-dev",
  "telemetry": true,
  "oltp": {
    "endpoint": "http://localhost:4318/v1/traces",
    "service_name": "bindu-agent-dev"
  }
}
```

Then set environment for batch tuning:

```bash
export DEPLOYMENT_ENV="development"
# Export immediately (no batching)
export OTEL_USE_BATCH_PROCESSOR="false"
```

**Result**: Spans appear in Jaeger immediately after request completes.

### Staging (Balanced)

Balance between latency and performance:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger-staging:4318/v1/traces"
export OTEL_SERVICE_NAME="bindu-agent"
export OTEL_SERVICE_VERSION="1.2.0"
export DEPLOYMENT_ENV="staging"

# Faster exports for testing
export OTEL_BSP_SCHEDULE_DELAY="2000"  # 2 seconds
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="256"
```

**Result**: Spans exported every 2 seconds or when 256 spans collected.

### Production (High Performance)

Optimized for high throughput:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN"
export OTEL_SERVICE_NAME="bindu-agent"
export OTEL_SERVICE_VERSION="2.0.0"
export DEPLOYMENT_ENV="production"
export OTEL_RESOURCE_ATTRIBUTES="team=ai-platform,region=us-west-2,cluster=prod-1"

# Larger batches, less frequent exports
export OTEL_BSP_MAX_QUEUE_SIZE="4096"
export OTEL_BSP_SCHEDULE_DELAY="10000"  # 10 seconds
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="1024"
```

**Result**: Maximum throughput, minimal overhead, spans exported every 10s or 1024 spans.

### High-Volume Production (With Sampling)

For extremely high traffic (future enhancement):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN"
export OTEL_SERVICE_NAME="bindu-agent"
export DEPLOYMENT_ENV="production"

# Sample 10% of traces
export OTEL_TRACE_SAMPLE_RATE="0.1"

# Large batches
export OTEL_BSP_MAX_QUEUE_SIZE="8192"
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="2048"
```

**Note**: Sampling requires code enhancement (see optimization guide).

## Backend-Specific Configuration

### Jaeger

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"
export OTEL_SERVICE_NAME="bindu-agent"
```

### OneUptime

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN"
export OTEL_SERVICE_NAME="bindu-agent"
```

### Honeycomb

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=YOUR_API_KEY"
export OTEL_SERVICE_NAME="bindu-agent"
```

### Grafana Tempo

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://tempo:4318/v1/traces"
export OTEL_SERVICE_NAME="bindu-agent"
```

### New Relic

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.nr-data.net:4318"
export OTEL_EXPORTER_OTLP_HEADERS="api-key=YOUR_LICENSE_KEY"
export OTEL_SERVICE_NAME="bindu-agent"
```

## Resource Attributes

Resource attributes help organize and filter traces:

### Standard Attributes

```bash
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=ai-agents,service.instance.id=agent-01"
```

### Custom Attributes

```bash
export OTEL_RESOURCE_ATTRIBUTES="team=platform,cost-center=engineering,owner=john@example.com"
```

### Multiple Attributes

```bash
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production,service.version=2.0.0,region=us-west-2,availability_zone=us-west-2a"
```

## Batch Processor Tuning Guide

### Understanding Parameters

**`max_queue_size`**: Buffer size for spans before blocking
- **Too low**: Application may block waiting for export
- **Too high**: High memory usage
- **Recommendation**: 2048 (default) for most cases

**`schedule_delay_millis`**: How often to export spans
- **Too low**: Frequent small exports (overhead)
- **Too high**: Delayed visibility in UI
- **Recommendation**: 
  - Dev: 1000-2000ms (fast feedback)
  - Prod: 5000-10000ms (efficiency)

**`max_export_batch_size`**: Maximum spans per export
- **Too low**: Many small exports
- **Too high**: Large payloads, potential timeouts
- **Recommendation**: 512 (default) for most cases

**`export_timeout_millis`**: Timeout for export operation
- **Too low**: Exports may fail on slow networks
- **Too high**: Application may hang on network issues
- **Recommendation**: 30000ms (30s) default is good

### Tuning for Your Workload

**Low Traffic** (< 10 req/min):
```bash
export OTEL_BSP_SCHEDULE_DELAY="2000"  # Export every 2s
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="100"
```

**Medium Traffic** (10-100 req/min):
```bash
# Use defaults
export OTEL_BSP_SCHEDULE_DELAY="5000"
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="512"
```

**High Traffic** (> 100 req/min):
```bash
export OTEL_BSP_MAX_QUEUE_SIZE="4096"
export OTEL_BSP_SCHEDULE_DELAY="10000"  # Export every 10s
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE="1024"
```

## Troubleshooting

### Spans Not Appearing

1. Check endpoint is set:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   ```

2. Check logs for export confirmation:
   ```
   [INFO] Successfully exported X span(s) to OTLP endpoint
   ```

3. If using batch processor, wait for schedule delay or generate enough spans

### High Memory Usage

Reduce queue size:
```bash
export OTEL_BSP_MAX_QUEUE_SIZE="1024"
```

### Delayed Trace Visibility

Reduce schedule delay:
```bash
export OTEL_BSP_SCHEDULE_DELAY="1000"  # 1 second
```

Or disable batching (dev only):
```bash
export OTEL_USE_BATCH_PROCESSOR="false"
```

### Export Failures

Check logs for errors:
```
[ERROR] Failed to export X span(s) to OTLP endpoint
```

Increase timeout:
```bash
export OTEL_BSP_EXPORT_TIMEOUT="60000"  # 60 seconds
```

## Best Practices

1. **Always set service name and version** for proper identification
2. **Use batch processing in production** for better performance
3. **Add resource attributes** for better filtering and organization
4. **Tune batch parameters** based on your traffic patterns
5. **Monitor export logs** to ensure traces are being sent
6. **Use different configurations** for dev/staging/prod environments
7. **Set deployment environment** to separate traces by environment

## Summary

The tracing system is highly configurable via environment variables:

✅ **Service identification** via `OTEL_SERVICE_NAME`, `OTEL_SERVICE_VERSION`  
✅ **Environment separation** via `DEPLOYMENT_ENV`  
✅ **Performance tuning** via batch processor parameters  
✅ **Custom metadata** via `OTEL_RESOURCE_ATTRIBUTES`  
✅ **Backend flexibility** via endpoint and headers configuration  

All configuration is done through environment variables—no code changes needed!
