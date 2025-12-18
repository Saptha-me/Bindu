# Hydra Authentication - Test Suite Documentation

This document describes the test suite for the Hydra authentication implementation.

> **Note:** Test files (`test_*.py`) are gitignored in this project. This document serves as a reference for implementing tests.

## Test Structure

```
tests/
├── unit/
│   ├── test_hydra_middleware.py
│   ├── test_kratos_client.py
│   ├── test_credential_manager.py
│   └── test_oauth_flows.py
├── integration/
│   └── test_oauth_flows.py
└── e2e/
    └── test_hydra_auth_flow.py
```

## Unit Tests

### test_hydra_middleware.py

Tests for `HydraMiddleware` class:

**Test Cases:**
1. `test_public_endpoint_bypass` - Public endpoints skip authentication
2. `test_missing_token_returns_401` - Missing token returns 401
3. `test_valid_token_authentication` - Valid token authenticates successfully
4. `test_inactive_token_returns_401` - Inactive token returns 401
5. `test_scope_validation` - Required scopes are validated
6. `test_m2m_token_detection` - M2M tokens detected correctly
7. `test_token_introspection_error` - Introspection errors handled
8. `test_extract_user_info` - User info extracted from token payload

**Run Tests:**
```bash
pytest tests/unit/test_hydra_middleware.py -v
```

### test_kratos_client.py

Tests for `KratosClient` class:

**Test Cases:**
1. `test_get_identity` - Fetch user identity
2. `test_update_identity` - Update user traits
3. `test_get_oauth_token` - Retrieve OAuth token
4. `test_store_oauth_token` - Store OAuth credentials
5. `test_refresh_oauth_token` - Check token expiration
6. `test_revoke_oauth_connection` - Revoke provider connection
7. `test_list_user_connections` - List all connections
8. `test_identity_not_found` - Handle missing identity
9. `test_token_expiration_detection` - Detect expired tokens

**Run Tests:**
```bash
pytest tests/unit/test_kratos_client.py -v
```

### test_credential_manager.py

Tests for `CredentialManager` class:

**Test Cases:**
1. `test_check_requirements_satisfied` - All credentials present
2. `test_check_requirements_missing` - Missing credentials detected
3. `test_check_requirements_expired` - Expired tokens detected
4. `test_get_credentials` - Fetch credentials for providers
5. `test_inject_into_context` - Inject credentials into context
6. `test_refresh_if_needed` - Token refresh check
7. `test_multiple_providers` - Handle multiple providers

**Run Tests:**
```bash
pytest tests/unit/test_credential_manager.py -v
```

### test_oauth_flows.py

Tests for OAuth route handlers:

**Test Cases:**
1. `test_oauth_authorize` - Authorization URL generation
2. `test_oauth_callback_success` - Successful callback handling
3. `test_oauth_callback_error` - OAuth error handling
4. `test_oauth_callback_invalid_state` - CSRF protection
5. `test_list_connections` - List user connections
6. `test_revoke_connection` - Revoke provider connection
7. `test_unauthorized_access` - Require authentication

**Run Tests:**
```bash
pytest tests/unit/test_oauth_flows.py -v
```

## Integration Tests

### test_oauth_flows.py (Integration)

End-to-end OAuth flow tests:

**Test Cases:**
1. `test_complete_oauth_flow` - Full authorization flow
2. `test_token_exchange` - Code to token exchange
3. `test_credential_storage` - Tokens stored in Kratos
4. `test_credential_retrieval` - Tokens retrieved correctly
5. `test_provider_metadata` - Provider-specific metadata
6. `test_multiple_providers_flow` - Multiple OAuth flows

**Setup:**
```bash
# Start Ory services
docker-compose -f docker-compose.hydra.yml up -d

# Run integration tests
pytest tests/integration/test_oauth_flows.py -v
```

## E2E Tests

### test_hydra_auth_flow.py

Complete authentication flow tests:

**Test Scenario:**
```python
async def test_complete_auth_flow():
    # 1. Register user via Kratos
    user = await register_user("test@example.com", "password")
    assert user["id"]
    
    # 2. Login and get Hydra token
    token = await login_user("test@example.com", "password")
    assert token["access_token"]
    
    # 3. Call agent without credentials (should fail)
    response = await call_agent(token, "Search Notion")
    assert response["error"] == "authorization_required"
    assert "notion" in response["missing_providers"]
    
    # 4. Authorize Notion
    auth_url = response["authorization_urls"]["notion"]
    await authorize_provider(token, "notion", auth_url)
    
    # 5. Call agent again (should succeed)
    response = await call_agent(token, "Search Notion")
    assert response["status"] == "success"
    assert "credentials" in response
```

