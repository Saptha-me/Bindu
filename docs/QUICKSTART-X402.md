# x402 Quick Start Guide

Get your agent accepting payments in 5 minutes! 🚀

---

## Step 1: Generate Wallets (1 minute)

```bash
# Install dependencies
pip install web3 eth-account

# Generate test wallets
python scripts/generate_wallets.py
```

**Output**: Two wallet addresses + `.env.test` file

---

## Step 2: Get Test Funds (2 minutes)

Visit any faucet and paste your wallet addresses:

**Recommended**: https://portal.cdp.coinbase.com/products/faucet

1. Paste **Merchant Address** → Claim 0.1 ETH
2. Paste **Client Address** → Claim 0.1 ETH

**Done!** ✅

---

## Step 3: Verify Setup (30 seconds)

```bash
# Copy config
cp .env.test .env

# Check balances
python scripts/check_balances.py
```

**Expected**: Both wallets show > 0 ETH

---

## Step 4: Create Paid Agent (1 minute)

```python
# examples/paid_agent.py
import os
from agno import Agent
from bindu.penguin import bindufy
from bindu.extensions.x402.merchant import create_payment_requirements

# Your agent
agent = Agent(
    name="Premium Agent",
    model="gpt-4",
)

# Add payment protection
config = {
    "author": "you@example.com",
    "name": "premium_agent",
    "execution_cost": {
        "credits_per_request": 100,  # $1.00 per request
    },
}

# Wrap run method
original_run = agent.run

def paid_run(messages, **kwargs):
    # Require payment
    return {
        "state": "payment-required",
        "required": {
            "accepts": [
                create_payment_requirements(
                    price="$1.00",
                    pay_to_address=os.getenv("X402_PAY_TO"),
                    network="base-sepolia",
                )
            ]
        }
    }

agent.run = paid_run

# Start server
bindu_agent = bindufy(agent, config)
bindu_agent.serve(port=3773)
```

---

## Step 5: Test It! (30 seconds)

```bash
# Terminal 1: Start agent
python examples/paid_agent.py

# Terminal 2: Test payment
curl -X POST http://localhost:3773/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "context_id": "test",
    "message": {
      "role": "user",
      "content": "Hello!"
    }
  }'
```

**Expected Response**:
```json
{
  "state": "payment-required",
  "required": {
    "accepts": [{
      "price": "$1.00",
      "network": "base-sepolia",
      "pay_to": "0xYourAddress"
    }]
  }
}
```

---

## ✅ You're Done!

Your agent now:
- ✅ Requires payment before execution
- ✅ Validates payment amount
- ✅ Prevents double-spend
- ✅ Enforces timeout
- ✅ Auto-retries settlement
- ✅ Logs everything

---

## What Happens Behind the Scenes

```
1. Client requests task
   ↓
2. Agent returns payment-required
   ↓
3. Client creates payment (signs with wallet)
   ↓
4. Client resubmits with payment
   ↓
5. ManifestWorker validates:
   ✓ Amount correct
   ✓ Nonce unique
   ✓ Not expired
   ✓ Signature valid (via x402 facilitator)
   ↓
6. Agent executes task
   ↓
7. Payment settled on-chain (with retries)
   ↓
8. Client receives result + tx_hash
```

**You don't write any of this - it's all automatic!**

---

## Troubleshooting

### "No funds"
```bash
python scripts/check_balances.py
# Visit faucet if balance is 0
```

### "Payment verification failed"
```bash
# Check logs
grep "x402" logs/bindu_server.log
```

### "Cannot connect"
```bash
# Verify RPC
curl https://sepolia.base.org -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

---

## Production Checklist

When ready for mainnet:

- [ ] Get real Base wallet (Coinbase Wallet or MetaMask)
- [ ] Buy real ETH and bridge to Base
- [ ] Update `.env`: `X402__DEFAULT_NETWORK=base`
- [ ] Update `X402_PAY_TO` to your real wallet
- [ ] Test with small amounts first
- [ ] Monitor logs and metrics

---

## Resources

- 📖 [Full Wallet Setup Guide](./x402-wallet-setup.md)
- 🔒 [Security Documentation](./x402-security.md)
- 📋 [Phase 2 Summary](./x402-phase2-summary.md)
- 🌐 [Base Faucets](https://docs.base.org/docs/tools/network-faucets)
- 💬 [x402 Protocol](https://github.com/coinbase/x402)

---

**Happy Building!** 💰🚀
