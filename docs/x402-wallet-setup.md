# x402 Wallet Setup Guide

Complete guide to setting up wallets for testing x402 payments on Base Sepolia.

---

## Prerequisites

- [ ] Python 3.9+
- [ ] Internet connection
- [ ] 10 minutes of your time

---

## Step 1: Generate Test Wallets

We'll create 2 wallets programmatically:

### Install Dependencies

```bash
pip install web3 eth-account python-dotenv
```

### Generate Wallets Script

Create `scripts/generate_wallets.py`:

```python
#!/usr/bin/env python3
"""Generate two test wallets for x402 payment testing."""

from eth_account import Account
import secrets
import os

def generate_wallet(name):
    """Generate a new Ethereum wallet."""
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    print(f"\n{'='*60}")
    print(f"🔐 {name} Wallet")
    print(f"{'='*60}")
    print(f"Address:     {account.address}")
    print(f"Private Key: {private_key}")
    print(f"{'='*60}")
    
    return {
        "address": account.address,
        "private_key": private_key
    }

def main():
    print("\n🚀 Generating Test Wallets for x402 Payment Testing\n")
    
    # Generate merchant wallet (receives payments)
    merchant = generate_wallet("MERCHANT (Agent/You)")
    
    # Generate client wallet (sends payments)
    client = generate_wallet("CLIENT (Payer)")
    
    # Create .env file
    env_content = f"""# x402 Payment Configuration
# Generated: {os.popen('date').read().strip()}

# Merchant Wallet (receives payments)
X402_PAY_TO={merchant['address']}
MERCHANT_PRIVATE_KEY={merchant['private_key']}

# Client Wallet (sends payments) - for testing only
CLIENT_ADDRESS={client['address']}
CLIENT_PRIVATE_KEY={client['private_key']}

# Network Configuration
X402__DEFAULT_NETWORK=base-sepolia
X402__MAX_TIMEOUT_SECONDS=600

# Facilitator (Coinbase)
X402_FACILITATOR_URL=https://api.developer.coinbase.com/x402
"""
    
    # Save to .env.test
    with open('.env.test', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Wallets generated successfully!")
    print(f"\n📝 Configuration saved to: .env.test")
    print("\n⚠️  IMPORTANT:")
    print("   1. NEVER commit .env.test to git")
    print("   2. Keep private keys secure")
    print("   3. These are TEST wallets only - don't use for real funds")
    
    print("\n📋 Next Steps:")
    print("   1. Copy .env.test to .env")
    print("   2. Get test funds from faucets (see below)")
    print("   3. Run the test script")
    
    print("\n🌊 Get Test Funds:")
    print(f"   Merchant: https://portal.cdp.coinbase.com/products/faucet")
    print(f"   Address:  {merchant['address']}")
    print(f"\n   Client:   https://portal.cdp.coinbase.com/products/faucet")
    print(f"   Address:  {client['address']}")

if __name__ == "__main__":
    main()
```

### Run the Script

```bash
cd /Users/rahuldutta/Documents/saptha-me/Bindu
python scripts/generate_wallets.py
```

**Output**:
```
🚀 Generating Test Wallets for x402 Payment Testing

============================================================
🔐 MERCHANT (Agent/You) Wallet
============================================================
Address:     0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
Private Key: 0x1234567890abcdef...
============================================================

============================================================
🔐 CLIENT (Payer) Wallet
============================================================
Address:     0x9876543210fedcba...
Private Key: 0xfedcba0987654321...
============================================================

✅ Wallets generated successfully!
📝 Configuration saved to: .env.test
```

---

## Step 2: Get Test Funds

### Option A: Coinbase Developer Platform (Recommended)

**Best for**: Reliable, official faucet

1. Go to: https://portal.cdp.coinbase.com/products/faucet
2. Create free account (if needed)
3. Enter your **merchant address**
4. Select "Base Sepolia"
5. Click "Claim"
6. Wait ~30 seconds
7. Repeat for **client address**

**Limits**: 1 claim per 24 hours per address

### Option B: QuickNode Faucet (Fastest)

**Best for**: Quick testing, multiple claims

