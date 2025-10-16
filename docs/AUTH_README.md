# Auth0 Authentication for Bindu Agents

Bindu supports Auth0 authentication to secure your AI agents with industry-standard OAuth 2.0 / JWT tokens.

## Quick Start

### 1. Enable Authentication

Update your agent config:

```json
{
  "author": "your-email@example.com",
  "name": "Secure Agent",
  "auth": {
    "enabled": true,
    "domain": "your-tenant.auth0.com",
    "audience": "https://api.bindu.ai"
  },
  "deployment": {"url": "http://localhost:8030"},
  "storage": {"type": "memory"},
  "scheduler": {"type": "memory"},
  "capabilities": {}
}
```

### 2. Get Auth0 Credentials

1. Create Auth0 account at [auth0.com](https://auth0.com)
2. Create an API with identifier: `https://api.bindu.ai`
3. Create M2M application and authorize it for your API
4. Copy: Domain, Client ID, Client Secret, Audience

### 3. Use Authenticated Client

```python
from examples.m2m_client_example import BinduM2MClient

# Set environment variables first
client = BinduM2MClient()
result = client.send_message("Hello, secure agent!")
print(result)
```

## Features

✅ **M2M Authentication** - Service-to-service auth with client credentials
✅ **JWT Validation** - Signature verification using JWKS
✅ **Permission-Based Access** - Fine-grained control over operations
✅ **Token Caching** - Automatic token refresh and caching
✅ **Public Endpoints** - Agent discovery and DID resolution remain public
✅ **Audit Trail** - Track which service/user performed which action

## Configuration Options

| Field | Required | Description |
|-------|----------|-------------|
| `enabled` | Yes | Enable/disable authentication |
| `domain` | Yes* | Auth0 tenant domain |
| `audience` | Yes* | API identifier |
| `algorithms` | No | JWT algorithms (default: `["RS256"]`) |
| `issuer` | No | Token issuer (auto-generated from domain) |
| `jwks_uri` | No | JWKS endpoint (auto-generated from domain) |
| `require_permissions` | No | Enable permission checking (default: `false`) |
| `permissions` | No | Permission mappings for JSON-RPC methods |

*Required when `enabled: true`

## Public Endpoints

These endpoints are always accessible without authentication:

- `/.well-known/agent.json` - Agent card (discovery)
- `/did/resolve` - DID resolution
- `/agent/info` - Agent information

## Protected Endpoints

These endpoints require valid JWT token:

- `POST /` - All JSON-RPC methods:
  - `message/send`
  - `tasks/get`
  - `tasks/cancel`
  - `tasks/list`
  - `contexts/list`
  - `tasks/feedback`

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32001 | Authentication required | No Authorization header |
| -32002 | Invalid token | Signature verification failed |
| -32003 | Insufficient permissions | Token lacks required permissions |
| -32004 | Token has expired | Token exp claim passed |

## Examples

- **Basic Config**: `examples/simple_agent_config.json` (auth disabled)
- **Secure Config**: `examples/agent_with_auth_config.json` (auth enabled)
- **Python Client**: `examples/m2m_client_example.py`

## Documentation

- [Full Setup Guide](./auth0-m2m-setup.md) - Complete Auth0 setup walkthrough
- [A2A Protocol](./hybrid-agent-pattern.md) - Agent-to-agent communication
- [Architecture](./orchestration-architecture.md) - System architecture

## Security Best Practices

1. ✅ Store credentials in environment variables
2. ✅ Use HTTPS in production
3. ✅ Rotate client secrets regularly
4. ✅ Grant minimum required permissions
5. ✅ Monitor Auth0 logs for suspicious activity
6. ✅ Cache tokens to reduce API calls
7. ✅ Use separate Auth0 tenants for dev/staging/prod

## Troubleshooting

### "Authentication required"
- Include header: `Authorization: Bearer <token>`

### "Invalid token signature"
- Verify `domain` and `audience` match Auth0 configuration
- Check token is not expired

### "Insufficient permissions"
- Verify M2M app has required permissions in Auth0
- Check permission mappings in agent config

See [Troubleshooting Guide](./auth0-m2m-setup.md#troubleshooting) for more details.

## Support

- [GitHub Issues](https://github.com/Saptha-me/Bindu/issues)
- [Auth0 Documentation](https://auth0.com/docs)
