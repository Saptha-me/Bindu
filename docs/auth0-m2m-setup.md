# Auth0 M2M Authentication Setup Guide

This guide explains how to set up Auth0 Machine-to-Machine (M2M) authentication for your Bindu agents.

## Table of Contents

1. [Overview](#overview)
2. [Auth0 Setup](#auth0-setup)
3. [Agent Configuration](#agent-configuration)
4. [Client Implementation](#client-implementation)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Overview

Bindu supports Auth0 authentication for securing agent endpoints. This is particularly useful for:

- **M2M Communication**: Service-to-service authentication
- **User Authentication**: End-user access control
- **Permission-Based Access**: Fine-grained control over operations
- **Audit Trail**: Track which service/user performed which action

### Architecture

```
Client Service
  ↓
  1. Request token from Auth0
  ↓
Auth0
  ↓
  2. Return JWT access token
  ↓
Client Service
  ↓
  3. Send request with token to Bindu Agent
  ↓
Bindu Agent (Auth0Middleware)
  ↓
  4. Validate token signature & claims
  ↓
  5. Check permissions (if required)
  ↓
  6. Process request
```

---

## Auth0 Setup

### Step 1: Create Auth0 Account

1. Go to [auth0.com](https://auth0.com) and sign up
2. Create a new tenant (e.g., `your-company`)
3. Your Auth0 domain will be: `your-company.auth0.com`

### Step 2: Create an API

1. Navigate to **Applications → APIs**
2. Click **Create API**
3. Fill in the details:
   - **Name**: `Bindu Agent API`
   - **Identifier**: `https://api.bindu.ai` (this is your audience)
   - **Signing Algorithm**: `RS256`
4. Click **Create**

### Step 3: Define Permissions (Optional)

If you want permission-based access control:

1. In your API settings, go to **Permissions** tab
2. Add permissions:
   - `agent:read` - Read tasks, contexts, agent info
   - `agent:write` - Send messages, create tasks
   - `agent:admin` - Cancel tasks, clear contexts
3. Click **Add**

### Step 4: Create M2M Application

1. Navigate to **Applications → Applications**
2. Click **Create Application**
3. Fill in the details:
   - **Name**: `Bindu M2M Client` (or your service name)
   - **Type**: Select **Machine to Machine Applications**
4. Click **Create**
5. Select your API (`Bindu Agent API`)
6. Select permissions (if using permission-based access)
7. Click **Authorize**

### Step 5: Get Credentials

1. Go to your M2M application settings
2. Copy the following:
   - **Domain**: `your-company.auth0.com`
   - **Client ID**: `abc123xyz789...`
   - **Client Secret**: `supersecret...` (keep this secure!)
   - **Audience**: `https://api.bindu.ai`

---

## Agent Configuration

### Basic Configuration (Auth Disabled)

```json
{
  "author": "your-email@example.com",
  "name": "My Agent",
  "description": "A simple agent",
  "auth": {
    "enabled": false
  },
  "deployment": {
    "url": "http://localhost:8030"
  },
  "storage": {"type": "memory"},
  "scheduler": {"type": "memory"},
  "capabilities": {}
}
```

### Secure Configuration (Auth Enabled)

```json
{
  "author": "your-email@example.com",
  "name": "Secure Agent",
  "description": "An agent with Auth0 authentication",
  "auth": {
    "enabled": true,
    "domain": "your-company.auth0.com",
    "audience": "https://api.bindu.ai",
    "algorithms": ["RS256"],
    "issuer": "https://your-company.auth0.com/",
    "require_permissions": false
  },
  "deployment": {
    "url": "http://localhost:8030"
  },
  "storage": {"type": "memory"},
  "scheduler": {"type": "memory"},
  "capabilities": {}
}
```

### With Permission-Based Access Control

```json
{
  "auth": {
    "enabled": true,
    "domain": "your-company.auth0.com",
    "audience": "https://api.bindu.ai",
    "algorithms": ["RS256"],
    "require_permissions": true,
    "permissions": {
      "message/send": ["agent:write"],
      "tasks/get": ["agent:read"],
      "tasks/cancel": ["agent:write"],
      "tasks/list": ["agent:read"],
      "contexts/list": ["agent:read"],
      "tasks/feedback": ["agent:write"]
    }
  }
}
```

### Public Endpoints

These endpoints are always public (no authentication required):

- `/.well-known/agent.json` - Agent card
- `/did/resolve` - DID resolution
- `/agent/info` - Agent information

---

## Client Implementation

### Python Client

```python
import os
import time
import requests
from typing import Optional

class BinduM2MClient:
    def __init__(self):
        self.auth0_domain = os.getenv("AUTH0_DOMAIN")
        self.client_id = os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET")
        self.audience = os.getenv("AUTH0_AUDIENCE")
        self.agent_url = os.getenv("BINDU_AGENT_URL", "http://localhost:8030")

        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        current_time = time.time()

        # Return cached token if still valid (5 min buffer)
        if self._token and self._token_expires_at > (current_time + 300):
            return self._token

        # Request new token
        token_url = f"https://{self.auth0_domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials"
        }

        response = requests.post(token_url, json=payload)
        response.raise_for_status()

        token_data = response.json()
        self._token = token_data["access_token"]
        self._token_expires_at = current_time + token_data["expires_in"]

        return self._token

    def send_message(self, message: str, context_id: str = None):
        """Send message to Bindu agent."""
        token = self._get_token()

        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "context_id": context_id,
                    "parts": [{"text": message}],
                    "role": "user"
                }
            },
            "id": f"req-{int(time.time())}"
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(self.agent_url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

# Usage
if __name__ == "__main__":
    client = BinduM2MClient()
    result = client.send_message("Hello, secure agent!")
    print(result)
```

### Environment Variables

```bash
# .env file
AUTH0_DOMAIN=your-company.auth0.com
AUTH0_CLIENT_ID=abc123xyz789
AUTH0_CLIENT_SECRET=supersecretvalue
AUTH0_AUDIENCE=https://api.bindu.ai
BINDU_AGENT_URL=http://localhost:8030
```

### Node.js Client

```javascript
const axios = require('axios');

class BinduM2MClient {
  constructor() {
    this.auth0Domain = process.env.AUTH0_DOMAIN;
    this.clientId = process.env.AUTH0_CLIENT_ID;
    this.clientSecret = process.env.AUTH0_CLIENT_SECRET;
    this.audience = process.env.AUTH0_AUDIENCE;
    this.agentUrl = process.env.BINDU_AGENT_URL || 'http://localhost:8030';

    this.token = null;
    this.tokenExpiresAt = 0;
  }

  async getToken() {
    const currentTime = Date.now() / 1000;

    if (this.token && this.tokenExpiresAt > (currentTime + 300)) {
      return this.token;
    }

    const tokenUrl = `https://${this.auth0Domain}/oauth/token`;
    const response = await axios.post(tokenUrl, {
      client_id: this.clientId,
      client_secret: this.clientSecret,
      audience: this.audience,
      grant_type: 'client_credentials'
    });

    this.token = response.data.access_token;
    this.tokenExpiresAt = currentTime + response.data.expires_in;

    return this.token;
  }

  async sendMessage(message, contextId = null) {
    const token = await this.getToken();

    const payload = {
      jsonrpc: '2.0',
      method: 'message/send',
      params: {
        message: {
          context_id: contextId,
          parts: [{ text: message }],
          role: 'user'
        }
      },
      id: `req-${Date.now()}`
    };

    const response = await axios.post(this.agentUrl, payload, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data;
  }
}

// Usage
const client = new BinduM2MClient();
client.sendMessage('Hello, secure agent!').then(console.log);
```

---

## Testing

### 1. Start Agent with Auth Disabled

```bash
python agno_example.py
```

Test without authentication:
```bash
curl -X POST http://localhost:8030/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "parts": [{"text": "Hello"}],
        "role": "user"
      }
    },
    "id": "test-1"
  }'
```

### 2. Enable Auth in Config

Update `agent_with_auth_config.json`:
```json
{
  "auth": {
    "enabled": true,
    "domain": "your-company.auth0.com",
    "audience": "https://api.bindu.ai"
  }
}
```

### 3. Test Without Token (Should Fail)

```bash
curl -X POST http://localhost:8030/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {"message": {"parts": [{"text": "Hello"}], "role": "user"}},
    "id": "test-2"
  }'
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32001,
    "message": "Authentication required"
  },
  "id": null
}
```

### 4. Get Token from Auth0

```bash
curl -X POST https://your-company.auth0.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.bindu.ai",
    "grant_type": "client_credentials"
  }'
