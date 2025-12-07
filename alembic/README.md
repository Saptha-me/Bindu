# Bindu Database Migrations

This directory contains Alembic migrations for the Bindu PostgreSQL storage backend.

## Prerequisites

1. PostgreSQL database running (local or remote)
2. Database URL configured in environment variables

## Configuration

Set the database URL in your environment:

```bash
# .env file or environment variable
DATABASE_URL=postgresql://user:password@localhost:5432/bindu  # pragma: allowlist secret

# Or using STORAGE__ prefix
STORAGE__POSTGRES_URL=postgresql://user:password@localhost:5432/bindu  # pragma: allowlist secret
```

## Quick Start

### 1. Install Dependencies

```bash
# Install with pip
pip install -e .

# Or with uv
uv pip install -e .
```

### 2. Create Database

```bash
# Using psql
createdb bindu

# Or with SQL
psql -U postgres -c "CREATE DATABASE bindu;"
```

### 3. Run Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history --verbose
```

## Common Commands

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade by 1 version
alembic upgrade +1

# Upgrade to specific revision
alembic upgrade 20241207_0001
```

### Rollback Migrations

```bash
# Downgrade by 1 version
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 20241207_0001

# Downgrade all (WARNING: destroys all data)
alembic downgrade base
```

### Create New Migration

```bash
# Create a new migration file
alembic revision -m "add_new_feature"

# Auto-generate migration from model changes (if using SQLAlchemy models)
alembic revision --autogenerate -m "auto_generated_changes"
```

### View Migration Status

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show detailed history with SQL
alembic history --verbose
```

## Migration Files

Migrations are located in `alembic/versions/`:

- `20241207_0001_initial_schema.py` - Initial database schema
  - Creates `tasks`, `contexts`, and `task_feedback` tables
  - Adds indexes for performance
  - Sets up automatic `updated_at` triggers

## Database Schema

### Tables

#### `tasks`
Stores A2A protocol tasks with JSONB history and artifacts.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| context_id | UUID | Reference to context |
| kind | VARCHAR(50) | Task type (default: 'task') |
| state | VARCHAR(50) | Current task state |
| state_timestamp | TIMESTAMPTZ | When state was last updated |
| history | JSONB | Message history array |
| artifacts | JSONB | Task artifacts array |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

#### `contexts`
Stores conversation contexts with message history.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| context_data | JSONB | Context-specific data |
| message_history | JSONB | Message history array |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

#### `task_feedback`
Stores user feedback for tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| task_id | UUID | Foreign key to tasks |
| feedback_data | JSONB | Feedback content |
| created_at | TIMESTAMPTZ | Creation timestamp |

### Indexes

Performance indexes are created for:
- Task lookups by context_id, state, timestamps
- JSONB queries on history, metadata, artifacts
- Context lookups by timestamps
- Feedback lookups by task_id

## Troubleshooting

### Connection Issues

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT version();"

# Check if database exists
psql -U postgres -l | grep bindu
```

### Migration Conflicts

```bash
# If migrations are out of sync, check current version
alembic current

# View pending migrations
alembic history

# Force stamp to specific version (use with caution!)
alembic stamp head
```

### Reset Database (Development Only)

```bash
# WARNING: This destroys all data!

# Downgrade all migrations
alembic downgrade base

# Drop and recreate database
dropdb bindu && createdb bindu

# Re-run migrations
alembic upgrade head
```

## Production Deployment

### Best Practices

1. **Always backup before migrations**
   ```bash
   pg_dump -U postgres bindu > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations in staging first**
   ```bash
   # Staging
   DATABASE_URL=postgresql://staging alembic upgrade head

   # Production (after testing)
   DATABASE_URL=postgresql://production alembic upgrade head
   ```

3. **Use read-only mode during migrations**
   - Put application in maintenance mode
   - Run migrations
   - Verify data integrity
   - Resume normal operations

4. **Monitor migration performance**
   ```bash
   # Time the migration
   time alembic upgrade head
   ```

### Kubernetes/Docker Deployment

Run migrations as an init container or job:

```yaml
# Kubernetes Job example
apiVersion: batch/v1
kind: Job
metadata:
  name: bindu-migrations
spec:
  template:
    spec:
      containers:
      - name: migrations
        image: bindu:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: bindu-secrets
              key: database-url
      restartPolicy: OnFailure
```

## Support

For issues or questions:
- Check the [Alembic documentation](https://alembic.sqlalchemy.org/)
- Review migration files in `alembic/versions/`
- Check application logs for detailed error messages
