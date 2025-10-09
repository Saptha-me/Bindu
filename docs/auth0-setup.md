# Auth0 Setup Guide for Bindu

This guide walks you through setting up Auth0 authentication for your Bindu agents.

## Your Auth0 Configuration

```
App Name:       bindu
Domain:         dev-tlzrol0zsxw40ujx.us.auth0.com
Client ID:      GGLemeiKL6MfXD7Hy4L4mtz8WNIhRtkS
Client Secret:  zXcdPIQRAM9iHzABZtcfaN_2iICW4pfuoyUChIcVDF5488ejtyKG_U_PyWj9kpJT
```

## Quick Start

### 1. Configure Your Agent

Use the provided configuration file:

```bash
cp examples/auth0_agent_config.json examples/my_agent_config.json
```

The config is already set up with your Auth0 credentials.

### 2. Configure Auth0 Application

In your Auth0 Dashboard (https://manage.auth0.com):

1. Go to **Applications** → **bindu**
2. Go to **Settings** tab
3. Configure the following:

   **Application URIs:**
   - Allowed Callback URLs: `http://localhost:8030/callback`
   - Allowed Logout URLs: `http://localhost:8030`
   - Allowed Web Origins: `http://localhost:8030`
   - Allowed Origins (CORS): `http://localhost:8030`

4. **Application Type:** Machine to Machine (M2M)

5. **Advanced Settings** → **Grant Types:**
   - ✅ Client Credentials (for M2M)
   - ✅ Authorization Code (for user login, optional)

6. Click **Save Changes**

### 3. Configure API in Auth0

1. Go to **Applications** → **APIs**
2. Click **Create API** (if you haven't already)
3. Configure:
   - **Name:** Bindu API
   - **Identifier:** `https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/`
   - **Signing Algorithm:** RS256

4. Go to **Permissions** tab and add:
   ```
   agent:read    - Read agent data and tasks
   agent:write   - Create and modify tasks
   agent:admin   - Administrative operations
   ```

5. Go to **Machine to Machine Applications** tab
6. Authorize your **bindu** application
7. Select the permissions you want to grant

### 4. Get an Access Token

Use the helper script to get a token:

```bash
python examples/get_auth0_token.py
```

This will output an access token you can use for testing.

### 5. Test Authentication

Start your agent:

```bash
python examples/agno_example.py examples/auth0_agent_config.json
```

Test with the token:

```bash
# Get token
TOKEN=$(python examples/get_auth0_token.py 2>/dev/null)

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tasks/list","params":{},"id":1}' \
     http://localhost:8030/

# Test public endpoint (no token needed)
curl http://localhost:8030/health
```

## Configuration Options

### Agent Config (`auth` section)

```json
{
  "auth": {
    "enabled": true,
    "provider": "auth0",
    "domain": "dev-tlzrol0zsxw40ujx.us.auth0.com",
    "audience": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/",
    "algorithms": ["RS256"],
    "issuer": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/",
    "jwks_uri": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/.well-known/jwks.json",
    "require_permissions": false,
    "public_endpoints": [
      "/health",
      "/agent.html",
      "/.well-known/*",
      "/did/resolve*",
      "/agent/info"
    ]
  }
}
```

### Configuration Fields

- **enabled**: Enable/disable authentication
- **provider**: Authentication provider (`auth0`, `dev`, `cognito`)
- **domain**: Your Auth0 domain
- **audience**: API identifier (must match Auth0 API)
- **algorithms**: Token signing algorithms (usually `["RS256"]`)
- **issuer**: Token issuer URL (your Auth0 domain)
- **jwks_uri**: JSON Web Key Set URL for signature verification
- **require_permissions**: Enforce permission checks
- **public_endpoints**: Endpoints that don't require authentication (glob patterns)

## Permission-Based Access Control

### Enable Permission Checks

Set `require_permissions: true` in your config and define endpoint permissions:

```json
{
  "auth": {
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

### How It Works

1. User/M2M app requests token from Auth0 with specific scopes
2. Auth0 issues token with granted permissions in `permissions` claim
3. Bindu validates token and checks if user has required permissions
4. Request is allowed/denied based on permissions

## Token Types

### M2M (Machine-to-Machine) Tokens

- Used for service-to-service communication
- Obtained via Client Credentials flow
- Subject (`sub`) ends with `@clients`
- Contains `permissions` or `scope` claim

```bash
# Get M2M token
python examples/get_auth0_token.py
```

### User Tokens

- Used for user authentication
- Obtained via Authorization Code flow (with browser)
- Subject (`sub`) is user ID (e.g., `auth0|123456`)
- Contains user profile claims (`email`, `name`, etc.)

## Troubleshooting

### "Invalid audience" Error

**Problem:** Token audience doesn't match configured audience.

**Solution:** Ensure `audience` in your config matches the API identifier in Auth0:
```json
"audience": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/"
```

### "Invalid signature" Error

**Problem:** Token signature verification failed.

**Solution:** 
1. Check that `domain` and `jwks_uri` are correct
2. Ensure token is from the correct Auth0 tenant
3. Verify `algorithms` includes `RS256`

### "Token expired" Error

**Problem:** Token has expired.

**Solution:** Get a new token using `get_auth0_token.py`

### "Insufficient permissions" Error

**Problem:** Token doesn't have required permissions.

**Solution:**
1. Check Auth0 API → Machine to Machine Applications
2. Ensure your app is authorized with required permissions
3. Or set `require_permissions: false` for testing

## Development vs Production

### Development (Localhost)

Option 1 - Disable auth:
```json
{"auth": {"enabled": false}}
```

Option 2 - Use dev middleware:
```json
{"auth": {"enabled": true, "provider": "dev"}}
```

Option 3 - Use Auth0 with localhost:
```json
{"auth": {"enabled": true, "provider": "auth0", ...}}
```

### Production

1. Use Auth0 with proper domain configuration
2. Enable HTTPS
3. Set `require_permissions: true`
4. Configure proper CORS origins
5. Use environment variables for secrets (don't commit!)

```bash
export AUTH0_DOMAIN="dev-tlzrol0zsxw40ujx.us.auth0.com"
export AUTH0_CLIENT_ID="GGLemeiKL6MfXD7Hy4L4mtz8WNIhRtkS"
export AUTH0_CLIENT_SECRET="your-secret-here"
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Use HTTPS in production** - Required for secure token transmission
3. **Enable permission checks** - Set `require_permissions: true`
4. **Rotate secrets regularly** - Update client secrets periodically
5. **Monitor token usage** - Check Auth0 logs for suspicious activity
6. **Use short token expiry** - Default is 24 hours, consider shorter for sensitive operations
7. **Validate audience** - Always set correct audience to prevent token misuse

## Additional Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Auth0 Python SDK](https://github.com/auth0/auth0-python)
- [JWT.io](https://jwt.io) - Decode and inspect tokens
- [Auth0 Dashboard](https://manage.auth0.com)
