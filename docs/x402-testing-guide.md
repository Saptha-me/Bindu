# x402 Payment Testing Guide

Complete guide for testing x402 payment flow with Bindu agents.

## Prerequisites

Install wallet utilities:

```bash
pip install -r examples/requirements-wallet.txt
```

## Quick Start

### Step 1: Generate Test Wallet

```bash
python examples/generate_test_wallet.py
```

**Output:**
```
================================================================================
GENERATING TEST WALLET
================================================================================

✅ Test wallet generated successfully!

Address:     0x1234567890abcdef1234567890abcdef12345678
Private Key: 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

⚠️  IMPORTANT:
   - This is a TEST wallet for development only
   - NEVER use this wallet for real funds
   - Store the private key securely
   - Use --private-key flag to sign payments
```

**Save these values!** You'll need them for the next steps.

### Step 2: Send First Request (Get Payment Requirements)

```bash
curl --location 'http://localhost:8030/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <>' \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "provide sunset quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440038",
            "contextId": "550e8400-e29b-41d4-a716-446655440038",
            "taskId": "550e8400-e29b-41d4-a716-446655440078"
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

**Expected Response:**
```json
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440024",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440078",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "input-required",
            "timestamp": "2025-10-26T14:47:52.183416+00:00"
        },
        "metadata": {
            "x402.payment.status": "payment-required",
            "x402.payment.required": {
                "x402Version": 1,
                "accepts": [...]
            }
        }
    }
}
```

✅ **Phase 1 Complete:** Agent returned `payment-required`

### Step 3: Generate Signed Payment Request

Use the private key from Step 1 and the IDs from Step 2:

```bash
python examples/generate_test_wallet.py --generate-request \
    --private-key 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890 \
    --context-id "550e8400-e29b-41d4-a716-446655440038" \
    --task-id "550e8400-e29b-41d4-a716-446655440078" \
    --message "provide sunset quote"
```

**Output:**
```
================================================================================
CREATING SIGNED PAYMENT PAYLOAD
================================================================================

✅ Payment payload signed successfully!

Payment Payload:
{
  "resource": "/agent/first Agent",
  "scheme": "exact",
  "network": "base-sepolia",
  "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "amount": "10000000000",
  "timestamp": "2025-10-26T15:00:00.000000+00:00",
  "payer": "0x1234567890abcdef1234567890abcdef12345678",
  "signature": "0x..."
}

================================================================================
COMPLETE CURL REQUEST
================================================================================

curl --location 'http://localhost:8030/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <>' \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "provide sunset quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440039",
            "contextId": "550e8400-e29b-41d4-a716-446655440038",
            "taskId": "550e8400-e29b-41d4-a716-446655440078",
            "metadata": {
                "x402.payment.status": "payment-submitted",
                "x402.payment.payload": {
                    "resource": "/agent/first Agent",
                    "scheme": "exact",
                    "network": "base-sepolia",
                    "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                    "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    "amount": "10000000000",
                    "timestamp": "2025-10-26T15:00:00.000000+00:00",
                    "payer": "0x1234567890abcdef1234567890abcdef12345678",
                    "signature": "0x..."
                }
            }
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440025"
}'
```

### Step 4: Send Payment Request

Copy and run the curl command from Step 3.

**Expected Response (Success):**
```json
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440025",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440078",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2025-10-26T15:00:05.000000+00:00"
        },
        "artifacts": [
            {
                "kind": "text",
                "name": "response",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Here's your sunset quote: ..."
                    }
                ]
            }
        ],
        "metadata": {
            "x402.payment.status": "payment-completed",
            "x402.payment.receipts": [
                {
                    "transactionHash": "0x...",
                    "blockNumber": 12345,
                    "network": "base-sepolia"
                }
            ]
        }
    }
}
```

✅ **Phase 2 Complete:** Payment verified, agent executed, payment settled!

## Advanced Usage

### Custom Payment Parameters

```bash
python examples/generate_test_wallet.py --generate-request \
    --private-key <YOUR_PRIVATE_KEY> \
    --resource "/agent/my-custom-agent" \
    --network "base-sepolia" \
    --asset "0x036CbD53842c5426634e7929541eC2318f3dCF7e" \
    --pay-to "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0" \
    --amount "10000000000" \
    --message "your custom message" \
    --context-id "your-context-id" \
    --task-id "your-task-id"
