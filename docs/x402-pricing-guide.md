# x402 Pricing Guide - Atomic Units

Complete guide to pricing your agent using atomic units (the blockchain way).

---

## 🔢 Understanding Atomic Units

Blockchain tokens use **atomic units** - the smallest indivisible unit of a token.

### **USDC on Base**
- **Decimals**: 6
- **1 USDC** = 1,000,000 atomic units
- **$1.00 USD** = 1,000,000 atomic units

Think of it like cents:
- **1 dollar** = 100 cents
- **1 USDC** = 1,000,000 atomic units

---

## 💰 Pricing Examples

### **Common Prices**

| USD Price | Atomic Units | Config Value |
|-----------|--------------|--------------|
| $0.001 (0.1¢) | 1,000 | `"1000"` |
| $0.01 (1¢) | 10,000 | `"10000"` |
| $0.10 (10¢) | 100,000 | `"100000"` |
| $0.50 (50¢) | 500,000 | `"500000"` |
| $1.00 | 1,000,000 | `"1000000"` |
| $5.00 | 5,000,000 | `"5000000"` |
| $10.00 | 10,000,000 | `"10000000"` |
| $100.00 | 100,000,000 | `"100000000"` |

### **Micro-Payments** (AI Agent Use Cases)

| Use Case | USD | Atomic Units |
|----------|-----|--------------|
| Simple query | $0.001 | `"1000"` |
| Basic task | $0.01 | `"10000"` |
| Complex task | $0.10 | `"100000"` |
| Research task | $1.00 | `"1000000"` |
| Premium service | $10.00 | `"10000000"` |

---

## 📝 Configuration Format

### **Atomic Units (Recommended)**

```json
{
  "execution_cost": {
    "amount": "1000000",        // ← Atomic units (1 USDC = $1.00)
    "token": "USDC",            // ← Token symbol
    "network": "base-sepolia",  // ← Blockchain network
    "minimum_trust_level": "low",
    "payment_required": true
  }
}
```

### **Field Descriptions**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `amount` | string | Atomic units of token | `"1000000"` |
| `token` | string | Token symbol | `"USDC"` |
| `network` | string | Blockchain network | `"base-sepolia"` or `"base"` |
| `minimum_trust_level` | string | Required trust level | `"low"`, `"verified"`, `"trusted"` |
| `payment_required` | boolean | Is payment mandatory? | `true` or `false` |

---

## 🧮 Calculating Atomic Units

### **Formula**

```
Atomic Units = USD Amount × 10^decimals
```

For USDC (6 decimals):
```
Atomic Units = USD Amount × 1,000,000
```

### **Examples**

```javascript
// $0.01 USD
0.01 × 1,000,000 = 10,000 atomic units

// $1.00 USD
1.00 × 1,000,000 = 1,000,000 atomic units

// $5.50 USD
5.50 × 1,000,000 = 5,500,000 atomic units
```

### **Python Helper**

```python
def usd_to_atomic(usd_amount: float, decimals: int = 6) -> str:
    """Convert USD to atomic units."""
    atomic = int(usd_amount * (10 ** decimals))
    return str(atomic)

# Examples
usd_to_atomic(0.01)   # "10000"
usd_to_atomic(1.00)   # "1000000"
usd_to_atomic(10.00)  # "10000000"
```

---

## 🌐 Network-Specific Details

### **Base Sepolia (Testnet)**

```json
{
  "execution_cost": {
    "amount": "1000000",
    "token": "USDC",
    "network": "base-sepolia"
  }
}
```

- **Purpose**: Testing
- **USDC Contract**: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- **Get Test USDC**: https://faucet.circle.com/
- **Explorer**: https://sepolia.basescan.org

### **Base Mainnet (Production)**

```json
{
  "execution_cost": {
    "amount": "1000000",
    "token": "USDC",
    "network": "base"
  }
}
```

- **Purpose**: Real payments
- **USDC Contract**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Get USDC**: Buy on Coinbase, bridge to Base
- **Explorer**: https://basescan.org

---

## 💡 Pricing Strategies

### **1. Micro-Payments (AI Queries)**

```json
{
  "execution_cost": {
    "amount": "10000",  // $0.01 per query
    "token": "USDC",
    "network": "base"
  }
}
```

**Best for**: Simple Q&A, quick tasks, high-volume usage

### **2. Standard Pricing (Complex Tasks)**

```json
{
  "execution_cost": {
    "amount": "1000000",  // $1.00 per task
    "token": "USDC",
    "network": "base"
  }
}
```

