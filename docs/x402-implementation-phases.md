# x402 Payment Flow Implementation - Phased Approach

**Status:** 🚧 In Progress  
**Last Updated:** 2025-10-26  
**Goal:** Implement proper x402 payment flow following official A2A x402 specification

---

## 📋 Overview

This document tracks the phased implementation of x402 payment integration in Bindu. We're following the official [A2A x402 specification](https://github.com/google-agentic-commerce/a2a-x402) to enable agents to monetize their services through on-chain payments.

### Current State Analysis

**What Works:**
- ✅ Agent configuration with `execution_cost` (amount, token, network, pay_to_address)
- ✅ X402AgentExtension creates PaymentRequirements
- ✅ Agent card advertises x402 capability
- ✅ Payment verification logic exists in manifest_worker (lines 134-204)

**What Needs Fixing:**
- ❌ Payment check happens too late (during agent execution)
- ❌ First request should return `payment-required` immediately
- ❌ Flow doesn't match official spec

### Official x402 Flow (Target)

```
Request 1: "hello" (no payment)
  ↓
  Server checks: Does agent require payment?
  ↓
  Response: Task with state=input-required
            metadata.x402.payment.status = "payment-required"
            metadata.x402.payment.required = { accepts: [...] }
  ↓
  Client signs payment with wallet
  ↓
Request 2: "hello" (with payment payload)
  ↓
  Server verifies payment
  ↓
  Agent executes
  ↓
  Server settles payment
  ↓
  Response: Task with state=completed
            artifacts = [agent output]
            metadata.x402.payment.status = "payment-completed"
```

---

## 🎯 PHASE 1: Payment-Required Detection

**Status:** ✅ COMPLETED (2025-10-26)  
**Goal:** First request returns `payment-required` without executing agent  
**Risk Level:** 🟢 Low (no impact on existing functionality)

### Changes Required

#### 1. Update `MessageHandlers` Class

**File:** `bindu/server/handlers/message_handlers.py`

**Change 1.1:** Add manifest parameter
```python
@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""
    
    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None  # ADD THIS
    workers: list[Any] | None = None
    context_id_parser: Any = None
```

**Change 1.2:** Add payment-required check in `send_message()`
```python
async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
    """Send a message using the A2A protocol."""
    message = request["params"]["message"]
    context_id = self.context_id_parser(message.get("context_id"))
    
    # NEW: Check if agent requires payment and no payment provided
    message_metadata = message.get("metadata", {})
    has_payment_payload = message_metadata.get("x402.payment.payload") is not None
    
    if self.manifest and not has_payment_payload:
        # Check if agent has execution_cost configured
        x402_ext = getattr(self.manifest, 'x402_extension', None)
        if x402_ext:
            # Agent requires payment - return payment-required immediately
            task: Task = await self.storage.submit_task(context_id, message)
            
            # Create payment requirements
            payment_req = x402_ext.create_payment_requirements(
                resource=f"/agent/{self.manifest.name}",
                description=f"Payment required to use {self.manifest.name}",
            )
            
            # Build payment-required metadata
            from bindu.extensions.x402.utils import build_payment_required_metadata
            payment_metadata = build_payment_required_metadata({
                "x402Version": 1,
                "accepts": [payment_req.model_dump(by_alias=True)]
            })
            
            # Create agent message explaining payment requirement
            from bindu.utils.worker_utils import MessageConverter
            agent_messages = MessageConverter.to_protocol_messages(
                f"Payment required: {x402_ext.amount_usd:.2f} USD ({x402_ext.token} on {x402_ext.network})",
                task["id"],
                context_id
            )
            
            # Update task to input-required with payment metadata
            await self.storage.update_task(
                task["id"],
                state="input-required",
                new_messages=agent_messages,
                metadata=payment_metadata
            )
            
            # Return task WITHOUT calling scheduler.run_task()
            task = await self.storage.load_task(task["id"])
            return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)
    
    # Normal flow (no payment required OR payment already provided)
    task: Task = await self.storage.submit_task(context_id, message)
    
    scheduler_params: TaskSendParams = TaskSendParams(
        task_id=task["id"],
        context_id=context_id,
        message=message,
    )
    
    # Add optional configuration parameters
    config = request["params"].get("configuration", {})
    if history_length := config.get("history_length"):
        scheduler_params["history_length"] = history_length
    
    await self.scheduler.run_task(scheduler_params)
    return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)
```

#### 2. Update Server Initialization

**File:** `bindu/server/task_manager.py` (or wherever MessageHandlers is instantiated)

