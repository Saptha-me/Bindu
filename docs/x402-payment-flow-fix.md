# x402 Payment Flow Fix

## Issues Identified

### 1. **Incorrect Order of Checks**
The original logic checked for payment requirements from manifest and previous tasks BEFORE checking if payment was already submitted in the current message. This caused unnecessary lookups.

### 2. **Current Task Included in Previous Tasks Check**
When calling `list_tasks_by_context(context_id)`, the current task (just created) was included in the results. This meant `latest_task` could be the current task itself, which has no metadata yet.

### 3. **No Check for Already Verified Payment**
The logic checked if previous task required payment but didn't check if that payment was already verified. This caused the system to keep asking for payment even after it was paid.

### 4. **Task Metadata Not Updated with Verified Status**
When payment was verified, only the message metadata was updated. The task metadata wasn't updated with the verified status, so subsequent tasks couldn't detect that payment was already made.

## Fixes Applied

### Fix 1: Reordered Logic (Lines 772-810)
```python
# Step 1: Check if payment was submitted in the current message FIRST
message_metadata = message.get("metadata") or {}
payment_status = message_metadata.get(app_settings.x402.meta_status_key)

# Step 2: Determine if agent requires payment from manifest
# ... (manifest check)

# Step 3: Check previous tasks ONLY if payment not submitted
if payment_status != app_settings.x402.status_submitted:
    # ... (previous tasks check)
```

**Benefit**: Avoids unnecessary database lookups when payment is already provided.

### Fix 2: Filter Out Current Task (Lines 814-817)
```python
# Filter out the current task and find the most recent previous task
previous_tasks = [
    t for t in tasks_in_context 
    if t.get("id") != task_id
]
```

**Benefit**: Ensures we only check actual previous tasks, not the current one.

### Fix 3: Check Verified Status (Lines 828-843)
```python
# Check if previous task already has verified payment
previous_payment_status = task_metadata.get(
    app_settings.x402.meta_status_key
)

# Only inherit payment requirements if:
# 1. Previous task required payment, AND
# 2. Previous task does NOT have verified payment yet
if previous_payment_required and previous_payment_status != app_settings.x402.status_verified:
    agent_requires_payment = True
    payment_requirements_data = previous_payment_required
```

**Benefit**: Prevents re-requesting payment when it's already been verified in a previous task.

### Fix 4: Store Verified Status in Task Metadata (Lines 332-350)
```python
# If payment was verified, store the verified status in task metadata
if payment_status == app_settings.x402.status_verified:
    task_metadata_update[app_settings.x402.meta_status_key] = payment_status
    task_metadata_update["x402.payment.verified_timestamp"] = time.time()
```

**Benefit**: Subsequent tasks can check if payment was already verified.

## Flow Examples

### Example 1: First Call (No Payment)
```
User sends: "provide sunset quote"
↓
1. Check message metadata → No payment status
2. Check manifest → Requires payment (execution_cost configured)
3. Skip previous tasks check (no payment submitted)
4. Return payment requirements
↓
Response includes: metadata.x402.payment.required
```

### Example 2: Second Call (With Payment) - SAME CONTEXT
```
User sends: "instagram" with payment metadata
contextId: SAME as first call
↓
1. Check message metadata → payment_status = "payment-submitted"
2. Check manifest → Requires payment
3. SKIP previous tasks check (payment already submitted)
4. Validate payment
5. Mark as verified in message metadata
6. Store verified status in task metadata
↓
Response: Task proceeds with verified payment
```

### Example 3: Third Call (Same Context, No Payment)
```
User sends: "another query" without payment
contextId: SAME as previous calls
↓
1. Check message metadata → No payment status
2. Check manifest → Requires payment
3. Check previous tasks → Find task with verified payment
4. previous_payment_status = "payment-verified"
5. SKIP inheriting payment requirements (already verified)
6. Return None (no payment required)
↓
Response: Task proceeds without payment requirement
```

### Example 4: Different Context
```
User sends: "hello" with different contextId
contextId: DIFFERENT from previous calls
↓
1. Check message metadata → No payment status
2. Check manifest → Requires payment
3. Check previous tasks → No previous tasks in this context
4. Return payment requirements
↓
Response includes: metadata.x402.payment.required
```

## Key Improvements

1. **Performance**: Payment status checked first, avoiding unnecessary DB queries
2. **Correctness**: Current task excluded from previous tasks check
3. **User Experience**: Payment not re-requested after verification
4. **Data Integrity**: Verified status persisted in task metadata
5. **Multi-turn Support**: Subsequent messages in same context don't require re-payment

## Testing Recommendations

1. **Test Case 1**: First message without payment → Should return payment requirements
2. **Test Case 2**: Second message with valid payment → Should verify and proceed
3. **Test Case 3**: Third message in same context without payment → Should proceed without re-requesting
4. **Test Case 4**: Invalid payment → Should raise ValueError
5. **Test Case 5**: Different context → Should request payment again
6. **Test Case 6**: Previous task with unverified payment → Should inherit requirements
