# Bindu x402 Integration: Architecture, Flow, and Examples

This document explains how x402 payments are integrated into Bindu on this branch. It covers the configuration, extension advertisement and activation, metadata model, worker lifecycle hooks (verify/settle), helper utilities, and endpoint behavior, with code references and end‑to‑end examples.

## Contents
- Overview
- Configuration and Settings
- Extension and Capability Advertisement
- Endpoint Integration and Activation Header
- Payment Flow and Metadata Contract
- Worker Lifecycle Integration (verify and settle)
- Merchant Helper for PaymentRequirements
- Utilities for Task Metadata
- End-to-End Examples
- Running Tests and Markers
- References

---

## Overview
x402 is a protocol for agent-to-agent payments. In Bindu, it is integrated as an A2A extension that:
- Advertises the agent’s capability to use x402 via the agent card (capabilities.extensions)
- Negotiates activation using the `X-A2A-Extensions` HTTP header
- Coordinates payment-required → payment-submitted → verified/settled flow via task metadata and the worker logic

Core code:
- bindu/extensions/x402/extension.py – extension declaration and activation header helpers
- bindu/extensions/x402/utils.py – metadata helpers for task records
- bindu/extensions/x402/merchant.py – helper to build x402 `PaymentRequirements`
- bindu/server/workers/manifest_worker.py – verify/settle orchestration and state transitions
- bindu/server/endpoints/{a2a_protocol.py, agent_card.py} – activation header echoing
- bindu/penguin/bindufy.py – capability injection so agents announce x402 support
- bindu/settings.py – centralized x402 configuration (URIs, metadata keys, statuses)

---

## Configuration and Settings
File: `bindu/settings.py` (class `X402Settings`)

Key fields (with defaults):
- `extension_uri`: `https://github.com/google-a2a/a2a-x402/v0.1`
- `provider`: `coinbase`
- `facilitator_url`: "" (unused in code, FacilitatorClient is constructed without explicit URL)
- `default_network`: `base`
- `pay_to_env`: `X402_PAY_TO` (env var name for merchant pay-to address)
- `max_timeout_seconds`: `600`
- Metadata keys:
  - `meta_status_key`: `x402.payment.status`
  - `meta_required_key`: `x402.payment.required`
  - `meta_payload_key`: `x402.payment.payload`
  - `meta_receipts_key`: `x402.payment.receipts`
  - `meta_error_key`: `x402.payment.error`
- Status values:
  - `status_required`: `payment-required`
  - `status_submitted`: `payment-submitted`
  - `status_verified`: `payment-verified`
  - `status_completed`: `payment-completed`
  - `status_failed`: `payment-failed`

Env configuration (example `.env`):
```
X402__DEFAULT_NETWORK=base
X402__MAX_TIMEOUT_SECONDS=600
# Typically provided out-of-band; if you load pay-to from env:
X402_PAY_TO=0xYourMerchantAddress
```

---

## Extension and Capability Advertisement
Files:
- `bindu/extensions/x402/extension.py`
- `bindu/penguin/bindufy.py`

Declaration helper:
```python
# bindu/extensions/x402/extension.py
def get_agent_extension(required: bool = False, description: Optional[str] = None) -> AgentExtension:
    return AgentExtension(
        uri=app_settings.x402.extension_uri,
        description=description or "Supports x402 A2A agent payments",
        required=required,
        params={},
    )
```

Capability injection (always on) during bindufy:
```python
# bindu/penguin/bindufy.py
def _update_capabilities_with_x402(capabilities: AgentCapabilities | Dict[str, Any] | None) -> AgentCapabilities:
    extensions = (caps_dict.get("extensions", []) or [])
    extensions.append(get_x402_agent_extension(required=False))
    caps_dict["extensions"] = extensions
    return AgentCapabilities(**caps_dict)
```

Result: Agent cards (served at `/.well-known/agent.json`) include an extension entry with the x402 URI so clients learn the agent supports payments.

---