**Change 2.1:** Pass manifest to MessageHandlers
```python
# Before:
self.message_handlers = MessageHandlers(
    scheduler=self.scheduler,
    storage=self.storage,
    workers=self.workers,
    context_id_parser=self.context_id_parser,
)

# After:
self.message_handlers = MessageHandlers(
    scheduler=self.scheduler,
    storage=self.storage,
    manifest=self.manifest,  # ADD THIS
    workers=self.workers,
    context_id_parser=self.context_id_parser,
)
```

### Testing Phase 1

**Test Case 1:** Agent with execution_cost
```bash
# Start agent with execution_cost configured
python examples/agno_example.py

# Send request without payment
curl -X POST http://localhost:3773/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "hello"}]
      }
    }
  }'

# Expected Response:
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "kind": "task",
    "id": "...",
    "status": {
      "state": "input-required",
      "message": {
        "metadata": {
          "x402.payment.status": "payment-required",
          "x402.payment.required": {
            "x402Version": 1,
            "accepts": [{
              "scheme": "exact",
              "network": "base-sepolia",
              "asset": "0x...",
              "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
              "maxAmountRequired": "10000",
              ...
            }]
          }
        }
      }
    }
  }
}
```

**Test Case 2:** Agent without execution_cost
```bash
# Agent should work normally (no payment required)
# Should execute immediately and return completed task
```

### Success Criteria ✅ ALL COMPLETED

- ✅ Agent with `execution_cost` returns `payment-required` on first request
- ✅ Agent WITHOUT `execution_cost` works normally
- ✅ No agent execution happens during payment-required response
- ✅ Task state is `input-required`
- ✅ Metadata contains proper `x402.payment.required` structure
- ✅ Utility function created in `bindu/utils/capabilities.py`
- ✅ Code refactored with `_handle_payment_required()` method
- ✅ Uses settings instead of hardcoded values
- ✅ Comprehensive unit tests added

### Implementation Summary

**Files Modified:**
1. `bindu/utils/capabilities.py` - Added `get_x402_extension_from_capabilities()`
2. `bindu/utils/__init__.py` - Exported utility function
3. `bindu/server/handlers/message_handlers.py` - Added `_handle_payment_required()` method
4. `bindu/extensions/x402/merchant.py` - Fixed `SupportedNetworks` TypeError
5. `tests/unit/test_capabilities_utils.py` - Unit tests for utility function

**Documentation:**
- `docs/x402-phase1-implementation.md` - Complete implementation guide

---

## 🔐 PHASE 2: Payment Verification & Execution

**Status:** ⏳ Not Started (depends on Phase 1)  
**Goal:** Second request with payment gets verified and executes  
**Risk Level:** 🟡 Medium (modifies execution flow)

### Current State

The verification logic already exists in `manifest_worker.py` (lines 134-204):
- ✅ Detects payment submission via message metadata
- ✅ Parses PaymentPayload
- ✅ Calls FacilitatorClient.verify()
- ✅ Handles verification failures
- ✅ Marks payment as verified

**What's Missing:**
- Settlement after successful execution (lines 301-359 have this, but needs testing)
- Proper error handling for settlement failures

### Changes Required

#### 1. Verify Existing Logic Works

**File:** `bindu/server/workers/manifest_worker.py`

**Review lines 134-204:** Payment verification logic
```python
# This code already exists - just needs testing
if latest_meta.get(app_settings.x402.meta_status_key) == app_settings.x402.status_submitted:
    # Parse payment payload
    payment_payload_obj = self._parse_payment_payload(payload_data)
    payment_requirements_obj = self._select_requirement_from_required(...)
    
    # Verify with facilitator
    verify_response = await facilitator_client.verify(...)
    
    if not verify_response.is_valid:
        # Return payment-failed
        ...
    else:
        # Mark verified, continue execution
        is_paid_flow = True
```

**Review lines 301-359:** Settlement logic
```python
# This code already exists - just needs testing
if is_paid_flow and payment_payload_obj and payment_requirements_obj:
    settle_response = await facilitator_client.settle(...)
    
    if settle_response.success:
        # Mark payment-completed
        md = build_payment_completed_metadata(...)
    else:
        # Mark payment-failed
        md = build_payment_failed_metadata(...)
```

#### 2. Add Missing Helper Methods

**File:** `bindu/server/workers/manifest_worker.py`

**Add if not exists:**
```python
def _parse_payment_payload(self, payload_data: dict) -> PaymentPayload:
    """Parse payment payload from message metadata."""
    from x402.types import PaymentPayload
    return PaymentPayload(**payload_data)

def _select_requirement_from_required(
    self, required_data: dict, payment_payload: PaymentPayload
) -> PaymentRequirements:
    """Select matching payment requirement from accepts array."""
    from x402.types import PaymentRequirements
    
    accepts = required_data.get("accepts", [])
    if not accepts:
        raise ValueError("No payment requirements in required data")
    
    # For now, select first requirement
    # TODO: Match based on payment_payload.resource or other criteria
    return PaymentRequirements(**accepts[0])
```

