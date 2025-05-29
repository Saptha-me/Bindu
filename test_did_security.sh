#!/bin/bash

# Define agent endpoint
AGENT_ENDPOINT="http://localhost:8000/"

# Generate or use existing DID document
if [ ! -f "test_client_did.json" ]; then
  cat > test_client_did.json << EOL
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
  "verificationMethod": [{
    "id": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK#keys-1",
    "type": "Ed25519VerificationKey2018",
    "controller": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    "publicKeyBase58": "HNJS2wRe4xXkYe1ZCk4WMZ9zaEDDcGoQFZ7SpWVzwA9Q"
  }],
  "authentication": ["did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK#keys-1"]
}
EOL
fi

# Step 1: Exchange DIDs
echo "Exchanging DIDs..."
DID_DOCUMENT=$(cat test_client_did.json | tr -d '\n')
DID_RESPONSE=$(curl -s -X POST "$AGENT_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "exchange_did",
    "params": {
      "source_agent_id": "test-client",
      "did_document": '"$DID_DOCUMENT"'
    },
    "id": "1"
  }')

echo "DID Exchange Response:"
echo "$DID_RESPONSE" | python -m json.tool

# Extract agent DID for further communications
AGENT_DID=$(echo "$DID_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['did'])")
echo "Agent DID: $AGENT_DID"

# Step 2: Verify identity - request a challenge
echo -e "\nVerifying identity (requesting challenge)..."
VERIFY_RESPONSE=$(curl -s -X POST "$AGENT_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "verify_identity",
    "params": {
      "source_agent_id": "test-client"
    },
    "id": "2"
  }')

echo "Identity Verification Challenge Response:"
echo "$VERIFY_RESPONSE" | python -m json.tool

# Extract the challenge details
CHALLENGE=$(echo "$VERIFY_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['challenge'])")
CHALLENGE_ID=$(echo "$VERIFY_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['challenge_id'])")

echo "Challenge: $CHALLENGE"
echo "Challenge ID: $CHALLENGE_ID"

# Step 3: Respond to the challenge (in a real implementation, you would sign the challenge)
echo -e "\nResponding to challenge (pretending to sign it)..."
SIGNATURE="simulated_signature_for_demo_purposes_only"

VERIFY_RESPONSE2=$(curl -s -X POST "$AGENT_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "verify_identity",
    "params": {
      "source_agent_id": "test-client",
      "challenge_id": "'"$CHALLENGE_ID"'",
      "signature": "'"$SIGNATURE"'"
    },
    "id": "3"
  }')

echo "Challenge Response Result:"
echo "$VERIFY_RESPONSE2" | python -m json.tool

# Step 4: Send a test message
echo -e "\nSending a test message..."
MESSAGE_RESPONSE=$(curl -s -X POST "$AGENT_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "act",
    "params": {
      "source_agent_id": "test-client",
      "message": "Hello secure agent!"
    },
    "id": "4"
  }')

echo "Message Response:"
echo "$MESSAGE_RESPONSE" | python -m json.tool