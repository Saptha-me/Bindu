"""Verify the payment signature locally before sending to facilitator."""

import json
from eth_account import Account
from eth_account.messages import encode_typed_data

# Load the payment request
with open("examples/second_request.json") as f:
    request = json.load(f)

payment_payload = request["params"]["message"]["metadata"]["x402.payment.payload"]
authorization = payment_payload["payload"]["authorization"]
signature = payment_payload["payload"]["signature"]

print("=" * 80)
print("PAYMENT DETAILS")
print("=" * 80)
print(f"From: {authorization['from']}")
print(f"To: {authorization['to']}")
print(f"Value: {authorization['value']}")
print(f"Nonce: {authorization['nonce']}")
print(f"Signature: {signature}")

# Reconstruct EIP-712 data
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
        "name": "USDC",
        "version": "2",
        "chainId": 84532,  # Base Sepolia
        "verifyingContract": "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    },
    "message": authorization
}

print("\n" + "=" * 80)
print("EIP-712 VERIFICATION")
print("=" * 80)

# Encode and verify
signable_message = encode_typed_data(full_message=eip712_data)
print(f"Message hash: {signable_message.body.hex()}")

try:
    # Remove 0x prefix if present
    sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
    recovered_address = Account.recover_message(signable_message, signature=sig_bytes)
    
    print(f"\nRecovered address: {recovered_address}")
    print(f"Expected address:  {authorization['from']}")
    
    if recovered_address.lower() == authorization['from'].lower():
        print("\n✅ SIGNATURE IS VALID")
        print("The signature correctly recovers to the 'from' address")
    else:
        print("\n❌ SIGNATURE IS INVALID")
        print("The signature does NOT recover to the 'from' address")
        print("\nThis is why the facilitator is rejecting it!")
        
except Exception as e:
    print(f"\n❌ ERROR VERIFYING SIGNATURE: {e}")
    import traceback
    traceback.print_exc()

# Also check wallet balance
print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. If signature is valid, check wallet USDC balance:")
print(f"   https://sepolia.basescan.org/address/{authorization['from']}")
print("\n2. If balance is sufficient, the issue might be:")
print("   - RPC node issues on facilitator side")
print("   - Network congestion")
print("   - Try again in a few minutes")