1. Go to: https://faucet.quicknode.com/base/sepolia
2. Enter your **merchant address**
3. Complete captcha
4. Click "Continue"
5. Receive 0.1 ETH
6. Repeat for **client address**

**Limits**: 1 drip per 12 hours

### Option C: Multiple Faucets (Maximum Funds)

Use all faucets to get more test ETH:

```bash
# Merchant Address: 0xYourMerchantAddress
# Client Address: 0xYourClientAddress

# Claim from each:
1. Coinbase CDP:     0.1 ETH  (24h)
2. QuickNode:        0.1 ETH  (12h)
3. Alchemy:          0.1 ETH  (24h)
4. Superchain:       0.05 ETH (24h)
5. thirdweb:         0.1 ETH  (24h)
6. Ponzifun:         1.0 ETH  (48h) ⭐ Most generous!

Total: ~1.5 ETH per address
```

---

## Step 3: Verify Balances

Create `scripts/check_balances.py`:

```python
#!/usr/bin/env python3
"""Check wallet balances on Base Sepolia."""

from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv('.env.test')

# Connect to Base Sepolia
RPC_URL = "https://sepolia.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def check_balance(address, name):
    """Check ETH balance for an address."""
    balance_wei = w3.eth.get_balance(address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    
    print(f"\n{name}")
    print(f"  Address: {address}")
    print(f"  Balance: {balance_eth} ETH")
    
    if balance_eth == 0:
        print(f"  ⚠️  No funds! Get test ETH from faucet")
    elif balance_eth < 0.01:
        print(f"  ⚠️  Low balance! Consider getting more test ETH")
    else:
        print(f"  ✅ Sufficient funds for testing")
    
    return balance_eth

def main():
    print("\n🔍 Checking Wallet Balances on Base Sepolia\n")
    print("="*60)
    
    merchant_address = os.getenv('X402_PAY_TO')
    client_address = os.getenv('CLIENT_ADDRESS')
    
    if not merchant_address or not client_address:
        print("❌ Error: Wallets not configured!")
        print("   Run: python scripts/generate_wallets.py")
        return
    
    # Check connection
    if not w3.is_connected():
        print("❌ Error: Cannot connect to Base Sepolia RPC")
        return
    
    print(f"✅ Connected to Base Sepolia (Chain ID: {w3.eth.chain_id})")
    
    # Check balances
    merchant_balance = check_balance(merchant_address, "💼 Merchant Wallet")
    client_balance = check_balance(client_address, "👤 Client Wallet")
    
    print("\n" + "="*60)
    print("\n📊 Summary:")
    print(f"   Total Test ETH: {merchant_balance + client_balance} ETH")
    
    if merchant_balance > 0 and client_balance > 0:
        print("\n✅ Ready to test x402 payments!")
    else:
        print("\n⚠️  Get test funds from faucets:")
        print("   https://portal.cdp.coinbase.com/products/faucet")

if __name__ == "__main__":
    main()
```

### Run Balance Check

```bash
python scripts/check_balances.py
```

**Expected Output**:
```
🔍 Checking Wallet Balances on Base Sepolia

============================================================
✅ Connected to Base Sepolia (Chain ID: 84532)

💼 Merchant Wallet
  Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
  Balance: 0.1 ETH
  ✅ Sufficient funds for testing

👤 Client Wallet
  Address: 0x9876543210fedcba...
  Balance: 0.1 ETH
  ✅ Sufficient funds for testing

============================================================

📊 Summary:
   Total Test ETH: 0.2 ETH

✅ Ready to test x402 payments!
```

---

## Step 4: Configure Your Project

### Copy Configuration

```bash
# Copy test config to main .env
cp .env.test .env

# Or manually create .env with your addresses
cat > .env << EOF
X402_PAY_TO=0xYourMerchantAddress
X402__DEFAULT_NETWORK=base-sepolia
X402__MAX_TIMEOUT_SECONDS=600
EOF
```

### Add to .gitignore

```bash
echo ".env" >> .gitignore
echo ".env.test" >> .gitignore
echo "scripts/wallets.json" >> .gitignore
```

---

## Step 5: Test Payment Flow

Create `scripts/test_payment.py`:

