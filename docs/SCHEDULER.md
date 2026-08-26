# Redis Scheduler

Bindu uses Redis as its distributed task scheduler for coordinating work across multiple workers and processes. The scheduler uses Redis lists with blocking operations for efficient task distribution.

**Scheduler is optional** - InMemoryScheduler is used by default for single-process deployments.

## Architecture

```mermaid
sequenceDiagram
    participant Client
    participant TaskManager
    participant Scheduler
    participant Queue
    participant Worker
    participant Storage

    Note over TaskManager: Startup
    TaskManager->>Scheduler: Initialize (Redis/Memory)
    TaskManager->>Worker: Start ManifestWorker
    Worker->>Scheduler: Listen for tasks

    Note over Client,Storage: Task Execution Flow

    rect rgb(240, 248, 255)
        Note over Client,Scheduler: 1. Task Submission
        Client->>TaskManager: POST / (message/send)
        TaskManager->>Storage: Save task (state: pending)
        TaskManager->>Scheduler: run_task(params)

        alt Redis Scheduler
            Scheduler->>Queue: RPUSH bindu:tasks
            Note over Queue: Task queued in Redis
        else Memory Scheduler
            Scheduler->>Queue: Send to memory stream
            Note over Queue: Task in memory queue
        end
    end

    rect rgb(255, 248, 240)
        Note over Worker,Storage: 2. Task Processing

        alt Redis Scheduler
            Worker->>Queue: BLPOP bindu:tasks (blocking)
            Queue-->>Worker: Task operation
        else Memory Scheduler
            Worker->>Queue: Receive from stream
            Queue-->>Worker: Task operation
        end

        Worker->>Storage: Update state: working
        Worker->>Worker: Execute agent handler
        Worker->>Storage: Update state: completed/failed
    end

    rect rgb(240, 255, 240)
        Note over Client,Storage: 3. Task Monitoring
        Client->>TaskManager: GET /tasks/{task_id}
        TaskManager->>Storage: Load task
        Storage-->>TaskManager: Task data
        TaskManager-->>Client: {state, result}
    end

    Note over TaskManager,Worker: Operations Supported
    Note over Scheduler: - run_task<br/>- cancel_task<br/>- pause_task<br/>- resume_task
```

## Configuration

### Environment Variables

Configure Redis connection via environment variables (see `.env.example`):

```bash
# Scheduler Configuration
# Type: "redis" for distributed scheduling or "memory" for single-process
SCHEDULER_TYPE=redis

# Redis connection string
REDIS_URL=rediss://default:<password>@<host>:<port>
```

**Connection String Formats:**

**With password:**
```
rediss://default:****@hostname:port
```

**Without password (local development):**
```
redis://localhost:6379
```

**With database number:**
```
redis://localhost:6379/0
```

**Example:**
```bash
REDIS_URL=rediss://default:****@redis-12345.upstash.io:6379
```

### Agent Configuration

No additional configuration needed in your agent code. Scheduler is configured via environment variables:

```python
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}

bindufy(config, handler)
```

## Setting Up Redis

### Local Development

#### Using Docker (Recommended)

```bash
# Start Redis container
docker run -d \
  --name bindu-redis \
  -p 6379:6379 \
  redis:7-alpine

# Set environment variable
export REDIS_URL="redis://localhost:6379"
```

#### Using Local Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Set environment variable
export REDIS_URL="redis://localhost:6379"
```

### Cloud Deployment

#### Upstash (Serverless Redis)

1. Create account at [upstash.com](https://upstash.com)
2. Create a new Redis database
3. Copy the connection string (TLS enabled)
4. Set environment variable:
   ```bash
   export REDIS_URL="rediss://default:****@xxx.upstash.io:6379"
   ```

## Switching Between Scheduler Types

### From Memory to Redis

1. Set environment variables:
   ```bash
   export SCHEDULER_TYPE=redis
   export REDIS_URL="redis://localhost:6379"
   ```

2. Restart agent

3. Existing in-memory queue is lost (ephemeral)

### From Redis to Memory

1. Update environment:
   ```bash
   export SCHEDULER_TYPE=memory
   # or unset SCHEDULER_TYPE (memory is default)
   ```

2. Restart agent

3. Tasks in Redis queue remain but won't be processed

## Pause / Resume Support

Bindu workers now support pausing and resuming long-running tasks. When a pause
is requested the worker will persist a lightweight checkpoint into the task
metadata and transition the task to the `suspended` state. This allows the
runtime to release resources while preserving progress. A subsequent resume
operation restores the checkpoint (via a worker-provided hook when available)
and transitions the task to the `resumed` state to continue execution.

Notes:
- Storage implementations persist the checkpoint in task `metadata.suspended_checkpoint`.
- Worker implementations may provide `capture_execution_state`, `restore_execution_state`,
  `on_pause` and `on_resume` hooks for richer behavior.
- The scheduler exposes `pause_task` and `resume_task` operations to drive these transitions.
