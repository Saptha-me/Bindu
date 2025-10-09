#!/bin/bash
# Test authenticated request to Bindu agent

# Get token
TOKEN=$(python examples/get_auth0_token.py)

echo "Testing authenticated request..."
echo ""

# Send authenticated request
curl --location 'http://localhost:8030/' \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer $TOKEN" \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello13"}],
        "kind": "message",
        "messageId": "550e8400-e29b-41d4-a716-446655440027",
        "contextId": "550e8400-e29b-41d4-a716-446655440027", 
        "taskId": "550e8400-e29b-41d4-a716-446655440041"
      },
      "configuration": {
        "acceptedOutputModes": ["application/json"]
      }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
  }'

echo ""
echo ""
echo "✅ Request completed"
