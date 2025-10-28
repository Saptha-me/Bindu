# X402 Middleware Implementation

**Status:** ✅ COMPLETED  
**Last Updated:** 2025-10-28  
**Implementation:** Middleware-only approach (clean & minimal)

---

## 📋 Overview

Bindu now implements x402 payment protocol using HTTP middleware, following the official Coinbase x402 specification. This provides a clean, standard way for agents to monetize their services through on-chain payments.

### Key Design Decision

**Middleware-Only Approach**: Payment verification happens at the HTTP layer via `X-PAYMENT` headers, not through A2A metadata. This matches the official x402 specification and simplifies the codebase.

---

## 🏗️ Architecture

```
Client Request
    ↓
X402Middleware (if agent has execution_cost)
    ↓
    ├─ No X-PAYMENT header? → Return 402 Payment Required
    ├─ Invalid payment? → Return 402 with error
    └─ Valid payment? → Verify → Continue
    ↓
A2A Protocol Endpoint (/)
    ↓
MessageHandlers.send_message()
    ↓
Agent Execution
    ↓
Response
    ↓
X402Middleware
    ↓
Settle Payment → Add X-PAYMENT-RESPONSE header
    ↓
Client receives response + payment confirmation
```

---

## 📁 Implementation Files

### 1. **X402Middleware** (`bindu/server/middleware/x402_middleware.py`)

**Responsibilities:**
- Intercepts requests to `/` (A2A endpoint)
- Checks for `X-PAYMENT` header
- Returns 402 if payment required but not provided
- Verifies payment with Coinbase facilitator
- Settles payment after successful agent execution
- Adds `X-PAYMENT-RESPONSE` header to response

**Key Features:**
- Based on official Coinbase x402 FastAPI middleware
- Uses `find_matching_payment_requirements()` from x402 library
- Automatic payment verification and settlement
- Proper error handling and logging

### 2. **Simplified MessageHandlers** (`bindu/server/handlers/message_handlers.py`)

**Changes:**
- ❌ Removed `_handle_payment_required()` method
- ❌ Removed `_handle_payment_verification()` method
- ❌ Removed all A2A metadata payment logic
- ✅ Simplified `send_message()` to just submit and schedule tasks

**Result:** 
- Reduced from 401 lines to ~230 lines
- Payment logic completely removed
- Clean separation of concerns

### 3. **Middleware Registration** (`bindu/server/applications.py`)

**Changes:**
- Automatically registers `X402Middleware` if agent has `execution_cost`
- Middleware runs before authentication (payment first, then auth)
- No configuration needed - works automatically

---

## 🔧 Configuration

### Agent Configuration

Add `execution_cost` to your agent config:

```json
{
  "name": "my_agent",
  "description": "A paid agent",
  "execution_cost": {
    "amount": "$0.01",
    "token": "USDC",
    "network": "base-sepolia",
    "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
  }
}
```

**That's it!** The middleware is automatically enabled.

---

## 💻 Client Usage

### JavaScript/TypeScript (Recommended)

```javascript
import { wrapFetchWithPayment } from "x402-fetch";
import { privateKeyToAccount } from "viem/accounts";

// Create wallet
const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY);

// Wrap fetch with automatic payment
const fetchWithPayment = wrapFetchWithPayment(fetch, account);

// Make request - payment handled automatically!
const response = await fetchWithPayment("http://localhost:3773/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    jsonrpc: "2.0",
    method: "message/send",
    params: {
      message: {
        role: "user",
        parts: [{ kind: "text", text: "Hello!" }]
      }
    }
  })
});

const result = await response.json();
```

### Browser Wallets

Use Coinbase Wallet browser extension - payment UI appears automatically!

### Python

```python
# Coming soon - using x402 Python package
```

---

## 🔄 Payment Flow

### 1. **First Request (No Payment)**

```http
POST / HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {...}
}
```

**Response: 402 Payment Required**

```json
{
  "x402Version": 1,
  "accepts": [{
    "scheme": "exact",
    "network": "base-sepolia",
    "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    "max_amount_required": "10000",
    "resource": "did:bindu:user:agent:uuid",
    "description": "Payment required to use my_agent",
    "pay_to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    "max_timeout_seconds": 600,
    "extra": {...}
  }],
  "error": "No X-PAYMENT header provided"
}
```

### 2. **Second Request (With Payment)**

```http
POST / HTTP/1.1
Content-Type: application/json
X-PAYMENT: eyJ4NDAyVmVyc2lvbiI6MSwic2NoZW1lIjoi...

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {...}
}
```

**Middleware Actions:**
1. ✅ Decode `X-PAYMENT` header
2. ✅ Parse `PaymentPayload`
3. ✅ Match payment requirements
4. ✅ Verify with facilitator
5. ✅ Allow request to proceed
6. ✅ Agent executes
7. ✅ Settle payment
8. ✅ Add `X-PAYMENT-RESPONSE` header

**Response: 200 OK**

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-uuid",
    "status": {"state": "completed"},
    "artifacts": [...]
  }
}
```

**Headers:**
```
X-PAYMENT-RESPONSE: eyJzdWNjZXNzIjp0cnVlLCJ0cmFuc2FjdGlvbkhhc2giOi...
```

---

## ✅ Benefits

1. **✅ Standards Compliant** - Follows official Coinbase x402 spec
2. **✅ Clean Architecture** - Payment logic in middleware, not business logic
3. **✅ Automatic** - No manual payment handling needed
4. **✅ Browser Compatible** - Works with Coinbase Wallet extension
5. **✅ Library Support** - Use official x402-fetch/x402-axios packages
6. **✅ Minimal Code** - Removed 170+ lines of payment logic from message_handlers
7. **✅ Easy Testing** - Use x402 client libraries for testing

---

## 🔍 Comparison: Before vs After

| Aspect | Before (A2A Metadata) | After (Middleware) |
|--------|----------------------|-------------------|
| **Payment Location** | A2A message metadata | HTTP X-PAYMENT header |
| **Verification** | In message_handlers.py | In X402Middleware |
| **Settlement** | In manifest_worker.py | In X402Middleware |
| **Client Support** | Custom implementation needed | Use x402-fetch/x402-axios |
| **Browser Wallets** | ❌ Not supported | ✅ Supported |
| **Code Complexity** | High (401 lines) | Low (230 lines) |
| **Standards Compliance** | Custom | ✅ Official x402 spec |

---

## 📚 Resources

- **Client Examples:** `/examples/clients/`
- **Middleware Code:** `/bindu/server/middleware/x402_middleware.py`
- **Official x402 Docs:** https://docs.cdp.coinbase.com/x402/welcome
- **x402-fetch Package:** https://www.npmjs.com/package/x402-fetch
- **x402-axios Package:** https://www.npmjs.com/package/x402-axios

---

## 🚀 Next Steps

1. ✅ Test with browser wallet (Coinbase Wallet extension)
2. ✅ Test with x402-fetch client library
3. ✅ Test with x402-axios client library
4. ⏳ Add Python client example when x402 Python package is ready
5. ⏳ Add to x402 Bazaar for discovery

---

## 🎉 Summary

The middleware-only approach provides a clean, standards-compliant implementation of x402 payment protocol in Bindu. Agents can now monetize their services with minimal configuration, and clients can use standard x402 libraries for automatic payment handling.

**From idea to paid agent in 2 minutes!** 🌻🚀✨