```python
#!/usr/bin/env python3
"""Test x402 payment flow end-to-end."""

import os
import asyncio
from dotenv import load_dotenv
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

load_dotenv()

async def test_payment():
    """Test making a payment to a protected agent."""
    
    print("\n🧪 Testing x402 Payment Flow\n")
    print("="*60)
    
    # Load client wallet
    client_private_key = os.getenv('CLIENT_PRIVATE_KEY')
    client_account = Account.from_key(client_private_key)
    
    print(f"👤 Client: {client_account.address}")
    print(f"💼 Merchant: {os.getenv('X402_PAY_TO')}")
    print(f"🌐 Network: {os.getenv('X402__DEFAULT_NETWORK')}")
    
    # Test endpoint (your agent)
    agent_url = "http://localhost:3773"
    
    print(f"\n📡 Testing agent at: {agent_url}")
    print("="*60)
    
    try:
        # Create x402 client
        async with x402HttpxClient(
            account=client_account,
            base_url=agent_url
        ) as client:
            
            # Make request to protected endpoint
            print("\n1️⃣ Sending request to agent...")
            response = await client.post(
                "/v1/tasks",
                json={
                    "context_id": "test-context",
                    "message": {
                        "role": "user",
                        "content": "Hello, paid agent!"
                    }
                }
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 402:
                print("   ✅ Payment required (as expected)")
                
                # x402 client will automatically handle payment
                print("\n2️⃣ x402 client handling payment...")
                print("   - Creating payment authorization")
                print("   - Signing with client wallet")
                print("   - Submitting payment")
                
                # The client automatically retries with payment
                # Check the response
                result = await response.aread()
                print(f"\n3️⃣ Response: {result}")
                
            else:
                print(f"   Response: {await response.aread()}")
        
        print("\n✅ Payment test completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Is your agent running? (python examples/agno_example.py)")
        print("  2. Is X402_PAY_TO set correctly?")
        print("  3. Do both wallets have test ETH?")

if __name__ == "__main__":
    asyncio.run(test_payment())
```

---

## Troubleshooting

### Issue: "Insufficient funds"

**Solution**: Get more test ETH from faucets
```bash
python scripts/check_balances.py
# Visit faucets if balance is low
```

### Issue: "Cannot connect to RPC"

**Solution**: Check network configuration
```bash
# Verify RPC is accessible
curl https://sepolia.base.org \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Issue: "Payment verification failed"

**Solution**: Check logs
```bash
grep "x402" logs/bindu_server.log | tail -20
```

---

## Security Checklist

- [ ] ✅ Never commit `.env` or `.env.test` to git
- [ ] ✅ Never share private keys
- [ ] ✅ Use separate wallets for testing vs production
- [ ] ✅ Keep test wallets separate from real funds
- [ ] ✅ Rotate keys if accidentally exposed

---

## Quick Reference

### Faucet URLs

| Faucet | Amount | Cooldown | URL |
|--------|--------|----------|-----|
| Coinbase CDP | 0.1 ETH | 24h | https://portal.cdp.coinbase.com/products/faucet |
| QuickNode | 0.1 ETH | 12h | https://faucet.quicknode.com/base/sepolia |
| Ponzifun | 1.0 ETH | 48h | https://testnet.ponzi.fun/faucet |
| Alchemy | 0.1 ETH | 24h | https://basefaucet.com/ |

### Network Details

```
Network Name: Base Sepolia
RPC URL: https://sepolia.base.org
Chain ID: 84532
Currency: ETH
Explorer: https://sepolia.basescan.org
```

### Environment Variables

```bash
X402_PAY_TO=0xYourMerchantAddress          # Required
X402__DEFAULT_NETWORK=base-sepolia         # Required
X402__MAX_TIMEOUT_SECONDS=600              # Optional
MERCHANT_PRIVATE_KEY=0x...                 # For testing only
CLIENT_PRIVATE_KEY=0x...                   # For testing only
```

---

## Next Steps

1. ✅ Generate wallets: `python scripts/generate_wallets.py`
2. ✅ Get test funds from faucets
3. ✅ Check balances: `python scripts/check_balances.py`
4. ✅ Configure `.env` file
5. ✅ Test payment flow: `python scripts/test_payment.py`
6. 🚀 Deploy your paid agent!

---

**Ready to accept payments!** 💰
