# Hydra Authentication Migration - Implementation

This directory contains the implementation of Ory Hydra + Kratos authentication for Bindu.

## What's Been Implemented

### Phase 1: Infrastructure ✅
- **Docker Compose Stack** (`docker-compose.hydra.yml`)
  - PostgreSQL database
  - Ory Hydra (OAuth2 server)
  - Ory Kratos (Identity management)
  - MailSlurper (Email testing)

- **Configuration Files**
  - `config/hydra/clients.yml` - OAuth2 client configurations
  - `config/kratos/kratos.yml` - Kratos configuration
  - `config/kratos/identity.schema.json` - User identity schema
  - `config/kratos/oidc.*.jsonnet` - OIDC provider mappers
  - `.env.hydra.example` - Environment configuration template

### Phase 2: Core Authentication ✅
- **Hydra Client** (`bindu/auth/hydra_client.py`)
  - Token introspection
  - Token refresh
  - Token revocation
  - OAuth2 client management

- **Kratos Client** (`bindu/auth/kratos_client.py`)
  - Identity management
  - OAuth credential storage/retrieval
  - Token refresh checking
  - Connection management

- **Hydra Middleware** (`bindu/server/middleware/auth/hydra.py`)
  - OAuth2 token validation
  - User context extraction
  - M2M authentication support

### Phase 3: OAuth Credential Management ✅
- **OAuth Routes** (`bindu/server/routes/oauth.py`)
  - Authorization flow initiation
  - OAuth callback handling
  - Connection listing
  - Connection revocation

- **Credential Manager** (`bindu/penguin/credential_manager.py`)
  - Requirement checking
  - Credential retrieval
  - Context injection
  - Token expiration handling

### Phase 4: MCP Integration ✅
- **MCP Server Config** (`bindu/mcp/server_config.py`)
  - Provider-to-package mapping
  - Supported providers: Notion, Google, Slack, GitHub

- **Credential Injector** (`bindu/mcp/credential_injector.py`)
  - Environment variable building
  - MCP server parameter preparation

### Phase 5: Settings ✅
- **Hydra/Kratos Settings** (updated `bindu/settings.py`)
  - `HydraSettings` class
  - `KratosSettings` class
  - Feature flag: `use_hydra_auth`

## Quick Start

### 1. Start the Ory Stack

```bash
# Copy environment file
cp .env.hydra.example .env.hydra

# Edit .env.hydra with your OAuth provider credentials
# At minimum, set:
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - NOTION_CLIENT_ID
# - NOTION_CLIENT_SECRET

# Start services
docker-compose -f docker-compose.hydra.yml up -d

# Check services are healthy
docker-compose -f docker-compose.hydra.yml ps
```

### 2. Configure Your Agent

```python
# examples/notion_agent.py
from bindu.penguin.bindufy import bindufy

config = {
    "author": "your@email.com",
    "name": "notion_agent",
    "description": "Agent with Notion integration",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    
    # NEW: Credential requirements
    "credential_requirements": {
        "notion": {
            "type": "oauth2",
            "provider": "notion",
            "scopes": ["read_content"],
            "required": True,
            "description": "Access your Notion workspace"
        }
    }
}

# Handler with credential injection
async def handler(context):
    messages = context["messages"]
    credentials = context["credentials"]
    
    # Use Notion credentials
    notion_token = credentials["notion"]["access_token"]
    
    # Your agent logic here
    return result

bindufy(config, handler)
```

### 3. Enable Hydra Authentication

Set in your `.env` file:
```bash
USE_HYDRA_AUTH=true
HYDRA_ADMIN_URL=http://localhost:4445
KRATOS_ADMIN_URL=http://localhost:4434
```

## Next Steps (Not Yet Implemented)

### Phase 6: Testing
- [ ] Unit tests for Hydra middleware
- [ ] Unit tests for Kratos client
- [ ] Unit tests for credential manager
- [ ] Integration tests for OAuth flows
- [ ] E2E tests for complete auth flow

### Phase 7: Migration & Compatibility
- [ ] Compatibility layer for dual Auth0/Hydra support
- [ ] Database migration scripts
- [ ] User migration flow
- [ ] Deprecation warnings for Auth0

### Phase 8: Documentation
- [ ] User migration guide
- [ ] OAuth provider setup guide
- [ ] Developer documentation
- [ ] API documentation updates

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Request with token
       ▼
┌─────────────────────┐
│ HydraMiddleware     │
│ - Validate token    │
│ - Extract user info │
└──────┬──────────────┘
       │ 2. User authenticated
       ▼
┌─────────────────────┐
│ CredentialManager   │
│ - Check requirements│
│ - Fetch from Kratos │
└──────┬──────────────┘
       │ 3. Credentials ready
       ▼
┌─────────────────────┐
│ Agent Handler       │
│ - Execute with creds│
│ - Use MCP servers   │
└─────────────────────┘
```

## OAuth Flow

```
1. User calls agent → Missing credentials error
2. User clicks authorization URL
3. Redirected to OAuth provider
4. User authorizes → Callback to Bindu
5. Bindu exchanges code for tokens
6. Tokens stored in Kratos
7. User calls agent again → Success!
```

## Troubleshooting

### Services not starting
```bash
# Check logs
docker-compose -f docker-compose.hydra.yml logs

# Restart services
docker-compose -f docker-compose.hydra.yml restart
```

### Token validation failing
- Check Hydra is running: `curl http://localhost:4444/health/ready`
- Check token is valid: Use Hydra admin API to introspect
- Check middleware configuration in settings

### OAuth flow errors
- Verify OAuth client credentials in `.env.hydra`
- Check redirect URIs match in provider settings
- Review Kratos logs for identity errors

## Security Notes

⚠️ **Production Deployment**:
- Change all secrets in `.env.hydra`
- Use HTTPS for all URLs
- Enable rate limiting
- Use Redis for state storage (not in-memory)
- Encrypt database connections
- Regular security audits

## Support

For issues or questions:
- GitHub Issues: https://github.com/getbindu/Bindu/issues
- Discord: https://discord.gg/3w5zuYUuwt
