# OneUptime Setup for Bindu Observability

## Overview

OneUptime is a comprehensive open-source observability platform that provides:
- **Distributed Tracing** (like Jaeger)
- **Metrics & Dashboards** (like Prometheus + Grafana)
- **Log Management** (like Loki)
- **Application Performance Monitoring** (like New Relic/DataDog)
- **Uptime Monitoring** (like Pingdom)
- **Incident Management** (like PagerDuty)
- **Status Pages** (like StatusPage.io)

All in one platform with native OpenTelemetry support!

## Quick Start (OneUptime Cloud)

### 1. Create Account

Sign up at https://oneuptime.com (free tier available)

### 2. Create Telemetry Ingestion Token

1. After creating a project, click **"More"** → **"Project Settings"**
2. Navigate to **"Telemetry Ingestion Key"**
3. Click **"Create Ingestion Key"**
4. Click **"View"** to see your token

### 3. Configure Bindu

```bash
# Set OneUptime endpoint and token
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN_HERE"
export OTEL_SERVICE_NAME="bindu-agent"

# Optional: Enable batch processing for better performance
export OTEL_USE_BATCH_PROCESSOR="true"
```

### 4. Run Your Agent

```bash
python your_agent.py
```

### 5. View Telemetry

Navigate to your OneUptime project dashboard to see:
- **Traces**: Complete request flows
- **Metrics**: Task counts, durations, error rates
- **Logs**: Structured application logs
- **APM**: Performance insights

## Self-Hosted OneUptime

### Docker Compose (Development)

```bash
# Clone repository
git clone https://github.com/OneUptime/oneuptime.git
cd oneuptime

# Start OneUptime
docker-compose up -d

# Wait for services to start (may take a few minutes)
docker-compose logs -f
```

**Access**:
- Dashboard: http://localhost:3002
- OTLP Endpoint: http://localhost:3002/otlp

**Configure Bindu**:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:3002/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN"
export OTEL_SERVICE_NAME="bindu-agent"
```

### Kubernetes (Production)

```bash
# Add Helm repository
helm repo add oneuptime https://helm-chart.oneuptime.com
helm repo update

# Install OneUptime
helm install oneuptime oneuptime/oneuptime \
  --namespace oneuptime \
  --create-namespace

# Get the OTLP endpoint
kubectl get svc -n oneuptime oneuptime-otel-collector
```

**Configure Bindu**:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://oneuptime-otel-collector.oneuptime.svc.cluster.local:4318"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=YOUR_TOKEN"
export OTEL_SERVICE_NAME="bindu-agent"
```

## What You'll See in OneUptime

### 1. Distributed Traces

**Complete Task Flows**:
```
task_manager.send_message (250ms)
├─ Attributes:
│  ├─ bindu.operation: "send_message"
│  ├─ bindu.request_id: "req-123"
│  ├─ bindu.task_id: "task-456"
│  └─ bindu.context_id: "ctx-789"
│
└─ run task (220ms)
   └─ agent.execute (200ms)
      ├─ Attributes:
      │  ├─ bindu.agent.name: "travel_agent"
      │  ├─ bindu.agent.did: "did:bindu:user:agent:uuid"
      │  ├─ bindu.agent.execution_time: 0.200
      │  └─ bindu.component: "agent_execution"
      │
      └─ Events:
         └─ task.state_changed
            ├─ from_state: "working"
            └─ to_state: "input-required"
```

### 2. Metrics Dashboard

**Automatic Metrics** (from your code):
- `bindu_tasks_total`: Total tasks processed
- `bindu_task_duration_seconds`: Task execution time
- `bindu_active_tasks`: Currently active tasks
- `bindu_contexts_total`: Total contexts created

**Custom Dashboards**:
- Task completion rate over time
- Average agent execution time
- Error rate by operation
- Active tasks gauge

### 3. Application Performance Monitoring

**Agent Performance**:
- Identify slow agents by DID
- Track execution time trends
- Compare agent performance
- Detect anomalies

**Task Analytics**:
- Success/failure rates
- State transition patterns
- Average time in each state
- Bottleneck identification

### 4. Log Management

**Structured Logs** (if you configure log export):
- Correlated with traces automatically
- Filter by task_id, context_id, agent_name
- Full-text search
- Log aggregation

### 5. Uptime Monitoring

**Monitor Your Agents**:
- HTTP endpoint checks
- API availability monitoring
- Response time tracking
- Multi-region probes

### 6. Alerting & Incidents

**Create Alerts**:
- Task failure rate > 5%
- Agent execution time > 10s
- Error rate spike
- Service downtime

**Incident Management**:
- Auto-create incidents from alerts
- Assign to on-call team
- Track resolution time
- Post-mortem templates

### 7. Status Page

**Public Status Page**:
- Show agent availability
- Display current incidents
- Historical uptime stats
- Subscribe to updates

## Configuration Examples

### Basic Setup

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=abc123"
export OTEL_SERVICE_NAME="bindu-agent"
```

### With Resource Attributes

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=abc123"
export OTEL_SERVICE_NAME="bindu-agent"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production,service.version=1.0.0,service.namespace=ai-agents"
```

