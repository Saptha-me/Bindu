# Bindu Storage Layer

Persistent and in-memory storage implementations for A2A protocol task and context management.

## Overview

The storage layer provides a pluggable backend system for storing tasks, contexts, and feedback. It supports multiple storage backends that can be switched via configuration without code changes.

## Architecture

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│      (TaskManager, Agents, etc.)        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         Storage Interface (ABC)         │
│  - load_task()                          │
│  - submit_task()                        │
│  - update_task()                        │
│  - list_tasks()                         │
│  - load_context()                       │
│  - update_context()                     │
│  - etc.                                 │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   Memory     │  │  PostgreSQL  │
│   Storage    │  │   Storage    │
└──────────────┘  └──────────────┘
```

## Available Backends

### 1. InMemoryStorage (Default)

**Use Cases:**
- Local development
- Testing
- Prototyping
- Single-session applications

**Pros:**
- ✅ Fastest performance (no I/O)
- ✅ Zero configuration
- ✅ No dependencies

**Cons:**
- ❌ Data lost on restart
- ❌ Not suitable for production
- ❌ Single-process only

**Configuration:**
```bash
STORAGE_BACKEND=memory
```

### 2. PostgresStorage (Production)

**Use Cases:**
- Production deployments
- Multi-pod/distributed systems
- Long-term data retention
- Enterprise environments

**Pros:**
- ✅ Persistent storage
- ✅ Survives pod restarts
- ✅ Multi-process safe
- ✅ ACID transactions
- ✅ Rich querying with JSONB
- ✅ Automatic migrations

**Cons:**
- ❌ Requires PostgreSQL database
- ❌ Slightly higher latency than memory
- ❌ Additional infrastructure

**Configuration:**
```bash
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://user:password@host:5432/bindu  # pragma: allowlist secret
STORAGE__POSTGRES_POOL_MAX=10
STORAGE__RUN_MIGRATIONS_ON_STARTUP=true
```

## Quick Start

### Using the Factory (Recommended)

```python
from bindu.server.storage import create_storage, close_storage

# Create storage based on configuration
storage = await create_storage()

# Use storage
task = await storage.load_task(task_id)
await storage.update_task(task_id, "completed", new_artifacts=[...])

# Cleanup (for PostgreSQL)
await close_storage(storage)
```

### Direct Instantiation

```python
from bindu.server.storage import InMemoryStorage, PostgresStorage

# In-memory storage
storage = InMemoryStorage()

# PostgreSQL storage
storage = PostgresStorage(
    database_url="postgresql://user:pass@localhost/bindu"  # pragma: allowlist secret
)
await storage.connect()
```

## Configuration

### Environment Variables

```bash
# Storage backend selection
STORAGE_BACKEND=postgres  # Options: memory, postgres

# PostgreSQL configuration
DATABASE_URL=postgresql://bindu:bindu@localhost:5432/bindu  # pragma: allowlist secret
STORAGE__POSTGRES_POOL_MIN=2
STORAGE__POSTGRES_POOL_MAX=10
STORAGE__POSTGRES_TIMEOUT=60
STORAGE__POSTGRES_COMMAND_TIMEOUT=30
STORAGE__POSTGRES_MAX_RETRIES=3
STORAGE__POSTGRES_RETRY_DELAY=1.0

# Migration settings
STORAGE__RUN_MIGRATIONS_ON_STARTUP=true
```

### Settings Class

```python
from bindu.settings import app_settings

