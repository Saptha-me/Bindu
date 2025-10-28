"""Generate second request with signed payment payload."""

import json
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_typed_data

# Load wallet
with open("examples/test_wallet.json") as f:
    wallet = json.load(f)

# Load first response
with open("examples/first_response.json") as f:
    first_response = json.load(f)

# Extract payment requirements
result = first_response["result"]
accepts = result["metadata"]["x402.payment.required"]["accepts"][0]

# Create payment data
private_key = wallet["private_key"]
account = Account.from_key(private_key)
payer_address = account.address

timestamp = datetime.now(timezone.utc).isoformat()

# Create EIP3009 authorization structure
import secrets
# Generate 20-byte nonce (40 hex chars) to match Coinbase API spec
random_nonce = "0x" + secrets.token_hex(20)
# Use Unix timestamps for validAfter and validBefore
current_time = int(datetime.now(timezone.utc).timestamp())
authorization = {
    "from": payer_address,
    "to": accepts["payTo"],
    "value": accepts["maxAmountRequired"],
    "validAfter": str(current_time - 60),  # Valid from 1 minute ago
    "validBefore": str(current_time + 3600),  # Valid for 1 hour
    "nonce": random_nonce,
}

# Create EIP-712 typed data for signing
# Get token info from extra field
token_name = accepts["extra"]["name"]  # "USDC"
token_version = accepts["extra"]["version"]  # "2"

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
        "name": token_name,
        "version": token_version,
        "chainId": 84532,  # base-sepolia chainId
        "verifyingContract": accepts["asset"]  # USDC contract address
    },
    "message": {
        "from": authorization["from"],
        "to": authorization["to"],
        "value": authorization["value"],
        "validAfter": authorization["validAfter"],
        "validBefore": authorization["validBefore"],
        "nonce": authorization["nonce"]
    }
}

# Sign with EIP-712
signable_message = encode_typed_data(full_message=eip712_data)
signed = account.sign_message(signable_message)

# Create PaymentPayload matching x402 spec
payment_payload = {
    "x402Version": 1,
    "scheme": accepts["scheme"],
    "network": accepts["network"],
    "payload": {
        "signature": "0x" + signed.signature.hex(),  # Add 0x prefix
        "authorization": authorization
    }
}

# Create second request
second_request = {
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "provide sunset quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440039",
            "contextId": result["context_id"],
            "taskId": result["id"],
            "metadata": {
                "x402.payment.status": "payment-submitted",
                "x402.payment.payload": payment_payload
            }
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440025"
}

# Save to file
with open("examples/second_request.json", "w") as f:
    json.dump(second_request, f, indent=4)

print("✅ Second request generated: examples/second_request.json")
print(f"\n📝 Payment Details:")
print(f"   Payer:        {payer_address}")
print(f"   Amount:       {accepts['maxAmountRequired']} (0.01 USDC)")
print(f"   Network:      {accepts['network']}")
print(f"   ValidAfter:   {authorization['validAfter']}")
print(f"   ValidBefore:  {authorization['validBefore']}")
print(f"   Nonce:        {random_nonce[:22]}... (20 bytes)")
print(f"   Signature:    {signed.signature.hex()[:20]}...")
print(f"\n🚀 Curl command:")
print(f"curl --location 'http://localhost:8030/' \\")
print(f"--header 'Content-Type: application/json' \\")
print(f"--header 'Authorization: Bearer <>' \\")
print(f"--data @examples/second_request.json")