### Multiple Environments

**Development**:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:3002/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=dev-token"
export OTEL_SERVICE_NAME="bindu-agent-dev"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=development"
```

**Production**:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://oneuptime.com/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="x-oneuptime-token=prod-token"
export OTEL_SERVICE_NAME="bindu-agent-prod"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production"
```

## Using OpenTelemetry Collector (Advanced)

For more control, use the OpenTelemetry Collector as a proxy:

### Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024

  resource:
    attributes:
      - key: service.namespace
        value: bindu
        action: insert

exporters:
  otlphttp:
    endpoint: "https://oneuptime.com/otlp"
    encoding: json
    headers:
      "Content-Type": "application/json"
      "x-oneuptime-token": "YOUR_TOKEN_HERE"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [otlphttp]

    metrics:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [otlphttp]

    logs:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [otlphttp]
```

### Run Collector

```bash
# Docker
docker run -d \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  -p 4317:4317 \
  -p 4318:4318 \
  otel/opentelemetry-collector:latest \
  --config=/etc/otel-collector-config.yaml

# Configure Bindu to use collector
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
```

**Benefits**:
- Centralized configuration
- Data preprocessing
- Multiple backend support
- Sampling and filtering
- Cost optimization

## Comparison: OneUptime vs Jaeger

| Feature | Jaeger | OneUptime |
|---------|--------|-----------|
| **Traces** | ✅ Excellent | ✅ Excellent |
| **Metrics** | ❌ No | ✅ Yes |
| **Logs** | ❌ No | ✅ Yes |
| **APM** | ❌ No | ✅ Yes |
| **Dashboards** | ⚠️ Basic | ✅ Advanced |
| **Alerting** | ❌ No | ✅ Yes |
| **Uptime Monitoring** | ❌ No | ✅ Yes |
| **Incident Management** | ❌ No | ✅ Yes |
| **Status Pages** | ❌ No | ✅ Yes |
| **On-Call Scheduling** | ❌ No | ✅ Yes |
| **Setup Complexity** | ⭐ Simple | ⭐⭐ Moderate |
| **Resource Usage** | ⭐ Light | ⭐⭐⭐ Heavy |
| **Open Source** | ✅ Yes | ✅ Yes |
| **Cloud Hosted** | ❌ No | ✅ Yes |

**Recommendation**:
- **Use Jaeger** if you only need distributed tracing
- **Use OneUptime** if you want a complete observability platform

## Troubleshooting

### Traces Not Appearing

1. **Verify token**:
   ```bash
   echo $OTEL_EXPORTER_OTLP_HEADERS
   ```

2. **Check endpoint**:
   ```bash
   curl -X POST https://oneuptime.com/otlp/v1/traces \
     -H "x-oneuptime-token: YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"resourceSpans":[]}'
   ```

3. **Check Bindu logs**:
   ```
   Configured OTLP exporter endpoint=https://oneuptime.com/otlp batch_mode=True has_headers=True
   ```

### Authentication Errors

**Error**: `401 Unauthorized`

**Solution**: Verify your token is correct and active in OneUptime project settings.

### Slow Performance

1. **Enable batch processing**:
   ```bash
   export OTEL_USE_BATCH_PROCESSOR="true"
   ```

2. **Use OpenTelemetry Collector** as a proxy to reduce direct connections

3. **Implement sampling** for high-volume scenarios

### Missing Attributes

**Issue**: Some `bindu.*` attributes not showing

**Solution**: Ensure you're using the latest version of Bindu with agent execution spans.

## Best Practices

### 1. Use Resource Attributes

```bash
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production,service.version=1.0.0,team=ai-platform"
```

### 2. Separate Environments

Use different tokens for dev/staging/prod to isolate telemetry data.

### 3. Set Service Name

```bash
export OTEL_SERVICE_NAME="bindu-agent-production"
```

### 4. Enable Batch Processing

```bash
export OTEL_USE_BATCH_PROCESSOR="true"
```

### 5. Monitor Costs

OneUptime Cloud has usage limits. Monitor your:
- Trace volume
- Metric cardinality
- Log volume

## Additional Resources

- **OneUptime Docs**: https://oneuptime.com/docs
- **GitHub**: https://github.com/OneUptime/oneuptime
- **OpenTelemetry Guide**: https://oneuptime.com/blog/post/2025-08-27-traces-and-spans-in-opentelemetry/view
- **Slack Community**: https://join.slack.com/t/oneuptimesupport/shared_invite/zt-2pz5p1uhe-Fpmc7bv5ZE5xRMe7qJnwmA

## Summary

OneUptime provides a **complete observability solution** for Bindu:

✅ **Distributed Tracing**: Full visibility into task flows
✅ **Metrics & Dashboards**: Track performance trends
✅ **Log Management**: Correlated logs with traces
✅ **APM**: Agent performance insights
✅ **Alerting**: Proactive issue detection
✅ **Incident Management**: Streamlined response
✅ **Status Pages**: Customer communication
✅ **Open Source**: Self-host or use cloud

Your existing OpenTelemetry implementation works seamlessly—just configure the endpoint and token! 🚀