### Testing Phase 2

**Test Case 1:** Complete payment flow
```bash
# Step 1: Get payment requirements (from Phase 1)
TASK_ID=$(curl -X POST http://localhost:3773/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "hello"}]
      }
    }
  }' | jq -r '.result.id')

# Step 2: Sign payment (using wallet/signing service)
# This creates PaymentPayload with signature

# Step 3: Submit payment
curl -X POST http://localhost:3773/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "hello"}],
        "metadata": {
          "x402.payment.status": "payment-submitted",
          "x402.payment.payload": {
            "resource": "/agent/my-agent",
            "signature": "0x...",
            ...
          }
        }
      }
    }
  }'

# Expected Response:
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "kind": "task",
    "status": {
      "state": "completed",
      "message": { /* agent response */ }
    },
    "artifacts": [{ /* agent output */ }],
    "metadata": {
      "x402.payment.status": "payment-completed",
      "x402.payment.receipts": [{
        "transactionHash": "0x...",
        "blockNumber": 12345,
        ...
      }]
    }
  }
}
```

**Test Case 2:** Invalid payment
```bash
# Submit invalid payment payload
# Expected: Task returns to input-required with payment-failed
```

**Test Case 3:** Settlement failure
```bash
# Mock facilitator to fail settlement
# Expected: Task returns to input-required with payment-failed
```

### Success Criteria

- ✅ Payment verification works correctly
- ✅ Valid payments allow agent execution
- ✅ Invalid payments return `payment-failed` error
- ✅ Settlement happens after successful execution
- ✅ Settlement receipts are stored in metadata
- ✅ Settlement failures are handled gracefully

### Rollback Plan

If Phase 2 fails:
1. Keep Phase 1 (agents still advertise payment requirements)
2. Disable payment verification temporarily
3. Investigate and fix issues before re-enabling

---

## ✨ PHASE 3: Optimization & Polish

**Status:** ⏳ Not Started (depends on Phase 2)  
**Goal:** Clean code, better architecture, comprehensive tests  
**Risk Level:** 🟢 Low (refactoring only)

### Potential Improvements

#### 1. Extract PaymentManager (Optional)

Following the pattern from `push_notification_manager.py`:

**File:** `bindu/server/payment_manager.py` (NEW)

```python
"""Payment management for x402 protocol integration."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from x402.facilitator import FacilitatorClient
from x402.types import PaymentPayload, PaymentRequirements

from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
    build_payment_required_metadata,
    build_payment_verified_metadata,
)
from bindu.settings import app_settings


@dataclass
class PaymentManager:
    """Manages x402 payment verification and settlement."""
    
    async def check_payment_required(
        self, manifest: Any, message_metadata: dict
    ) -> Optional[dict]:
        """Check if payment is required for this request.
        
        Returns payment-required metadata if needed, None otherwise.
        """
        has_payment = message_metadata.get("x402.payment.payload") is not None
        if has_payment:
            return None
        
        x402_ext = getattr(manifest, 'x402_extension', None)
        if not x402_ext:
            return None
        
        # Create payment requirements
        payment_req = x402_ext.create_payment_requirements(
            resource=f"/agent/{manifest.name}",
            description=f"Payment required to use {manifest.name}",
        )
        
        return build_payment_required_metadata({
            "x402Version": 1,
            "accepts": [payment_req.model_dump(by_alias=True)]
        })
    
    async def verify_payment(
        self, payment_payload: PaymentPayload, payment_requirements: PaymentRequirements
    ) -> tuple[bool, Optional[str]]:
        """Verify payment with facilitator.
        
        Returns (is_valid, error_reason).
        """
        facilitator = FacilitatorClient()
        verify_response = await facilitator.verify(payment_payload, payment_requirements)
        
        if not verify_response.is_valid:
            return False, verify_response.invalid_reason or "verification_failed"
        
        return True, None
    
    async def settle_payment(
        self, payment_payload: PaymentPayload, payment_requirements: PaymentRequirements
    ) -> tuple[bool, dict]:
        """Settle payment on-chain.
        
        Returns (success, metadata).
        """
        facilitator = FacilitatorClient()
        settle_response = await facilitator.settle(payment_payload, payment_requirements)
        
        if settle_response.success:
            return True, build_payment_completed_metadata(
                settle_response.model_dump(by_alias=True)
            )
        else:
            return False, build_payment_failed_metadata(
                settle_response.error_reason or "settlement_failed",
                settle_response.model_dump(by_alias=True)
            )
```

