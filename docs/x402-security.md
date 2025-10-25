# x402 Payment Security Guide

## Overview

This document outlines the security measures, known risks, and best practices for x402 payment integration in Bindu.

---

## Security Measures Implemented

### 1. **Comprehensive Payment Validation**

All payment submissions undergo multi-layer validation before acceptance:

#### **Amount Validation**
- Verifies `authorization.value >= maxAmountRequired`
- Prevents underpayment attacks
- Logs all amount mismatches

#### **Pay-To Address Validation**
- Ensures payment goes to merchant's address
- Case-insensitive comparison for Ethereum addresses
- Prevents payment redirection attacks

#### **Scheme & Network Matching**
- Validates payment uses correct blockchain network
- Ensures payment scheme matches requirements
- Prevents cross-chain confusion attacks

### 2. **Nonce Tracking (Double-Spend Prevention)**

**Implementation**: In-memory `NonceTracker` with TTL-based cleanup

**Protection Against**:
- Same payment used for multiple tasks
- Replay attacks with old signatures
- Concurrent payment submissions with same nonce

**How It Works**:
```python
# Before verification
if _nonce_tracker.is_nonce_used(network, nonce):
    reject_payment("nonce_already_used")

# After successful validation
_nonce_tracker.mark_nonce_used(network, nonce, ttl=timeout+300)
```

**TTL**: `maxTimeoutSeconds + 5 minutes` buffer

**Thread-Safe**: Uses locks for concurrent access

### 3. **Timeout Validation**

**Implementation**: Timestamp-based expiration checking

**Protection Against**:
- Expired payment submissions
- Stale authorization reuse
- Replay attacks with old signatures

**How It Works**:
```python
# Store timestamp when payment required
metadata["x402.payment.required_timestamp"] = time.time()

# Validate on payment submission
elapsed_time = current_time - required_timestamp
if elapsed_time > max_timeout_seconds:
    reject_payment("timeout_exceeded")
```

**Enforcement**: Payments rejected if submitted after `maxTimeoutSeconds` from requirement

### 4. **Settlement Retry with Exponential Backoff**

**Implementation**: Automatic retry mechanism for transient failures

**Features**:
- **Max Retries**: 3 attempts
- **Exponential Backoff**: 2s, 4s, 8s between attempts
- **Idempotency**: Uses same nonce for all retries
- **Metadata Tracking**: Records attempt count and timestamps

**How It Works**:
```python
max_retries = 3
for attempt in range(max_retries):
    settle_response = await facilitator.settle(payload, requirements)
    if settle_response.success:
        break
    backoff = 2 ** attempt
    await asyncio.sleep(backoff)
```

**Benefits**:
- Handles transient network failures
- Improves payment success rate
- Prevents work loss on temporary issues

### 5. **Comprehensive Audit Logging**

All payment events are logged with structured data for forensics and dispute resolution:

#### **Logged Events**:
- `x402_payment_verification_started` - Payment submission detected
- `x402_payment_validation_started` - Validation process begins
- `x402_payment_validation_success` - All validations passed
- `x402_validation_failed` - Validation failure with reason
- `x402_facilitator_verify_calling` - Calling external verifier
- `x402_facilitator_verify_success` - Verification succeeded
- `x402_facilitator_verify_failed` - Verification failed
- `x402_facilitator_settle_calling` - Settlement initiated
- `x402_facilitator_settle_success` - Settlement completed (with tx_hash)
- `x402_facilitator_settle_failed` - Settlement failed
- `x402_settlement_retry_scheduled` - Retry scheduled with backoff
- `x402_facilitator_settle_retry` - Retry attempt initiated
- `x402_facilitator_settle_success_after_retry` - Settlement succeeded after retry
- `x402_settlement_max_retries_exceeded` - All retries exhausted
- `x402_payment_timeout_exceeded` - Payment expired
- `x402_payment_verification_exception` - Unexpected error
- `x402_facilitator_settle_exception` - Settlement error
- `x402_nonce_marked_used` - Nonce registered

#### **Log Data Includes**:
- Task ID and Context ID
- Network and scheme
- Amount and addresses
- Nonce values
- Transaction hashes (on settlement)
- Error reasons and types
- Timestamps

---

## Known Security Risks

### 1. **Verify vs Settle Timing Gap** ⚠️⚠️⚠️

**Risk**: Payment valid at `/verify` time but invalid at `/settle` time