# Access storage settings
backend = app_settings.storage.backend
db_url = app_settings.storage.postgres_url
```

## Database Schema (PostgreSQL)

### Tables

#### `tasks`
Stores A2A protocol tasks with JSONB history and artifacts.

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    context_id UUID NOT NULL,
    kind VARCHAR(50) NOT NULL DEFAULT 'task',
    state VARCHAR(50) NOT NULL,
    state_timestamp TIMESTAMPTZ NOT NULL,
    history JSONB NOT NULL DEFAULT '[]',
    artifacts JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `contexts`
Stores conversation contexts with message history.

```sql
CREATE TABLE contexts (
    id UUID PRIMARY KEY,
    context_data JSONB NOT NULL DEFAULT '{}',
    message_history JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `task_feedback`
Stores user feedback for tasks.

```sql
CREATE TABLE task_feedback (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    feedback_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Indexes

Performance indexes are automatically created:
- B-tree indexes on `context_id`, `state`, timestamps
- GIN indexes on JSONB columns for efficient querying
- Foreign key indexes for referential integrity

## API Reference

### Core Operations

#### `load_task(task_id, history_length=None)`
Load a task from storage.

```python
task = await storage.load_task(task_id)
task = await storage.load_task(task_id, history_length=10)  # Last 10 messages
```

#### `submit_task(context_id, message)`
Create a new task or continue an existing non-terminal task.

```python
task = await storage.submit_task(context_id, message)
```

#### `update_task(task_id, state, new_artifacts=None, new_messages=None, metadata=None)`
Update task state and append new content.

```python
# Update state only
task = await storage.update_task(task_id, "working")

# Add artifacts and messages
task = await storage.update_task(
    task_id,
    "completed",
    new_artifacts=[artifact],
    new_messages=[message],
    metadata={"duration": 5.2}
)
```

#### `list_tasks(length=None)`
List all tasks.

```python
all_tasks = await storage.list_tasks()
recent_tasks = await storage.list_tasks(length=10)
```

#### `list_tasks_by_context(context_id, length=None)`
List tasks in a specific context.

```python
context_tasks = await storage.list_tasks_by_context(context_id)
```

### Context Operations

#### `load_context(context_id)`
Load context data.

```python
context = await storage.load_context(context_id)
```

#### `update_context(context_id, context)`
Store or update context.

```python
await storage.update_context(context_id, {"user_id": "123", "preferences": {...}})
```

#### `list_contexts(length=None)`
List all contexts.

```python
contexts = await storage.list_contexts()
```

### Utility Operations

#### `clear_context(context_id)`
Clear all tasks in a context.

```python
await storage.clear_context(context_id)
```

#### `clear_all()`
Clear all data (destructive).

```python
await storage.clear_all()
```

### Feedback Operations

#### `store_task_feedback(task_id, feedback_data)`
Store user feedback.

```python
await storage.store_task_feedback(task_id, {
    "rating": 5,
    "comment": "Great response!"
})
```

#### `get_task_feedback(task_id)`
Retrieve feedback.

```python
feedback = await storage.get_task_feedback(task_id)
```

## Migration Management

### Running Migrations

```bash
# Automatic (on startup)
STORAGE__RUN_MIGRATIONS_ON_STARTUP=true

# Manual
alembic upgrade head

# Check current version
alembic current

# View history
alembic history
```

### Creating New Migrations

```bash
# Create new migration
alembic revision -m "add_new_feature"

# Auto-generate from model changes
alembic revision --autogenerate -m "auto_changes"
```

See [alembic/README.md](../../../../alembic/README.md) for detailed migration documentation.

## Production Deployment

### Docker Compose Example

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: bindu
      POSTGRES_USER: bindu
      POSTGRES_PASSWORD: bindu
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  bindu:
    build: .
    environment:
      STORAGE_BACKEND: postgres
      DATABASE_URL: postgresql://bindu:bindu@postgres:5432/bindu
      STORAGE__RUN_MIGRATIONS_ON_STARTUP: "true"
    depends_on:
      - postgres
    ports:
      - "3773:3773"

volumes:
  postgres_data:
```

### Kubernetes Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bindu-config
data:
  STORAGE_BACKEND: "postgres"
  STORAGE__RUN_MIGRATIONS_ON_STARTUP: "true"

---
apiVersion: v1
kind: Secret
metadata:
  name: bindu-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres-service:5432/bindu"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bindu
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bindu
  template:
    metadata:
      labels:
        app: bindu
    spec:
      containers:
      - name: bindu
        image: bindu:latest
        envFrom:
        - configMapRef:
            name: bindu-config
        - secretRef:
            name: bindu-secrets
        ports:
        - containerPort: 3773
```

## Performance Considerations

### Connection Pooling

PostgreSQL storage uses connection pooling for optimal performance:

```python
# Configure pool size based on load
STORAGE__POSTGRES_POOL_MIN=2   # Minimum connections
STORAGE__POSTGRES_POOL_MAX=20  # Maximum connections
```

**Guidelines:**
- Development: 2-5 connections
- Production (low traffic): 10-20 connections
- Production (high traffic): 20-50 connections
- Formula: `max_connections = (num_pods * pool_max) + buffer`

### Query Optimization

JSONB indexes are automatically created for:
- Task history queries
- Metadata searches
- Artifact lookups

Use JSONB operators for efficient queries:
```sql
-- Find tasks with specific metadata
SELECT * FROM tasks WHERE metadata @> '{"priority": "high"}';

-- Search in history
SELECT * FROM tasks WHERE history @> '[{"role": "user"}]';
```

### Monitoring

Monitor these metrics:
- Connection pool utilization
- Query latency
- Transaction duration
- Index hit ratio

## Testing

### Unit Tests

```python
import pytest
from bindu.server.storage import InMemoryStorage, PostgresStorage

@pytest.mark.asyncio
async def test_task_lifecycle():
    storage = InMemoryStorage()

    # Submit task
    task = await storage.submit_task(context_id, message)
    assert task["status"]["state"] == "submitted"

    # Update task
    task = await storage.update_task(task["id"], "completed")
    assert task["status"]["state"] == "completed"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_postgres_storage():
    storage = PostgresStorage(database_url="postgresql://test:test@localhost/test_db")
    await storage.connect()

    try:
        # Test operations
        task = await storage.submit_task(context_id, message)
        loaded = await storage.load_task(task["id"])
        assert loaded["id"] == task["id"]
    finally:
        await storage.disconnect()
```

## Troubleshooting

### Connection Issues

```python
# Check database connectivity
psql $DATABASE_URL -c "SELECT version();"

# Verify pool settings
# Increase timeout if seeing connection errors
STORAGE__POSTGRES_TIMEOUT=120
```

### Migration Errors

```bash
# Check current version
alembic current

# View pending migrations
alembic history

# Manually run migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Performance Issues

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public';
```

## Best Practices

1. **Use the factory** - Always use `create_storage()` for automatic configuration
2. **Close connections** - Call `close_storage()` on shutdown for PostgreSQL
3. **Handle retries** - PostgreSQL storage has built-in retry logic for transient failures
4. **Monitor connections** - Keep pool size appropriate for your load
5. **Run migrations** - Enable automatic migrations in production or use init containers
6. **Backup regularly** - Use `pg_dump` for PostgreSQL backups
7. **Test both backends** - Ensure your code works with both memory and PostgreSQL

## Support

For issues or questions:
- Check the [main README](../../../../README.md)
- Review [Alembic migrations](../../../../alembic/README.md)
- Open an issue on GitHub
