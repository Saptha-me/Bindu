"""Generate payment payload for the /foo endpoint."""

import base64
import json
import secrets
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_typed_data

# Load wallet
with open("examples/test_wallet.json") as f:
    wallet = json.load(f)

private_key = wallet["private_key"]
account = Account.from_key(private_key)
payer_address = account.address

# Payment details (matching payment_requirements in coinbase_check.py)
pay_to = "0x2654bb8B272f117c514aAc3d4032B1795366BA5d"  # Must match coinbase_check.py
amount = "10"  # 0.01 USDC in atomic units
asset = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC on base-sepolia

# Create authorization
current_time = int(datetime.now(timezone.utc).timestamp())
random_nonce = "0x" + secrets.token_hex(20)

authorization = {
    "from": payer_address,
    "to": pay_to,
    "value": amount,
    "validAfter": str(current_time - 60),
    "validBefore": str(current_time + 3600),
    "nonce": random_nonce,
}

# Create EIP-712 typed data for USDC
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
        "chainId": 84532,  # base-sepolia
        "verifyingContract": asset
    },
    "message": authorization
}

# Sign with EIP-712
signable_message = encode_typed_data(full_message=eip712_data)
signed = account.sign_message(signable_message)

# Create payment payload
payment_payload = {
    "x402Version": 1,
    "scheme": "exact",
    "network": "base-sepolia",
    "payload": {
        "signature": "0x" + signed.signature.hex(),
        "authorization": authorization
    }
}

# Base64 encode for X-PAYMENT header
payment_json = json.dumps(payment_payload)
payment_header = base64.b64encode(payment_json.encode()).decode()

# Save to file for reference
with open("examples/foo_payment.json", "w") as f:
    json.dump(payment_payload, f, indent=4)

print("✅ Payment payload generated!")
print(f"\n📝 Payment Details:")
print(f"   Payer:        {payer_address}")
print(f"   Pay To:       {pay_to}")
print(f"   Amount:       {amount} (0.01 USDC)")
print(f"   Network:      base-sepolia")
print(f"   ValidAfter:   {authorization['validAfter']}")
print(f"   ValidBefore:  {authorization['validBefore']}")
print(f"   Nonce:        {random_nonce[:22]}...")
print(f"   Signature:    {signed.signature.hex()[:20]}...")

print(f"\n💾 Saved to: examples/foo_payment.json")

print(f"\n🚀 Curl command:")
print(f"curl -X GET http://localhost:8000/foo \\")
print(f"  -H 'Content-Type: application/json' \\")
print(f"  -H 'X-PAYMENT: {payment_header}' \\")
print(f"  -v")

print(f"\n📋 X-PAYMENT header value:")
print(payment_header)