**Attack Vectors**:
1. **Insufficient Funds**: Client withdraws funds between verify and settle
2. **Double-Spend**: Same nonce submitted to multiple merchants
3. **Race Condition**: Balance sufficient for one payment but not both

**Source**: [Circle Gateway Issue #447](https://github.com/coinbase/x402/issues/447)

**Quote**:
> "We view trusting the /verify call as a security risk. Because it does not require the facilitator to apply the EIP-3009 authorization onchain, a malicious buyer could present EIP-3009 authorizations that are valid at the time of /verify but not at time of /settle."

**Current Mitigation**:
- Nonce tracking prevents same nonce reuse within Bindu instance
- Comprehensive logging for dispute resolution
- Task remains open on settlement failure (client can retry)

**Recommended Mitigation** (Future):
- Add configuration: `X402_TRUST_VERIFY=false`
- When false: Only start work after `/settle` completes
- Trade-off: Slower response time vs guaranteed payment

### 2. **In-Memory Nonce Storage**

**Risk**: Nonce tracker resets on server restart

**Impact**: 
- Same nonce could be reused after restart
- Window of vulnerability during restart

**Mitigation** (Current):
- TTL-based cleanup limits exposure window
- Nonces expire after timeout period

**Mitigation** (Future - Phase 2)**:
- Persistent storage (Redis/PostgreSQL)
- Survives server restarts
- Shared across multiple instances

### 3. **No Cross-Instance Protection**

**Risk**: Multiple Bindu instances don't share nonce state

**Impact**: Same nonce could be used on different instances

**Mitigation** (Future):
- Centralized nonce storage (Redis)
- Distributed lock for nonce checks

### 4. **Settlement Failure Handling** ✅ MITIGATED

**Risk**: Agent completes work but payment settlement fails

**Current Mitigation** (Phase 2 - Implemented):
- ✅ Automatic settlement retry (3 attempts)
- ✅ Exponential backoff (2s, 4s, 8s)
- ✅ Idempotency via nonce reuse
- ✅ Metadata tracking of attempts
- ✅ Detailed logging of retry attempts

**Behavior**:
- First failure: Retry after 2 seconds
- Second failure: Retry after 4 seconds
- Third failure: Retry after 8 seconds
- All retries failed: Task kept in `input-required` with error

**Impact Reduction**: Significantly improved payment success rate for transient failures

---

## Security Best Practices

### For Merchants (Agent Operators)

1. **Monitor Payment Logs**
   ```bash
   # Watch for failed verifications
   grep "x402_validation_failed" logs/bindu_server.log
   
   # Monitor settlement failures
   grep "x402_facilitator_settle_failed" logs/bindu_server.log
   ```

2. **Set Appropriate Timeouts**
   - Use `maxTimeoutSeconds` based on service complexity
   - Shorter timeouts reduce replay attack window
   - Typical: 300-600 seconds

3. **Validate Pay-To Address**
   - Always set correct merchant address in requirements
   - Use environment variable: `X402_PAY_TO`
   - Never hardcode addresses

4. **Review Nonce Tracker Metrics**
   - Monitor nonce rejection rate
   - High rejection rate may indicate attack
   - Investigate repeated nonce reuse attempts

### For Clients (Payment Senders)

1. **Use Unique Nonces**
   - Generate cryptographically random nonces
   - Never reuse nonces across payments
   - EIP-3009 requires unique nonces per authorization

2. **Set Appropriate Validity Windows**
   - `validAfter`: Current time or slightly in future
   - `validBefore`: Current time + reasonable buffer
   - Avoid very long validity windows

3. **Monitor Payment Status**
   - Check task metadata for payment state
   - Retry on verification failures (with new nonce)
   - Don't retry on settlement failures (payment may be processing)

---

## Validation Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Payment Submission                                          │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Parse Payment Payload                               │
│  - Extract authorization details                             │
│  - Log payment_verification_started                          │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Select & Validate Requirement                       │
│  ✓ Scheme matches                                            │
│  ✓ Network matches                                           │
│  ✓ Amount >= maxAmountRequired                              │
│  ✓ Pay-to address matches merchant                          │
│  ✓ Nonce not already used                                   │
│  - Log validation_success or validation_failed               │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Mark Nonce as Used                                  │
│  - Store in NonceTracker with TTL                            │
│  - Log nonce_marked_used                                     │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Call Facilitator /verify                            │
│  - Cryptographic signature validation                        │
│  - Balance check                                             │
│  - On-chain nonce check                                      │
│  - Transaction simulation                                    │
│  - Log facilitator_verify_success or _failed                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Execute Agent Work                                  │
│  - Only if verification succeeded                            │
│  - Agent generates deliverable                               │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Call Facilitator /settle                            │
│  - Submit transaction on-chain                               │
│  - Wait for confirmation                                     │
│  - Log facilitator_settle_success or _failed                 │
│  - Attach tx_hash to metadata                                │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Complete Task                                       │
│  - Success: state=completed, artifacts attached              │
│  - Failure: state=input-required, error message              │
└─────────────────────────────────────────────────────────────┘
```

---

## Failure Scenarios

### Validation Failure
```json
{
  "state": "input-required",
  "metadata": {
    "x402.payment.status": "payment-failed",
    "x402.payment.error": "insufficient_amount|pay_to_address_mismatch|nonce_already_used"
  }
}
```
**Action**: Client can retry with corrected payment

### Verification Failure
```json
{
  "state": "input-required",
  "metadata": {
    "x402.payment.status": "payment-failed",
    "x402.payment.error": "verification_failed: <reason>"
  }
}
```
**Action**: Client can retry with new payment

### Settlement Failure
```json
{
  "state": "input-required",
  "metadata": {
    "x402.payment.status": "payment-failed",
    "x402.payment.error": "settlement_failed: <reason>",
    "x402.payment.receipts": [{"tx_hash": null, "error": "..."}]
  }
}
```
**Action**: Contact merchant support (work may be done but payment pending)

---

## Monitoring & Alerting

### Key Metrics to Monitor

1. **Payment Success Rate**
   ```
   successful_settlements / total_payment_attempts
   ```

2. **Nonce Rejection Rate**
   ```
   nonce_already_used_count / total_validation_attempts
   ```

3. **Verification Failure Rate**
   ```
   verify_failed_count / total_verify_attempts
   ```

4. **Settlement Failure Rate**
   ```
   settle_failed_count / total_settle_attempts
   ```

### Alert Thresholds

- **Nonce rejection rate > 5%**: Possible replay attack
- **Verification failure rate > 10%**: Client integration issues
- **Settlement failure rate > 2%**: Facilitator or network issues
- **Same address repeated failures > 3**: Potential malicious actor

---

## Incident Response

### Suspected Double-Spend Attack

1. Check logs for repeated nonce usage:
   ```bash
   grep "nonce_already_used" logs/ | grep "<nonce>"
   ```

2. Identify affected tasks and addresses

3. Review payment metadata for all instances

4. Contact facilitator if on-chain settlement occurred

### Settlement Failures

1. Check settlement logs for error details and retry attempts:
   ```bash
   grep "x402_facilitator_settle" logs/ | grep "<task_id>"
   ```

2. Review retry attempts:
   ```bash
   grep "x402_settlement_retry" logs/ | grep "<task_id>"
   ```

3. Verify facilitator service status

4. Check blockchain network status

5. Review transaction hash (if available)

6. If max retries exceeded, check metadata:
   ```json
   {
     "x402.settlement.attempts": 3,
     "x402.settlement.max_retries_exceeded": true
   }
   ```

7. Manual settlement may be required for persistent failures

### Payment Redirection

1. Check logs for `pay_to_address_mismatch`

2. Verify merchant address configuration

3. Review all payments from suspicious addresses

4. Update merchant address if compromised

---

## Future Enhancements (Roadmap)

### Phase 2 (High Priority) - ✅ COMPLETED
- [x] Timeout validation
- [x] Settlement retry with idempotency
- [ ] Persistent nonce storage (Redis) - deferred to Phase 3

### Phase 3 (Medium Priority)
- [ ] Rate limiting per address
- [ ] Cross-instance nonce coordination
- [ ] Payment analytics dashboard

### Phase 4 (Future)
- [ ] Escrow mechanism
- [ ] Dispute resolution system
- [ ] Multi-signature settlements
- [ ] Payment batching optimization

---

## References

- [x402 Protocol Specification](https://github.com/coinbase/x402)
- [EIP-3009: Transfer With Authorization](https://eips.ethereum.org/EIPS/eip-3009)
- [Circle Gateway Security Discussion](https://github.com/coinbase/x402/issues/447)
- [x402 Exact Scheme on EVM](https://github.com/coinbase/x402/blob/main/specs/schemes/exact/scheme_exact_evm.md)
- [Bindu x402 Integration Plan](./x402-plan.md)

---

## Contact

For security issues or questions:
- Review logs in `logs/bindu_server.log`
- Check task metadata for payment details
- Consult facilitator documentation for settlement issues
