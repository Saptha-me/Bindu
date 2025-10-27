#!/usr/bin/env python3
"""
Generate a test wallet for x402 payments.

This creates a new Ethereum wallet and saves the private key securely.
USE ONLY FOR TESTNET! Never use this wallet for real money.
"""

import json
from eth_account import Account
from pathlib import Path

# Generate new account
account = Account.create()

print("=" * 60)
print("NEW TEST WALLET GENERATED")
print("=" * 60)
print(f"\n📍 Public Address (safe to share):")
print(f"   {account.address}")
print(f"\n🔑 Private Key (KEEP SECRET!):")
print(f"   {account.key.hex()}")
print("\n" + "=" * 60)

# Save to file (for convenience)
wallet_data = {
    "address": account.address,
    "private_key": account.key.hex(),
    "network": "base-sepolia",
    "warning": "THIS IS A TEST WALLET - DO NOT USE FOR MAINNET"
}

output_file = Path(__file__).parent / "test_wallet.json"
with open(output_file, 'w') as f:
    json.dump(wallet_data, f, indent=2)

print(f"\n✅ Wallet saved to: {output_file}")
print("\n⚠️  SECURITY WARNINGS:")
print("   1. This wallet is for TESTNET ONLY")
print("   2. Never commit test_wallet.json to git")
print("   3. Add test_wallet.json to .gitignore")
print("   4. Never use this wallet for real money")
print("\n📝 Next steps:")
print("   1. Get testnet USDC from: https://faucet.circle.com/")
print("   2. Set environment variable:")
print(f"      export WALLET_PRIVATE_KEY='{account.key.hex()}'")
print("   3. Run payment script:")
print("      python create_x402_payment.py")
print("\n" + "=" * 60)