## Endpoint Integration and Activation Header
Files:
- `bindu/server/endpoints/agent_card.py`
- `bindu/server/endpoints/a2a_protocol.py`
Helpers:
```python
# bindu/extensions/x402/extension.py
def is_activation_requested(request: Request) -> bool:
    exts = request.headers.get("X-A2A-Extensions", "")
    return app_settings.x402.extension_uri in exts

def add_activation_header(response: Response) -> Response:
    response.headers["X-A2A-Extensions"] = app_settings.x402.extension_uri
    return response
```

Usage in endpoints (echo header when requested):
```python
# a2a_protocol.py
if x402_is_requested(request):
    resp = x402_add_header(resp)

# agent_card.py
if x402_is_requested(request):
    resp = x402_add_header(resp)
```

Example request/response:
```
GET /.well-known/agent.json
X-A2A-Extensions: https://github.com/google-a2a/a2a-x402/v0.1

HTTP/200 OK
X-A2A-Extensions: https://github.com/google-a2a/a2a-x402/v0.1
...
```

---

## Payment Flow and Metadata Contract
All x402 task coordination lives in task metadata keys under `app_settings.x402.*`.

Metadata keys:
- Status: `x402.payment.status` ∈ {payment-required, payment-submitted, payment-verified, payment-completed, payment-failed}
- Required: `x402.payment.required` – an object describing payment requirements (usually includes `accepts: [PaymentRequirements, ...]`)
- Payload: `x402.payment.payload` – a submitted `PaymentPayload` (signed/approved by payer)
- Receipts: `x402.payment.receipts` – settlement receipts array
- Error: `x402.payment.error` – reason string when failed

Important: The task state machine remains aligned with A2A hybrid pattern. Payment states are recorded in metadata while the task’s A2A state is set independently (e.g., `input-required`, `completed`).

---

## Worker Lifecycle Integration (verify and settle)
File: `bindu/server/workers/manifest_worker.py`

Pre-processing (detect submission prior to entering `working`):
```python
latest_msg = (task.get("history") or [])[-1] if task.get("history") else None
latest_meta = (latest_msg or {}).get("metadata") or {}

if latest_meta.get(meta_status_key) == status_submitted and latest_meta.get(meta_payload_key):
    payload_data = latest_meta[meta_payload_key]
    required_data = task.get("metadata", {}).get(meta_required_key) or latest_meta.get(meta_required_key)

    payment_payload_obj = self._parse_payment_payload(payload_data)
    payment_requirements_obj = self._select_requirement_from_required(required_data, payment_payload_obj)

    facilitator_client = FacilitatorClient()
    verify_response = await facilitator_client.verify(payment_payload_obj, payment_requirements_obj)
    if not verify_response.is_valid:
        # mark metadata failed, keep state input-required and return
    else:
        # mark metadata verified; continue execution as usual
```

Execution path:
1) If not in payment-submitted flow → task transitions to `working` and proceeds to run the agent.
2) After agent returns a result, if this is a paid flow, `settle(...)` is invoked before completing the task so receipts can be recorded:
```python
settle_response = await facilitator_client.settle(payment_payload_obj, payment_requirements_obj)
if settle_response.success:
    metadata = build_payment_completed_metadata(settle_response.model_dump(...))
    await self._handle_terminal_state(task, results, state="completed", additional_metadata=metadata)
else:
    # attach failed metadata, keep task in input-required with error message
```

State policy:
- Verification failure → `state = input-required`, `metadata.status = payment-failed`
- Verification success → `metadata.status = payment-verified`, continue
- Settlement success → `state = completed`, `metadata.status = payment-completed`, `metadata.receipts = [...]`
- Settlement failure/exception → `state = input-required`, `metadata.status = payment-failed`

Structured “payment-required” responses from the agent are also recognized:
```python
# When agent returns a dict with state == app_settings.x402.status_required OR includes "required"
metadata = build_payment_required_metadata(required)
await self.storage.update_task(task_id, state="input-required", metadata=metadata)
```

---

## Merchant Helper for PaymentRequirements
File: `bindu/extensions/x402/merchant.py`

