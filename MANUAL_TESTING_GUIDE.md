# Manual Testing Guide for Hydra Authentication

## Prerequisites

1. ✅ Hydra services running (already done)
2. ✅ OAuth client registered (already done)
3. Need: A simple Bindu agent to test with

## Step 1: Create a Test Agent

Create `test_agent_hydra.py`:

```python
"""Simple test agent for Hydra authentication."""

from bindu.penguin.bindufy import bindufy

config = {
    "author": "test@example.com",
    "name": "hydra_test_agent",
    "description": "Test agent for Hydra authentication",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True
    }
}

async def handler(context):
    """Simple echo handler."""
    messages = context.get("messages", [])
    user = context.get("user", {})
    
    # Echo back user info
    response = f"""
✅ **Authentication Successful!**

**User Info:**
- Subject: {user.get('sub', 'N/A')}
- Client ID: {user.get('client_id', 'N/A')}
- Is M2M: {user.get('is_m2m', False)}
- Scopes: {user.get('scope', 'N/A')}

**Message:** {messages[-1]['parts'][0]['text'] if messages else 'No message'}
"""
    
    return {
        "role": "assistant",
        "parts": [{"kind": "text", "text": response}]
    }

if __name__ == "__main__":
    print("🚀 Starting Hydra Test Agent...")
    print("   URL: http://localhost:3773")
    print("   Auth: Hydra OAuth2")
    bindufy(config, handler)
```

## Step 2: Enable Hydra Authentication

Create/edit `.env` file in the project root:

```bash
# Enable Hydra authentication
USE_HYDRA_AUTH=true

# Hydra endpoints
HYDRA__ADMIN_URL=http://localhost:4445
HYDRA__PUBLIC_URL=http://localhost:4444

# Kratos endpoints (optional for now)
KRATOS__ADMIN_URL=http://localhost:4434
KRATOS__PUBLIC_URL=http://localhost:4433
```

## Step 3: Start the Test Agent

```bash
python test_agent_hydra.py
```

Expected output:
```
🚀 Starting Hydra Test Agent...
   URL: http://localhost:3773
   Auth: Hydra OAuth2
```

## Step 4: Get an Access Token

### Option A: Using Client Credentials (M2M)

```powershell
# Get token
$response = Invoke-WebRequest -Method POST -Uri "http://localhost:4444/oauth2/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=client_credentials&client_id=bindu-agent-m2m&client_secret=bindu_agent_m2m_secret_change_in_production&scope=agent:read agent:write"

$token = ($response.Content | ConvertFrom-Json).access_token
Write-Host "Token: $token"
```

### Option B: Using Python Script

```python
import httpx
import asyncio

async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:4444/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "bindu-agent-m2m",
                "client_secret": "bindu_agent_m2m_secret_change_in_production",
                "scope": "agent:read agent:write"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token_data = response.json()
        print(f"Access Token: {token_data['access_token']}")
        return token_data['access_token']

asyncio.run(get_token())
```

## Step 5: Test the Agent with Token

### Using PowerShell:

```powershell
# Call the agent
Invoke-WebRequest -Method POST -Uri "http://localhost:3773/" `
  -Headers @{"Authorization"="Bearer $token"; "Content-Type"="application/json"} `
  -Body '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Hello Hydra!"}]}},"id":"1"}'
```

### Using curl:

```bash
curl -X POST http://localhost:3773/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello Hydra!"}]
      }
    },
    "id": "1"
  }'
```

### Using Python:

```python
import httpx
import asyncio

async def test_agent(token):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:3773/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "Hello Hydra!"}]
                    }
                },
                "id": "1"
            }
        )
        print(response.json())

# Use the token from Step 4
token = "YOUR_TOKEN_HERE"
asyncio.run(test_agent(token))
```

## Step 6: Verify Authentication

**Expected Success Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "role": "assistant",
    "parts": [{
      "kind": "text",
      "text": "✅ **Authentication Successful!**\n\n**User Info:**\n- Subject: bindu-agent-m2m\n- Client ID: bindu-agent-m2m\n- Is M2M: true\n- Scopes: agent:read agent:write\n\n**Message:** Hello Hydra!"
    }]
  },
  "id": "1"
}
```

**Expected Failure (No Token):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32001,
    "message": "Authentication required"
  },
  "id": "1"
}
```

**Expected Failure (Invalid Token):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32002,
    "message": "Invalid token"
  },
  "id": "1"
}
```

## Step 7: Test Token Introspection

Verify the token is valid:

```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:4445/admin/oauth2/introspect" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "token=$token"
```

Expected response:
```json
{
  "active": true,
  "sub": "bindu-agent-m2m",
  "client_id": "bindu-agent-m2m",
  "scope": "agent:read agent:write",
  "exp": 1734509876,
  "iat": 1734506276
}
```

## Troubleshooting

### Agent Not Starting
- Check if port 3773 is available
- Verify Hydra services are running: `docker-compose -f docker-compose.hydra.yml ps`

### 401 Unauthorized
- Verify token is included in Authorization header
- Check token hasn't expired
- Verify `USE_HYDRA_AUTH=true` in `.env`

### 500 Internal Server Error
- Check agent logs for errors
- Verify Hydra is accessible: `curl http://localhost:4445/health/ready`

### Token Request Fails
- Verify client credentials are correct
- Check Hydra logs: `docker logs bindu-hydra`

## Next Steps

Once basic authentication works:
1. Test with OAuth credential requirements (Notion, Google)
2. Test token refresh
3. Test scope validation
4. Test M2M vs user tokens

## Quick Test Script

Save as `quick_test.py`:

```python
import httpx
import asyncio

async def full_test():
    async with httpx.AsyncClient() as client:
        # 1. Get token
        print("1. Getting token...")
        token_response = await client.post(
            "http://localhost:4444/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "bindu-agent-m2m",
                "client_secret": "bindu_agent_m2m_secret_change_in_production",
                "scope": "agent:read agent:write"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = token_response.json()["access_token"]
        print(f"✅ Token: {token[:50]}...")
        
        # 2. Call agent
        print("\n2. Calling agent...")
        agent_response = await client.post(
            "http://localhost:3773/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "Test message"}]
                    }
                },
                "id": "1"
            }
        )
        print(f"✅ Response: {agent_response.json()}")

asyncio.run(full_test())
```

Run: `python quick_test.py`
