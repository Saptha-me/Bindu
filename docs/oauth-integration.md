# OAuth Integration Guide for Bindu Agents

This guide shows you how to add OAuth provider integrations to your Bindu agents, allowing them to access external services like Notion, Google Maps, Slack, and more.

## Overview

Bindu agents can require OAuth credentials for external services. When a user calls an agent that needs credentials they haven't authorized, Bindu automatically:
1. Returns an authorization URL
2. User authorizes the service
3. Bindu stores the credentials securely in Kratos
4. Future agent calls automatically inject the credentials

## Quick Start

### 1. Define Credential Requirements

Add `credential_requirements` to your agent config:

```python
config = {
    "author": "your@email.com",
    "name": "notion_search_agent",
    "description": "Search your Notion workspace",
    "credential_requirements": {
        "notion": {
            "type": "oauth2",
            "provider": "notion",
            "scopes": ["read_content", "search"],
            "required": True,
            "description": "Access your Notion workspace to search documents"
        }
    }
}
```

### 2. Use Credentials in Your Handler

Credentials are automatically injected into the handler context:

```python
async def handler(context):
    messages = context["messages"]
    credentials = context["credentials"]
    
    # Get Notion access token
    notion_token = credentials["notion"]["access_token"]
    
    # Use with Notion API or MCP server
    # ...
    
    return result
```

### 3. Configure OAuth Provider

Set up your OAuth application with the provider:

**Notion:**
1. Go to https://www.notion.so/my-integrations
2. Create new integration
3. Copy Client ID and Client Secret
4. Set redirect URI: `http://localhost:3773/oauth/callback/notion`

**Google:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Add redirect URI: `http://localhost:3773/oauth/callback/google`

Add credentials to `.env.hydra`:
```bash
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## Supported Providers

### Notion
```python
"notion": {
    "type": "oauth2",
    "provider": "notion",
    "scopes": ["read_content", "search"],
    "required": True
}
```

**Available Scopes:**
- `read_content` - Read pages and databases
- `search` - Search workspace
- `update_content` - Modify pages

### Google (Maps, Drive, etc.)
```python
"google": {
    "type": "oauth2",
    "provider": "google",
    "scopes": ["https://www.googleapis.com/auth/maps.readonly"],
    "required": True
}
```

**Common Scopes:**
- `https://www.googleapis.com/auth/maps.readonly` - Google Maps
- `https://www.googleapis.com/auth/drive.readonly` - Google Drive
- `https://www.googleapis.com/auth/gmail.readonly` - Gmail

### Slack
```python
"slack": {
    "type": "oauth2",
    "provider": "slack",
    "scopes": ["channels:read", "chat:write"],
    "required": True
}
```

**Common Scopes:**
- `channels:read` - Read channel info
- `chat:write` - Send messages
- `users:read` - Read user info

### GitHub
```python
"github": {
    "type": "oauth2",
    "provider": "github",
    "scopes": ["repo", "read:user"],
    "required": False  # Optional
}
```

**Common Scopes:**
- `repo` - Full repository access
- `read:user` - Read user profile
- `gist` - Create gists

## Multiple Providers

Agents can require multiple OAuth providers:

```python
config = {
    "credential_requirements": {
        "notion": {
            "type": "oauth2",
            "provider": "notion",
            "scopes": ["read_content"],
            "required": True
        },
        "google": {
            "type": "oauth2",
            "provider": "google",
            "scopes": ["https://www.googleapis.com/auth/maps.readonly"],
            "required": False  # Optional
        }
    }
}
```

## Using with MCP Servers

Bindu automatically injects credentials as environment variables for MCP servers:

```python
from bindu.mcp import CredentialInjector

async def handler(context):
    credentials = context["credentials"]
    
    # Get MCP server parameters with credentials
    server_params = CredentialInjector.get_server_params("notion", credentials["notion"])
    
    # Start MCP server
    async with ClientSession(server_params) as session:
        await session.initialize()
        result = await session.call_tool("notion_search", {
            "query": "project plans"
        })
    
    return result
```

## Error Handling

### Missing Credentials

If a user hasn't authorized a required provider:

```json
{
  "error": "authorization_required",
  "missing_providers": ["notion"],
  "authorization_urls": {
    "notion": "http://localhost:3773/oauth/authorize/notion"
  }
}
```

Your client should redirect the user to the authorization URL.

### Expired Credentials

Bindu automatically detects expired tokens and returns the same error as missing credentials.

### Handling in Code

```python
async def call_agent_with_retry(agent_url, message):
    response = await call_agent(agent_url, message)
    
    if response.get("error") == "authorization_required":
        # Show authorization URLs to user
        auth_urls = response["authorization_urls"]
        print(f"Please authorize: {auth_urls}")
        
        # Wait for user to authorize
        await wait_for_authorization()
        
        # Retry
        response = await call_agent(agent_url, message)
    
    return response
```

## Managing Connections

### List User's Connections

```bash
GET /oauth/connections
Authorization: Bearer <hydra_token>
```

Response:
```json
{
  "connections": [
    {
      "provider": "notion",
      "connected": true,
      "expires_at": "2025-12-16T12:00:00Z",
      "workspace_name": "My Workspace"
    },
    {
      "provider": "google",
      "connected": false
    }
  ]
}
```

### Revoke Connection

```bash
DELETE /oauth/connections/notion
Authorization: Bearer <hydra_token>
```

## Security Best Practices

1. **Minimal Scopes:** Request only the scopes your agent needs
2. **Required vs Optional:** Mark providers as `required: false` if not essential
3. **Token Refresh:** Bindu handles token refresh automatically
4. **Secure Storage:** Credentials are encrypted in Kratos

## Adding Custom Providers

To add a new OAuth provider:

1. **Add to MCP config** (`bindu/mcp/server_config.py`):
```python
MCP_SERVER_CONFIG["my_provider"] = {
    "package": "@modelcontextprotocol/server-my-provider",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-my-provider"],
    "env_vars": {
        "MY_PROVIDER_TOKEN": "access_token",
    },
}
```

2. **Add to OAuth routes** (`bindu/server/routes/oauth.py`):
```python
OAUTH_PROVIDERS["my_provider"] = {
    "authorize_url": "https://my-provider.com/oauth/authorize",
    "token_url": "https://my-provider.com/oauth/token",
    "scopes": ["read", "write"],
}
```

3. **Configure credentials:**
```bash
MY_PROVIDER_CLIENT_ID=...
MY_PROVIDER_CLIENT_SECRET=...
```

## Troubleshooting

### Authorization URL not working
- Check redirect URI matches in provider settings
- Verify client ID/secret in `.env.hydra`
- Check Kratos is running: `curl http://localhost:4433/health/ready`

### Credentials not injected
- Verify user authorized the provider
- Check `GET /oauth/connections` shows `connected: true`
- Check credential manager logs

### Token expired
- Bindu should auto-detect and request re-authorization
- Check token `expires_at` in connection info
- Manually revoke and re-authorize if needed

## Examples

See `examples/` directory for complete examples:
- `examples/notion_agent.py` - Notion integration
- `examples/google_maps_agent.py` - Google Maps integration
- `examples/multi_provider_agent.py` - Multiple providers

## Support

- Documentation: https://docs.getbindu.com
- Discord: https://discord.gg/3w5zuYUuwt
- GitHub: https://github.com/getbindu/Bindu