This helper converts human-friendly price inputs into atomic amounts and packages an x402 `PaymentRequirements`:
```python
from x402.common import process_price_to_atomic_amount
from x402.types import PaymentRequirements, Price, SupportedNetworks

def create_payment_requirements(price: Price, pay_to_address: str, resource: str, network: str = "base", ...):
    max_amount_required, asset_address, eip712_domain = process_price_to_atomic_amount(price, network)
    return PaymentRequirements(
        scheme=scheme,
        network=SupportedNetworks(network),
        asset=asset_address,
        pay_to=pay_to_address,
        max_amount_required=max_amount_required,
        resource=resource,
        description=description,
        mime_type=mime_type,
        max_timeout_seconds=max_timeout_seconds,
        output_schema=output_schema,
        extra=eip712_domain,
        **kwargs,
    )
```

Example invocation:
```python
req = create_payment_requirements(
  price="$1.00",            # or token amount definition
  pay_to_address="0xmerchant",
  resource="/compute/plan/123",
  network="base",
  description="Compute credits for plan 123",
  mime_type="application/json",
  scheme="exact",
  max_timeout_seconds=600,
  output_schema={"type": "object"},
)
```

---

## Utilities for Task Metadata
File: `bindu/extensions/x402/utils.py`

Helpers centralize metadata updates:
```python
build_payment_required_metadata(required) -> {
  status_key: payment-required,
  required_key: required
}

build_payment_verified_metadata() -> {
  status_key: payment-verified
}

build_payment_completed_metadata(receipt) -> {
  status_key: payment-completed,
  receipts_key: [receipt]
}

build_payment_failed_metadata(error, receipt=None) -> {
  status_key: payment-failed,
  error_key: error,
  # optionally receipts_key: [receipt]
}
```

---

## End-to-End Examples

### 1) Agent asks for payment (payment-required)
Agent returns a structured object (either directly or via the worker’s structured response path):
```json
{
  "state": "payment-required",
  "required": {
    "accepts": [
      {
        "scheme": "exact",
        "network": "base",
        "asset": "0x...asset",
        "pay_to": "0xmerchant",
        "max_amount_required": 12345,
        "resource": "/compute/plan/123",
        "mime_type": "application/json",
        "extra": { "domain": "eip712" }
      }
    ],
    "prompt": "Please authorize $1.00 on Base to continue."
  }
}
```
The worker sets task state to `input-required` and attaches metadata:
```json
{
  "x402.payment.status": "payment-required",
  "x402.payment.required": { ... as above ... }
}
```

### 2) Client submits payment (payment-submitted)
Client includes x402 payload on the next user message:
```json
{
  "metadata": {
    "x402.payment.status": "payment-submitted",
    "x402.payment.payload": { /* PaymentPayload */ }
  }
}
```
The worker:
1. Parses payload and selects a matching requirement from `required.accepts`.
2. Calls `FacilitatorClient.verify(payload, requirement)`.
   - If invalid → state `input-required`, metadata `payment-failed`.
   - If valid → metadata `payment-verified`; proceed to run agent.
3. After agent result, calls `FacilitatorClient.settle(...)`.
   - On success → state `completed`; metadata `payment-completed` + `receipts`.
   - On failure → state `input-required`; metadata `payment-failed` + error message.

### 3) Failure scenarios
- Verification failure:
  ```json
  { "x402.payment.status": "payment-failed", "x402.payment.error": "verification_failed" }
  ```
  Task remains `input-required`.

- Settlement failure:
  ```json
  { "x402.payment.status": "payment-failed", "x402.payment.error": "settlement_failed", "x402.payment.receipts": [{...}] }
  ```
  Task remains `input-required`.

---

## Running Tests and Markers
All x402-related tests are marked `@pytest.mark.x402`. Run:
```
source .venv/bin/activate
pytest -q -m x402
```

Coverage includes:
- Extension and activation header
- Metadata utilities
- Merchant requirements builder
- Worker verify/settle success/failure paths (FacilitatorClient mocked)
- Endpoint header echo on agent card and A2A run endpoints

---

## References
- x402 Protocol: https://www.x402.org
- This repo (branch):
  - `bindu/extensions/x402/extension.py`, `utils.py`, `merchant.py`
  - `bindu/server/workers/manifest_worker.py`
  - `bindu/server/endpoints/a2a_protocol.py`, `agent_card.py`
  - `bindu/penguin/bindufy.py`
  - `bindu/settings.py` (X402Settings)
- Related concepts: A2A Protocol and extension negotiation via `X-A2A-Extensions`