**Usage in manifest_worker.py:**
```python
@dataclass
class ManifestWorker(Worker):
    manifest: AgentManifest
    payment_manager: PaymentManager = field(default_factory=PaymentManager)
    
    async def run_task(self, params: TaskSendParams) -> None:
        # Use payment_manager instead of inline logic
        is_valid, error = await self.payment_manager.verify_payment(...)
```

#### 2. Comprehensive Testing

**File:** `tests/integration/test_x402_payment_flow.py` (NEW)

```python
"""Integration tests for x402 payment flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.x402
async def test_payment_required_response():
    """Test that agent with execution_cost returns payment-required."""
    # Setup agent with execution_cost
    # Send message without payment
    # Assert response has payment-required metadata
    pass

@pytest.mark.x402
async def test_payment_verification_success():
    """Test successful payment verification and execution."""
    # Setup agent with execution_cost
    # Get payment requirements
    # Submit valid payment
    # Assert task completes with payment-completed
    pass

@pytest.mark.x402
async def test_payment_verification_failure():
    """Test payment verification failure."""
    # Submit invalid payment
    # Assert task returns to input-required with payment-failed
    pass

@pytest.mark.x402
async def test_payment_settlement_failure():
    """Test payment settlement failure."""
    # Mock facilitator to fail settlement
    # Assert task returns to input-required with payment-failed
    pass

@pytest.mark.x402
async def test_non_paid_agent_normal_flow():
    """Test that agents without execution_cost work normally."""
    # Setup agent without execution_cost
    # Send message
    # Assert normal execution (no payment required)
    pass
```

#### 3. Update Documentation

**File:** `docs/x402-plan.md`

Update with actual implementation details:
- Remove outdated references
- Add code examples from actual implementation
- Document the two-request flow clearly
- Add troubleshooting section

**File:** `README.md`

Add x402 payment example:
```markdown
## Monetizing Your Agent with x402

Enable payments for your agent by adding `execution_cost` to your config:

```json
{
  "name": "my-paid-agent",
  "execution_cost": {
    "amount": "1000000",
    "token": "USDC",
    "network": "base-sepolia",
    "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
  }
}
```

Your agent will now require payment before execution. Clients will receive
payment requirements and can submit signed payments to use your agent.
```

### Success Criteria

- ✅ Code is well-organized and maintainable
- ✅ All tests pass with >80% coverage
- ✅ Documentation is complete and accurate
- ✅ No regressions in existing functionality

---

## 📊 Progress Tracking

### Phase 1: Payment-Required Detection ✅ COMPLETE
- [x] Update MessageHandlers class
- [x] Update server initialization
- [x] Create utility function in capabilities.py
- [x] Refactor with _handle_payment_required() method
- [x] Fix SupportedNetworks TypeError
- [x] Use settings instead of hardcoded values
- [x] Add unit tests
- [x] Test with paid agent
- [x] Test with non-paid agent
- [x] Code review
- [x] Documentation complete

### Phase 2: Payment Verification & Execution
- [ ] Verify existing verification logic
- [ ] Add missing helper methods
- [ ] Test complete payment flow
- [ ] Test invalid payment handling
- [ ] Test settlement failures
- [ ] Code review

### Phase 3: Optimization & Polish
- [ ] Extract PaymentManager (optional)
- [ ] Write comprehensive tests
- [ ] Update documentation
- [ ] Final code review
- [ ] Merge to main

---

## 🔗 References

- [A2A x402 Specification](https://github.com/google-agentic-commerce/a2a-x402/blob/main/spec/v0.1/spec.md)
- [x402 Python Library](https://github.com/google-agentic-commerce/a2a-x402/blob/main/python/x402_a2a/README.md)
- [x402 Protocol Documentation](https://x402.gitbook.io/x402)
- [Current Implementation Plan](./x402-plan.md)

---

## 📝 Notes

### Design Decisions

1. **Why check payment in message_handlers?**
   - Follows official spec: payment-required happens BEFORE execution
   - Cleaner separation: negotiation at handler, verification at worker
   - Better performance: no unnecessary agent initialization

2. **Why keep verification in manifest_worker?**
   - Verification needs to happen just before execution
   - Worker has access to task history and context
   - Existing code is well-tested

3. **Why phased approach?**
   - Lower risk: each phase is independently testable
   - Faster feedback: can deploy Phase 1 while working on Phase 2
   - Easier rollback: can revert individual phases

### Known Issues

- [ ] Need to handle task correlation for payment submission (same task vs new task)
- [ ] Need to decide on payment requirement selection strategy (multiple accepts)
- [ ] Need to add timeout handling for payment submission

### Future Enhancements

- [ ] Support for multiple payment methods (accepts array)
- [ ] Dynamic pricing based on request parameters
- [ ] Payment history and analytics
- [ ] Refund mechanism for failed executions
