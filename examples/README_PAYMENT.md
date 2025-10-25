# X402 Payment Script Usage

## Quick Start

```bash
# Run with defaults (uses test_wallet.json and sample_payment_requirements.json)
python examples/create_x402_payment.py

# Output will be saved to examples/payment_payload.json
```

## Features

### ✅ Automatic Balance Checking
The script now automatically checks your USDC balance and shows:
- Current balance in USDC
- Whether you have sufficient funds
- Visual indicator (✓ Sufficient / ✗ Insufficient)

### 📁 File Structure
```
examples/
├── create_x402_payment.py          # Main payment script
├── generate_test_wallet.py         # Generate new test wallet
├── test_wallet.json                # Your test wallet (gitignored)
├── sample_payment_requirements.json # Sample payment requirements
└── payment_payload.json            # Generated payment (gitignored)
```

## Example Output

```
Payment Information
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field              ┃ Value                                       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Network            │ Base Sepolia (Testnet)                      │
│ Token              │ USDC                                        │
│ Amount             │ 0.010000 USDC (10000 atomic units)          │
│ Pay To             │ 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0  │
│ Your Address       │ 0xE24646D44BFf8FF9Bffb93D5C1aAb8d314C42370  │
│ Your Balance       │ 1.000000 USDC ✓ Sufficient                 │
│ Timeout            │ 600 seconds                                 │
└────────────────────┴─────────────────────────────────────────────┘
```

## Supported Networks

| Network | RPC Endpoint | USDC Address |
|---------|--------------|--------------|
| base-sepolia | https://sepolia.base.org | 0x036CbD53842c5426634e7929541eC2318f3dCF7e |
| base | https://mainnet.base.org | 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 |
| ethereum | https://eth.llamarpc.com | 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 |
| ethereum-sepolia | https://ethereum-sepolia-rpc.publicnode.com | 0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238 |

## Getting Testnet USDC

1. **Generate wallet** (if you don't have one):
   ```bash
   python examples/generate_test_wallet.py
   ```

2. **Get testnet USDC**:
   - Visit: https://faucet.circle.com/
   - Select "Base Sepolia"
   - Enter your address: `0xE24646D44BFf8FF9Bffb93D5C1aAb8d314C42370`
   - Click "Request USDC"

3. **Verify balance**:
   ```bash
   python examples/create_x402_payment.py
   # Check "Your Balance" row in the output
   ```

## Troubleshooting

### "Unable to fetch" balance
- Check your internet connection
- RPC endpoint might be down (try again later)
- Network not supported

### "Insufficient" balance
- Get more testnet USDC from faucet
- Check you're on the correct network

### "Error loading account"
- Verify private key format (should start with 0x)
- Check test_wallet.json exists and is valid JSON

## Security Notes

⚠️ **Never commit these files to git:**
- `test_wallet.json` - Contains your private key
- `payment_payload.json` - Contains signed transactions

✅ **These are already in .gitignore**

🔒 **For testnet only:**
- Never use test wallet for mainnet
- Never send real money to test addresses
