# Bindu Client Examples

This directory contains examples of how to interact with Bindu agents that require payment via the x402 protocol.

## Overview

When a Bindu agent has `execution_cost` configured, it requires payment before execution. The payment is handled automatically by x402 client libraries.

## JavaScript/TypeScript Clients

### Prerequisites

```bash
npm install x402-fetch viem
# or
npm install x402-axios viem
```

### Using x402-fetch (Recommended)

See `fetch-example.js` for a complete example using the native fetch API with automatic payment handling.

```javascript
import { wrapFetchWithPayment, decodeXPaymentResponse } from "x402-fetch";
import { privateKeyToAccount } from "viem/accounts";

// Create wallet from private key
const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY);

// Wrap fetch with automatic payment handling
const fetchWithPayment = wrapFetchWithPayment(fetch, account);

// Make request - payment handled automatically!
const response = await fetchWithPayment("http://localhost:3773/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: "1",
    method: "message/send",
    params: {
      message: {
        role: "user",
        parts: [{ kind: "text", text: "Hello, agent!" }]
      }
    }
  })
});

const result = await response.json();
const paymentResponse = decodeXPaymentResponse(
  response.headers.get("x-payment-response")
);

console.log("Agent response:", result);
console.log("Payment confirmation:", paymentResponse);
```

### Using x402-axios

See `axios-example.js` for a complete example using axios with payment interceptors.

```javascript
import axios from "axios";
import { withPaymentInterceptor, decodeXPaymentResponse } from "x402-axios";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY);
const api = withPaymentInterceptor(axios.create(), account);

const response = await api.post("http://localhost:3773/", {
  jsonrpc: "2.0",
  id: "1",
  method: "message/send",
  params: {
    message: {
      role: "user",
      parts: [{ kind: "text", text: "Hello, agent!" }]
    }
  }
});

const paymentResponse = decodeXPaymentResponse(
  response.headers["x-payment-response"]
);
```

## Python Clients

### Using x402 Python Package

```bash
pip install x402 eth-account
```

See `python-example.py` for a complete example.

## Browser Wallets

For browser-based applications, use the Coinbase Wallet browser extension. The extension automatically:
1. Detects 402 Payment Required responses
2. Shows a payment UI to the user
3. Signs the payment with the user's wallet
4. Retries the request with payment

No additional code needed - just make normal HTTP requests!

## Manual Payment Generation (For Testing)

If you need to manually generate payment headers for testing with cURL or Postman:

```bash
# Use the existing payment generation script
python ../generate_payment_for_foo.py

# Copy the X-PAYMENT header value to your HTTP client
```

## Environment Variables

All examples require a wallet private key:

```bash
# Create .env file
WALLET_PRIVATE_KEY="0x..."
```

⚠️ **Security Warning**: Never commit your `.env` file or expose your private key!

## What Happens Automatically

The x402 client libraries handle:
1. ✅ Initial request to agent
2. ✅ Detection of 402 Payment Required response
3. ✅ Parsing of payment requirements
4. ✅ Signing payment with your wallet
5. ✅ Generation of X-PAYMENT header
6. ✅ Retry of request with payment
7. ✅ Extraction of payment confirmation

You just make a normal HTTP request - everything else is automatic!

## Resources

- [x402 Protocol Documentation](https://docs.cdp.coinbase.com/x402/welcome)
- [x402-fetch npm package](https://www.npmjs.com/package/x402-fetch)
- [x402-axios npm package](https://www.npmjs.com/package/x402-axios)
- [Bindu Documentation](https://docs.saptha.me)
