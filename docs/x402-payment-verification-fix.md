# x402 Payment Verification Fix

## Issue Summary

The payment verification was failing with `invalid_payload` error because the payment payload was not conforming to the official x402 protocol specification.

## Root Cause

The `process_payment_response.py` script was generating an **incorrect payment payload format** using simple message signing instead of the proper **EIP-712 typed data signing** required by the x402 protocol.

### Incorrect Format (Before)
```json
{
  "resource": "/agent/first Agent",
  "scheme": "exact",
  "network": "base-sepolia",
  "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
  "amount": "10000000000",
  "timestamp": "2025-10-26T16:14:47.587608+00:00",
  "payer": "0x558AB94CB5249F94E217e2cCaa04E4E0fFBE879A",
  "signature": "0x..."
}
```

### Correct Format (After)
```json
{
  "x402Version": 1,
  "scheme": "exact",
  "network": "base-sepolia",
  "payload": {
    "signature": "0x...",
    "authorization": {
      "from": "0x558AB94CB5249F94E217e2cCaa04E4E0fFBE879A",
      "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
      "value": "10000000000",
      "validAfter": "0",
      "validBefore": "1761500061",
      "nonce": "0x0000000000000000000000000000000000000000000000000000000000000000"
    }
  }
}
```

## Technical Details

### EIP-3009 Authorization

The x402 protocol uses **EIP-3009 (Transfer With Authorization)** which allows gasless token transfers. The authorization must be signed using **EIP-712 typed data**.

### EIP-712 Typed Data Structure

```python
eip712_data = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"}
        ],
        "TransferWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"}
        ]
    },
    "primaryType": "TransferWithAuthorization",
    "domain": {
        "name": "USDC",  # From payment_requirements.extra.name
        "version": "2",  # From payment_requirements.extra.version
        "chainId": 84532,  # base-sepolia
        "verifyingContract": "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC contract
    },
    "message": {
        "from": "0x558AB94CB5249F94E217e2cCaa04E4E0fFBE879A",
        "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        "value": "10000000000",
        "validAfter": "0",
        "validBefore": "1761500061",
        "nonce": "0x0000000000000000000000000000000000000000000000000000000000000000"
    }
}
```

## Changes Made

### 1. Updated `process_payment_response.py`

**Before:**
- Used `encode_defunct()` for simple message signing
- Created flat payment data structure
- Signature over JSON string

**After:**
- Uses `encode_typed_data()` for EIP-712 signing
- Creates proper EIP-3009 authorization structure
- Signature over typed data hash
- Includes proper domain parameters from `payment_requirements.extra`

### 2. Key Improvements

1. **Proper EIP-712 Domain**: Uses token contract's `name` and `version` from `extra` field
2. **Chain ID Mapping**: Automatically determines chain ID from network name
3. **Authorization Structure**: Follows EIP-3009 specification exactly
4. **x402 Version**: Includes `x402Version: 1` in payload
5. **Nested Payload**: Wraps authorization and signature in `payload` object

## Testing

To test the fix:

```bash
# 1. Start the agent
python examples/agno_example.py

# 2. Send initial request (will return payment-required)
curl --location 'http://localhost:8030/' \
--header 'Content-Type: application/json' \
--data '{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "provide sunset quote"}],
      "kind": "message",
      "messageId": "550e8400-e29b-41d4-a716-446655440037",
      "contextId": "550e8400-e29b-41d4-a716-446655440038"
    }
  },
  "id": "550e8400-e29b-41d4-a716-446655440024"
}'

# 3. Generate signed payment (now uses correct EIP-712 format)
python examples/process_payment_response.py \
  --response examples/example-reponse-payload.json \
  --private-key <YOUR_PRIVATE_KEY>

# 4. Send payment request (should now verify successfully)
curl --location 'http://localhost:8030/' \
--header 'Content-Type: application/json' \
--data @examples/second_request.json
```

## References

- **x402 A2A Protocol**: https://github.com/google-agentic-commerce/a2a-x402
- **EIP-3009**: https://eips.ethereum.org/EIPS/eip-3009
- **EIP-712**: https://eips.ethereum.org/EIPS/eip-712
- **Official Documentation**: Line 319+ in x402 A2A README

## Related Files

- `/examples/process_payment_response.py` - Fixed to use EIP-712 signing
- `/examples/generate_second_request.py` - Already had correct implementation
- `/bindu/server/handlers/message_handlers.py` - Payment verification handler
- `/bindu/extensions/x402/merchant.py` - Payment requirements creation

## Notes

- The `generate_second_request.py` script already had the correct implementation
- The `process_payment_response.py` was a simplified version that didn't follow the spec
- Both scripts now generate identical payment payload formats
- The `extra` field in `PaymentRequirements` is critical for EIP-712 domain parameters