```

### 5. Test With Valid Token (Should Succeed)

```bash
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8030/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {"message": {"parts": [{"text": "Hello"}], "role": "user"}},
    "id": "test-3"
  }'
```

---

## Troubleshooting

### Error: "Authentication required"

**Cause**: No Authorization header or invalid format

**Solution**: Include header: `Authorization: Bearer <token>`

### Error: "Invalid token signature"

**Cause**: Token signature verification failed

**Solutions**:
- Check that `domain` in config matches Auth0 tenant
- Verify `audience` matches API identifier in Auth0
- Ensure token is not expired

### Error: "Token has expired"

**Cause**: Token expiration time (exp) has passed

**Solution**: Request a new token from Auth0

### Error: "Invalid audience"

**Cause**: Token audience doesn't match config

**Solutions**:
- Verify `audience` in agent config matches Auth0 API identifier
- Check that token was requested with correct audience

### Error: "Insufficient permissions"

**Cause**: Token doesn't have required permissions

**Solutions**:
- Check M2M application has required permissions in Auth0
- Verify `require_permissions` is set correctly in config
- Review permission mappings in config

### Agent Won't Start

**Cause**: Invalid auth configuration

**Solutions**:
- Verify `domain` format: `your-tenant.auth0.com`
- Verify `audience` format: `https://api.your-domain.com`
- Check for typos in configuration
- Review logs for specific error messages

---

## Security Best Practices

1. **Never commit secrets**: Use environment variables for credentials
2. **Use HTTPS in production**: Enforce SSL/TLS for all requests
3. **Rotate secrets regularly**: Update client secrets periodically
4. **Minimum permissions**: Grant only required permissions
5. **Monitor access**: Review Auth0 logs for suspicious activity
6. **Token caching**: Cache tokens to reduce Auth0 API calls
7. **Separate environments**: Use different Auth0 tenants for dev/staging/prod

---

## Next Steps

- [A2A Protocol Documentation](./hybrid-agent-pattern.md)
- [Orchestration Architecture](./orchestration-architecture.md)
- [Auth0 Documentation](https://auth0.com/docs)
