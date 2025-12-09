# Tenacity Retry Mechanism Implementation

## Overview
Added Tenacity-based retry mechanism to APIs and workers in Bindu to handle transient failures gracefully.

## Changes Made

### 1. Dependencies
- **File**: `pyproject.toml`
- **Change**: Added `tenacity>=9.0.0` to project dependencies

### 2. Retry Settings
- **File**: `bindu/settings.py`
- **Changes**: Added `RetrySettings` class with configurable parameters:
  - Worker retry settings (max_attempts, min_wait, max_wait)
  - Storage retry settings
  - Scheduler retry settings
  - API retry settings
  - All configurable via environment variables with `RETRY__` prefix

### 3. Retry Configuration Module
- **File**: `bindu/utils/retry.py` (NEW)
- **Features**:
  - Uses `app_settings.retry` for centralized configuration
  - Four specialized retry decorators:
    - `@retry_worker_operation()` - For worker task execution (3 attempts, 1-10s wait)
    - `@retry_storage_operation()` - For database/storage ops (5 attempts, 0.5-5s wait)
    - `@retry_scheduler_operation()` - For scheduler ops (3 attempts, 1-8s wait)
    - `@retry_api_call()` - For external API calls (4 attempts, 1-15s wait)
  - Utility function `execute_with_retry()` for ad-hoc retry logic
  - Exponential backoff with jitter
  - Integrated logging for observability

### 4. Worker Retry Logic
- **File**: `bindu/server/workers/manifest_worker.py`
- **Changes**:
  - Added `@retry_worker_operation()` to `run_task()` method
  - Added `@retry_worker_operation(max_attempts=2)` to `cancel_task()` method
  - Handles transient failures during task execution

### 5. Storage Retry Logic

#### PostgreSQL Storage
- **File**: `bindu/server/storage/postgres_storage.py`
- **Changes**:
  - Replaced custom retry logic with Tenacity-based `execute_with_retry()`
  - All database operations now use retry mechanism via `_retry_on_connection_error()`
  - Handles connection errors, timeouts, and transient database issues

#### In-Memory Storage
- **File**: `bindu/server/storage/memory_storage.py`
- **Changes**:
  - Added `@retry_storage_operation()` to critical operations:
    - `load_task()` - 3 attempts, 0.1-1s wait
    - `submit_task()` - 3 attempts, 0.1-1s wait
    - `update_task()` - 3 attempts, 0.1-1s wait
  - Provides consistency with PostgreSQL storage interface

### 6. Scheduler Retry Logic

#### Redis Scheduler
- **File**: `bindu/server/scheduler/redis_scheduler.py`
- **Changes**:
  - Added `@retry_scheduler_operation()` to all task operations:
    - `run_task()`
    - `cancel_task()`
    - `pause_task()`
    - `resume_task()`
  - Handles Redis connection issues and transient failures

#### In-Memory Scheduler
- **File**: `bindu/server/scheduler/memory_scheduler.py`
- **Changes**:
  - Added `@retry_scheduler_operation()` to all task operations:
    - `run_task()` - 3 attempts, 0.1-1s wait
    - `cancel_task()` - 3 attempts, 0.1-1s wait
    - `pause_task()` - 3 attempts, 0.1-1s wait
    - `resume_task()` - 3 attempts, 0.1-1s wait
  - Provides consistency with Redis scheduler interface

### 7. Application Initialization Retry Logic
- **File**: `bindu/server/applications.py`
- **Changes**:
  - Added retry logic to `create_storage()` initialization in lifespan
  - Added retry logic to `create_scheduler()` initialization in lifespan
  - Uses `execute_with_retry()` with settings-based configuration
  - Ensures resilient startup even with transient connection failures

### 8. Environment Configuration
- **File**: `.env.example`
- **Changes**: Added retry configuration section with all settings:
  - `RETRY__WORKER_MAX_ATTEMPTS`, `RETRY__WORKER_MIN_WAIT`, `RETRY__WORKER_MAX_WAIT`
  - `RETRY__STORAGE_MAX_ATTEMPTS`, `RETRY__STORAGE_MIN_WAIT`, `RETRY__STORAGE_MAX_WAIT`
  - `RETRY__SCHEDULER_MAX_ATTEMPTS`, `RETRY__SCHEDULER_MIN_WAIT`, `RETRY__SCHEDULER_MAX_WAIT`
  - `RETRY__API_MAX_ATTEMPTS`, `RETRY__API_MIN_WAIT`, `RETRY__API_MAX_WAIT`

### 9. Tests
- **File**: `tests/unit/test_retry.py` (NEW)
- **Coverage**:
  - Configuration tests
  - Decorator functionality tests
  - Success and failure scenarios
  - Retry attempt verification
  - Integration tests
  - Logging behavior tests

## Retry Strategy

### Exponential Backoff with Jitter
All retry decorators use exponential backoff with random jitter to:
- Prevent thundering herd problems
- Distribute retry attempts over time
- Reduce load on failing services

### Configurable Parameters
Each decorator accepts:
- `max_attempts`: Maximum retry attempts
- `min_wait`: Minimum wait time between retries (seconds)
- `max_wait`: Maximum wait time between retries (seconds)

### Retryable Exceptions
Currently retries on:
- `ConnectionError`
- `TimeoutError`
- `asyncio.TimeoutError`
- Generic `Exception` (can be refined per use case)

## Benefits

1. **Resilience**: Automatic recovery from transient failures
2. **Observability**: Integrated logging of retry attempts
3. **Consistency**: Uniform retry behavior across all components
4. **Configurability**: All retry parameters configurable via environment variables
5. **Maintainability**: Centralized retry logic in settings and retry module
6. **Flexibility**: Override defaults per decorator call when needed

## Usage Examples

### Using Default Settings
```python
# Uses app_settings.retry.worker_* values
@retry_worker_operation()
async def run_task(self, params: TaskSendParams) -> None:
    # Task execution logic
    pass
```

### Overriding Settings
```python
# Override specific parameters
@retry_storage_operation(max_attempts=10, min_wait=2.0)
async def update_task(self, task_id: UUID, state: str) -> Task:
    # Database update logic with custom retry
    pass
```

### Environment Configuration
```bash
# In .env file
RETRY__WORKER_MAX_ATTEMPTS=5
RETRY__WORKER_MIN_WAIT=2.0
RETRY__WORKER_MAX_WAIT=20.0
```

### Ad-hoc Retry
```python
result = await execute_with_retry(
    some_async_function,
    arg1, arg2,
    max_attempts=5,
    min_wait=1,
    max_wait=10
)
```

## Future Enhancements

1. **Circuit Breaker**: Add circuit breaker pattern for failing services
2. **Metrics**: Export retry metrics to observability platform
3. **Custom Retry Conditions**: Per-exception retry strategies
4. **Retry Budget**: Limit total retry time across all operations
5. **Adaptive Backoff**: Adjust backoff based on system load

## Testing

Run retry tests:
```bash
uv run pytest tests/unit/test_retry.py -v
```

Run all tests:
```bash
uv run pytest tests/ -v
```

## Notes

- Memory storage and scheduler have shorter retry windows (0.1-1s) since they're in-memory operations
- PostgreSQL and Redis operations use longer retry windows to handle network/connection issues
- All retry attempts are logged for debugging and monitoring
- Retry decorators preserve exception types and messages for proper error handling
