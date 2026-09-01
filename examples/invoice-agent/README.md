# Invoice Agent with X402 Payment Flow
====================================

## Overview

This example implements a billing agent that:

*   Generates invoices with structured line items
*   Emits X402-compatible payment requests    
*   Verifies payments and updates invoice state
    

It demonstrates a complete payment lifecycle:
```bash
   create → pay → verify → settled  
   ```

## Features

*   Invoice creation with structured payload
*   X402 payment header generation
*   Payment verification (mocked for demo)
*   In-memory (non-persistent) invoice state tracking
    
## Setup

Install dependencies:
```bash
pip install bindu python-dotenv
```

Create .env:
```bash
   AGENT_WALLET_ADDRESS=0x_your_wallet_here
   OPENROUTER_API_KEY=sk-xxxx #optional   
   ```

Run the agent:
```bash
  python invoice_agent.py  
  ```

## Example Input
```json
   {
  "type": "generate_invoice",
  "payload": {
    "recipient": "akash@example.com",
    "items": [
      { "description": "API access", "quantity": 1, "unit_price": 50 },
      { "description": "Compute", "quantity": 2, "unit_price": 20 }
    ],
    "currency": "USDC"
  }
}  
   ```
   
## Example Output:

```json
{
  "invoice_id": "inv_66ac3b32-6cb4-4588-bd06-f71160ba206c",
  "total": 90,
  "payment_header": "X402 0xE5bC3b8796432A70aC8450E2aaD54055d9e2DBb8:90"
}
{
  "invoice": {
    "id": "inv_66ac3b32-6cb4-4588-bd06-f71160ba206c",
    "recipient": "acme@example.com",
    "recipient_wallet": "0xE5bC3b8796432A70aC8450E2aaD54055d9e2DBb8",
    "items": [
      { "description": "API", "quantity": 1, "unit_price": 50 },
      { "description": "Compute", "quantity": 2, "unit_price": 20 }
    ],
    "currency": "USDC",
    "total": 90,
    "status": "paid",
    "tx_hash": "0xabc123"
  }
}
```


## Skills

*   generate\_invoice – create invoice and emit X402 payment request
*   get\_invoice – fetch invoice by ID
*   list\_invoices – list invoices
*   verify\_payment – verify payment and update invoice state
    

## Notes

*   Payment verification is mocked for demonstration
*   Storage is in-memory and can be replaced with a database
*   Wallet address can be any valid EVM address