**Run E2E Tests:**
```bash
# Ensure services are running
docker-compose -f docker-compose.hydra.yml ps

# Run E2E tests
pytest tests/e2e/test_hydra_auth_flow.py -v --timeout=60
```

## Test Coverage

**Target Coverage:** 80%

**Run with Coverage:**
```bash
pytest tests/ -v --cov=bindu.auth --cov=bindu.server.middleware.auth.hydra --cov=bindu.penguin.credential_manager --cov-report=html
```

**View Coverage Report:**
```bash
open htmlcov/index.html
```

## Mocking

### Mock Hydra Client

```python
from unittest.mock import AsyncMock, patch

@patch("bindu.server.middleware.auth.hydra.HydraClient")
async def test_with_mock_hydra(mock_client):
    mock_instance = AsyncMock()
    mock_instance.introspect_token.return_value = {
        "active": True,
        "sub": "user123",
        "scope": "openid email"
    }
    mock_client.return_value.__aenter__.return_value = mock_instance
    
    # Test code here
```

### Mock Kratos Client

```python
@patch("bindu.penguin.credential_manager.KratosClient")
async def test_with_mock_kratos(mock_client):
    mock_instance = AsyncMock()
    mock_instance.get_oauth_token.return_value = {
        "access_token": "test_token",
        "token_type": "Bearer"
    }
    mock_client.return_value.__aenter__.return_value = mock_instance
    
    # Test code here
```

## Test Fixtures

### Common Fixtures

```python
@pytest.fixture
def hydra_config():
    """Mock Hydra configuration."""
    config = MagicMock()
    config.admin_url = "http://localhost:4445"
    config.required_scopes = []
    config.public_endpoints = ["/.well-known/agent.json"]
    return config

@pytest.fixture
async def test_user():
    """Create test user in Kratos."""
    async with KratosClient() as kratos:
        identity = await kratos.create_identity({
            "traits": {"email": "test@example.com"}
        })
        yield identity
        # Cleanup
        await kratos.delete_identity(identity["id"])

@pytest.fixture
def mock_oauth_provider():
    """Mock OAuth provider responses."""
    with patch("httpx.AsyncClient") as mock:
        mock.return_value.post.return_value.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "expires_in": 3600
        }
        yield mock
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/unit/test_hydra_middleware.py -v
```

### Specific Test
```bash
pytest tests/unit/test_hydra_middleware.py::test_valid_token_authentication -v
```

### With Coverage
```bash
pytest tests/ --cov=bindu --cov-report=term-missing
```

### Parallel Execution
```bash
pytest tests/ -n auto
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: bindu_secret
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      
      hydra:
        image: oryd/hydra:v2.2.0
        env:
          DSN: postgres://bindu:bindu_secret@postgres:5432/bindu_auth
      
      kratos:
        image: oryd/kratos:v1.1.0
        env:
          DSN: postgres://bindu:bindu_secret@postgres:5432/bindu_auth
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev
      
      - name: Run tests
        run: pytest tests/ -v --cov=bindu --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Performance Tests

### Load Testing Token Validation

```python
import asyncio
import time

async def test_token_validation_performance():
    """Test token validation latency."""
    middleware = HydraMiddleware(app, config)
    
    start = time.time()
    tasks = [
        middleware._validate_token_async("test_token")
        for _ in range(100)
    ]
    await asyncio.gather(*tasks)
    end = time.time()
    
    avg_latency = (end - start) / 100
    assert avg_latency < 0.05  # < 50ms average
```

## Troubleshooting Tests

### Tests Failing Locally
- Ensure Ory services are running
- Check environment variables are set
- Clear pytest cache: `pytest --cache-clear`

### Flaky Tests
- Add retries for network calls
- Increase timeouts for async operations
- Use fixtures for proper setup/teardown

### Coverage Not Updating
- Delete `.coverage` file
- Run with `--cov-append` flag
- Check `.coveragerc` configuration