```

### Sign Payment Only (Without Full Request)

```bash
python examples/generate_test_wallet.py --sign-payment \
    --private-key <YOUR_PRIVATE_KEY> \
    --resource "/agent/first Agent" \
    --amount "10000000000"
```

## Testing Scenarios

### Scenario 1: Successful Payment Flow

1. ✅ First request → `payment-required`
2. ✅ Generate signed payment
3. ✅ Second request → `payment-completed`
4. ✅ Agent executes and returns artifacts

### Scenario 2: Invalid Signature

1. ✅ First request → `payment-required`
2. ❌ Submit invalid signature
3. ✅ Response → `payment-failed` with error
4. ✅ Task returns to `input-required`

**Test:**
```bash
# Manually modify signature in the curl request to be invalid
"signature": "0xinvalid"
```

**Expected:**
```json
{
    "status": {
        "state": "input-required"
    },
    "metadata": {
        "x402.payment.status": "payment-failed",
        "x402.payment.error": "invalid_signature"
    }
}
```

### Scenario 3: Settlement Failure

This happens when payment verification succeeds but on-chain settlement fails (e.g., insufficient gas, network issues).

**Expected:**
```json
{
    "status": {
        "state": "input-required"
    },
    "metadata": {
        "x402.payment.status": "payment-failed",
        "x402.payment.error": "settlement_failed"
    }
}
```

### Scenario 4: Agent Without Payment

For agents without `execution_cost`, the flow works normally without payment:

1. ✅ Request → Agent executes immediately
2. ✅ Response → `completed` with artifacts
3. ✅ No payment metadata

## Troubleshooting

### Error: "Payment verification failed"

**Cause:** Invalid signature or payment data mismatch

**Solution:**
1. Ensure you're using the correct private key
2. Verify payment parameters match the requirements
3. Check that signature was generated correctly

### Error: "Payment settlement failed"

**Cause:** On-chain transaction failed

**Solution:**
1. Check network connectivity
2. Verify facilitator service is running
3. Check wallet has sufficient gas (for testnet)

### Error: "Payment required"

**Cause:** No payment payload in request

**Solution:**
1. Ensure `metadata.x402.payment.payload` is present
2. Verify `metadata.x402.payment.status` is `"payment-submitted"`

## Mock Testing (Development)

For development without blockchain interaction, you can mock the facilitator:

```python
# In your test file
from unittest.mock import patch, MagicMock, AsyncMock

with patch("bindu.server.workers.manifest_worker.FacilitatorClient") as mock:
    instance = MagicMock()
    
    # Mock verify (success)
    verify_response = MagicMock()
    verify_response.is_valid = True
    instance.verify = AsyncMock(return_value=verify_response)
    
    # Mock settle (success)
    settle_response = MagicMock()
    settle_response.success = True
    settle_response.model_dump = MagicMock(return_value={
        "transactionHash": "0xtest123",
        "blockNumber": 12345
    })
    instance.settle = AsyncMock(return_value=settle_response)
    
    mock.return_value = instance
    
    # Run your tests...
```

## Security Notes

⚠️ **IMPORTANT:**

1. **Test Wallets Only:** Never use test wallets for real funds
2. **Private Key Security:** Never commit private keys to git
3. **Testnet Only:** Use base-sepolia or other testnets for development
4. **Production:** Use proper wallet integration (MetaMask, WalletConnect) in production

## Next Steps

- [ ] Test complete payment flow
- [ ] Test error scenarios (invalid signature, settlement failure)
- [ ] Integrate with frontend wallet (MetaMask, etc.)
- [ ] Deploy to testnet
- [ ] Get test USDC from faucet
- [ ] Monitor transactions on block explorer

## Resources

- [x402 Specification](https://github.com/google-agentic-commerce/a2a-x402)
- [Base Sepolia Faucet](https://faucet.circle.com/)
- [Base Sepolia Explorer](https://sepolia.basescan.org/)
- [Bindu x402 Implementation](./x402-implementation-phases.md)