**Best for**: Research, analysis, document processing

### **3. Premium Pricing (Specialized Services)**

```json
{
  "execution_cost": {
    "amount": "10000000",  // $10.00 per service
    "token": "USDC",
    "network": "base"
  }
}
```

**Best for**: Expert analysis, custom models, high-value outputs

### **4. Dynamic Pricing (Future)**

```json
{
  "execution_cost": {
    "amount": "variable",  // Based on complexity
    "min_amount": "100000",   // $0.10 minimum
    "max_amount": "5000000",  // $5.00 maximum
    "token": "USDC",
    "network": "base"
  }
}
```

**Best for**: Usage-based billing, token generation, compute-heavy tasks

---

## 🔍 Verification

### **Check Your Pricing**

```python
# Your config
amount = "1000000"
decimals = 6

# Calculate USD
usd_price = int(amount) / (10 ** decimals)
print(f"Price: ${usd_price:.2f} USD")
# Output: Price: $1.00 USD
```

### **Common Mistakes**

❌ **Wrong**: `"amount": "1.00"` (should be atomic units, not USD)  
✅ **Correct**: `"amount": "1000000"`

❌ **Wrong**: `"amount": 1000000` (should be string, not number)  
✅ **Correct**: `"amount": "1000000"`

❌ **Wrong**: Missing leading zeros: `"amount": "1000"` for $0.001  
✅ **Correct**: `"amount": "1000"` (this is actually correct!)

---

## 📊 Quick Reference Table

### **Atomic Units → USD**

```
Atomic Units ÷ 1,000,000 = USD

Examples:
1,000 ÷ 1,000,000 = $0.001
10,000 ÷ 1,000,000 = $0.01
100,000 ÷ 1,000,000 = $0.10
1,000,000 ÷ 1,000,000 = $1.00
10,000,000 ÷ 1,000,000 = $10.00
```

### **USD → Atomic Units**

```
USD × 1,000,000 = Atomic Units

Examples:
$0.001 × 1,000,000 = 1,000
$0.01 × 1,000,000 = 10,000
$0.10 × 1,000,000 = 100,000
$1.00 × 1,000,000 = 1,000,000
$10.00 × 1,000,000 = 10,000,000
```

---

## 🛠️ Testing Your Pricing

### **1. Start with Testnet**

```json
{
  "execution_cost": {
    "amount": "10000",  // $0.01 for testing
    "token": "USDC",
    "network": "base-sepolia"
  }
}
```

### **2. Get Test USDC**

Visit: https://faucet.circle.com/
- Select "Base Sepolia"
- Enter your wallet address
- Get free test USDC

### **3. Test Payment Flow**

```bash
# Check your agent's pricing
curl http://localhost:3773/agent/info | jq '.execution_cost'

# Expected output:
{
  "amount": "10000",
  "token": "USDC",
  "network": "base-sepolia"
}
```

### **4. Move to Production**

Once tested, update to mainnet:

```json
{
  "execution_cost": {
    "amount": "1000000",  // $1.00 real money
    "token": "USDC",
    "network": "base"  // ← Changed from base-sepolia
  }
}
```

---

## 📚 Additional Resources

- **x402 Protocol**: https://github.com/coinbase/x402
- **USDC on Base**: https://www.circle.com/en/usdc-multichain/base
- **Base Network**: https://base.org
- **EIP-3009 Standard**: https://eips.ethereum.org/EIPS/eip-3009

---

## 💬 FAQ

### **Q: Why use atomic units instead of USD?**
A: Blockchain tokens are stored as integers (no decimals). Atomic units are the native format.

### **Q: Can I use other tokens besides USDC?**
A: Currently, x402 primarily supports USDC. Other tokens may be added in the future.

### **Q: What if I want to charge in ETH?**
A: ETH has 18 decimals. For $1.00 worth of ETH at $3000/ETH:
```
1 ÷ 3000 = 0.000333... ETH
0.000333... × 10^18 = 333,333,333,333,333 atomic units
```

### **Q: Can I change pricing after deployment?**
A: Yes! Update your config and restart the agent. Existing tasks use old pricing, new tasks use new pricing.

### **Q: What's the minimum price?**
A: Technically 1 atomic unit = $0.000001 USD, but gas fees make very small payments impractical. Recommended minimum: $0.01 (10,000 atomic units).

---

**Use atomic units for precise, blockchain-native pricing!** 🎯
