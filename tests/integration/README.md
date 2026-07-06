# Integration Tests

End-to-end tests that verify complete flows across Bindu components. Some tests use real servers on local network ports; others exercise deterministic multi-component flows in process. These are slower and less hermetic than unit tests, so deterministic E2E tests run in CI (every PR) but **not** in pre-commit (every commit).

## Test Structure

```
tests/integration/
  grpc/
    __init__.py
    test_grpc_e2e.py       # Full gRPC + A2A round-trip tests
  x402/
    __init__.py
    test_e2e_scenarios.py  # Deterministic x402 settlement-ordering flows
    test_skale_facilitator_supported.py  # Live SKALE facilitator smoke tests, opt-in
  test_task_ownership.py   # Task ownership and context isolation checks
```

## Running

```bash
# Run non-network E2E integration tests
uv run pytest tests/integration/ -v -m "e2e and not network"

# Run just gRPC E2E tests
uv run pytest tests/integration/grpc/ -v -m e2e

# Run deterministic x402 E2E tests
uv run pytest tests/integration/x402/ -v -m "e2e and x402 and not network"

# Run live x402 facilitator smoke tests
X402_NETWORK_TESTS=1 uv run pytest tests/integration/x402/ -v -m "x402 and network"

# Run with verbose output
uv run pytest tests/integration/grpc/ tests/integration/x402/ -v -m "e2e and not network" -s
```

## gRPC E2E Tests

**File:** `grpc/test_grpc_e2e.py`

These tests verify the complete language-agnostic agent flow — the same path a TypeScript or Kotlin SDK takes when calling `bindufy()`.

### What's tested

| Test | What it proves |
|------|---------------|
| `test_heartbeat_unregistered` | gRPC server starts on test port, accepts Heartbeat calls, returns `acknowledged=false` for unknown agents |
| `test_register_agent` | Full RegisterAgent flow: config validation, DID creation, manifest with GrpcAgentClient, HTTP server started |
| `test_heartbeat_registered` | After registration, Heartbeat returns `acknowledged=true` |
| `test_agent_card_available` | A2A agent card at `/.well-known/agent.json` contains DID, skills, and capabilities |
| `test_send_message_and_get_response` | **Full round-trip**: A2A HTTP message -> TaskManager -> Scheduler -> Worker -> GrpcAgentClient -> MockAgentHandler -> response with DID-signed artifacts |
| `test_health_endpoint` | `/health` endpoint returns 200 on the registered agent's HTTP server |

### Architecture

The tests use a `MockAgentHandler` that simulates what a TypeScript or Kotlin SDK does:

```
Test Process
  |
  |-- Start gRPC server (BinduService) on :13774
  |-- Start MockAgentHandler on :13999
  |-- Call RegisterAgent (config + callback=:13999)
  |     |
  |     |-- Core runs bindufy logic
  |     |-- Creates GrpcAgentClient(:13999)
  |     |-- Starts HTTP/A2A on :13773
  |
  |-- Send A2A message via HTTP to :13773
  |     |
  |     |-- TaskManager -> Scheduler -> Worker
  |     |-- Worker calls GrpcAgentClient(:13999)
  |     |-- MockAgentHandler returns "Echo: ..."
  |     |-- Worker processes response
  |
  |-- Verify task completed with correct content
  |-- Clean up all servers
```

### Ports used

| Port | Purpose |
|------|---------|
| 13773 | HTTP/A2A server (non-standard to avoid conflicts) |
| 13774 | gRPC BinduService (non-standard) |
| 13999 | MockAgentHandler (non-standard) |

Non-standard ports are used to avoid conflicts with a locally running Bindu instance on the default ports (3773/3774).

### MockAgentHandler

The mock handler echoes messages back with a prefix:

```python
class MockAgentHandler(AgentHandlerServicer):
    def __init__(self):
        self.calls = []

    def HandleMessages(self, request, context):
        self.calls.append(request)
        last_message = request.messages[-1] if request.messages else None
        content = f"Echo: {last_message.content}" if last_message else "No messages"
        return HandleResponse(
            content=content,
            state="",
            is_final=True,
        )
```

This mirrors how a real SDK behaves: it receives messages over gRPC, runs the developer's handler, and returns the response.

## x402 E2E Tests

**File:** `x402/test_e2e_scenarios.py`

These tests verify the paid task lifecycle around x402 verification, settlement, and replay handling. They use the real `X402Middleware`, `ManifestWorker`, in-memory storage, and nonce store, while mocking the facilitator boundary so each payment outcome is deterministic.

### What's tested

| Test | What it proves |
|------|---------------|
| `test_scenario_1_front_run_drain` | Settlement failure marks the task failed, withholds artifacts, and preserves recovery metadata |
| `test_scenario_2_settle_timeout` | Facilitator timeouts fail closed before the agent runs and keep reconciliation metadata |
| `test_scenario_3_parallel_nonce_double_spend` | One successful settlement can complete while a competing failed settlement avoids an unpaid agent call |
| `test_scenario_4_replay_rejected_at_middleware` | Replayed payment nonces are rejected by middleware before verification |

**File:** `x402/test_skale_facilitator_supported.py`

These are live-network smoke tests for the SKALE-aware facilitator. They are skipped by default and only run when `X402_NETWORK_TESTS=1` is set.

## Adding New Integration Tests

### For new gRPC features

Add tests to `grpc/test_grpc_e2e.py`. Use the existing `grpc_server` and `mock_agent` fixtures, which handle server lifecycle:

```python
@pytest.mark.e2e
@pytest.mark.slow
def test_my_new_feature(grpc_server, mock_agent):
    server, registry = grpc_server
    # Your test here
```

### For new integration areas

Create a new directory:

```
tests/integration/
  grpc/           # Existing
  x402/           # Existing payment flows
  payments/       # New payment area, if separate from x402
    __init__.py
    test_e2e.py
```

Mark tests with `@pytest.mark.e2e` and `@pytest.mark.slow`.
Use `@pytest.mark.network` for tests that call external services, and keep those tests opt-in through an environment variable.

## CI Pipeline

Integration tests run in the GitHub Actions CI workflow (`.github/workflows/ci.yml`) on every PR to main. They run **after** unit tests pass:

```text
Unit Tests (pre-commit) --> E2E gRPC + x402 Tests (CI) --> TypeScript SDK Build (CI)
```

## Troubleshooting

### "Port already in use"

Kill processes on the test ports:

```bash
lsof -ti:13773 -ti:13774 -ti:13999 | xargs kill 2>/dev/null
```

### Tests hang

The test fixture has a 30-second timeout for server startup. If tests hang:
- Check if the ports are already occupied
- Check if a previous test run left zombie processes
- Run with `-s` flag to see live output: `uv run pytest tests/integration/grpc/ tests/integration/x402/ -v -m "e2e and not network" -s`

### Tests pass locally but fail in CI

Common causes:
- CI doesn't have `grpcio` installed (check `pyproject.toml` optional deps)
- Port conflicts with other CI jobs (the non-standard ports should prevent this)
- Timing issues — increase sleep/retry values if needed
