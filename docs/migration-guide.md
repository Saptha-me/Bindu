# Migrating from Auth0 to Hydra Authentication

This guide helps existing Bindu users migrate from Auth0 to Ory Hydra authentication.

## Overview

The migration process allows you to:
- Continue using Auth0 during the transition period
- Gradually migrate users to Hydra
- Maintain service continuity with zero downtime

## Migration Timeline

### Week 1-2: Parallel Operation
- Deploy Hydra alongside Auth0
- Test Hydra with internal users
- Both authentication systems active

### Week 3: Gradual Migration
- Enable Hydra for new users
- Provide migration path for existing users
- Auth0 remains active for existing sessions

### Week 4: Full Cutover
- Set `USE_HYDRA_AUTH=true` as default
- Deprecate Auth0 endpoints
- Remove Auth0 dependencies

## Prerequisites

1. **Backup your data**
   ```bash
   # Backup Auth0 user data
   # Backup database
   ```

2. **Deploy Ory stack**
   ```bash
   docker-compose -f docker-compose.hydra.yml up -d
   ```

3. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

## Step-by-Step Migration

### Step 1: Enable Compatibility Mode

Update your `.env` file:
```bash
# Enable dual-auth mode
USE_HYDRA_AUTH=true

# Hydra configuration
HYDRA_ADMIN_URL=http://localhost:4445
KRATOS_ADMIN_URL=http://localhost:4434
```

Update your application to use `CompatAuthMiddleware`:
```python
from bindu.server.middleware.auth.compat import CompatAuthMiddleware

# Instead of Auth0Middleware, use CompatAuthMiddleware
app.add_middleware(
    CompatAuthMiddleware,
    auth_config=auth0_config,  # Keep Auth0 config for fallback
    hydra_config=hydra_config,
)
```

### Step 2: User Migration Flow

**For Existing Auth0 Users:**

1. User logs in with Auth0 (still works)
2. Bindu shows migration prompt:
   ```
   "We've upgraded our authentication system! 
    Click here to migrate to the new system."
   ```
3. User clicks "Migrate to Hydra"
4. System creates Kratos account:
   - Email from Auth0 profile
   - Password reset email sent
5. Link existing data to new account
6. Auth0 session invalidated

**Migration API Endpoint:**
```python
# POST /api/migrate-to-hydra
# Headers: Authorization: Bearer <auth0_token>

async def migrate_to_hydra(request: Request):
    # 1. Verify Auth0 token
    auth0_user = request.state.user
    
    # 2. Create Kratos identity
    async with KratosClient() as kratos:
        identity = await kratos.create_identity({
            "traits": {
                "email": auth0_user["email"],
                "name": auth0_user.get("name"),
            }
        })
    
    # 3. Store migration mapping
    await db.execute(
        "INSERT INTO auth_migration (auth0_user_id, hydra_user_id) "
        "VALUES (:auth0_id, :hydra_id)",
        {
            "auth0_id": auth0_user["sub"],
            "hydra_id": identity["id"],
        }
    )
    
    # 4. Send password setup email
    # (Kratos handles this automatically)
    
    return {"status": "migration_initiated", "email": auth0_user["email"]}
```

### Step 3: Data Migration

**Migrate User Agents:**
```sql
-- Update agent ownership to Hydra user IDs
UPDATE user_agents ua
SET hydra_user_id = am.hydra_user_id
FROM auth_migration am
WHERE ua.auth0_user_id = am.auth0_user_id;
```

**Migrate OAuth Connections:**
```python
# If users had OAuth connections in Auth0, migrate to Kratos
async def migrate_oauth_connections(auth0_user_id: str, hydra_user_id: str):
    # Get Auth0 OAuth connections
    auth0_connections = await get_auth0_connections(auth0_user_id)
    
    # Store in Kratos
    async with KratosClient() as kratos:
        for provider, tokens in auth0_connections.items():
            await kratos.store_oauth_token(
                hydra_user_id,
                provider,
                tokens
            )
```

### Step 4: Verify Migration

**Check Migration Status:**
```sql
-- Count migrated users
SELECT 
    COUNT(*) as total_users,
    COUNT(hydra_user_id) as migrated_users,
    COUNT(*) - COUNT(hydra_user_id) as pending_users
FROM users;

-- View migration progress
SELECT 
    migration_status,
    COUNT(*) as count
FROM auth_migration
GROUP BY migration_status;
```

**Test Hydra Authentication:**
```bash
# Get Hydra token
curl -X POST http://localhost:4444/oauth2/token \
  -d "grant_type=password" \
  -d "username=user@example.com" \
  -d "password=userpassword" \
  -d "client_id=bindu-web" \
  -d "client_secret=<client_secret>"

# Test API with Hydra token
curl -X POST http://localhost:3773/ \
  -H "Authorization: Bearer <hydra_token>" \
  -d '{"jsonrpc":"2.0","method":"message/send",...}'
```

### Step 5: Disable Auth0 Fallback

After all users migrated (or migration deadline reached):

1. Update `.env`:
   ```bash
   # Disable Auth0 fallback
   USE_AUTH0_FALLBACK=false
   ```

2. Remove `CompatAuthMiddleware`, use `HydraMiddleware` only:
   ```python
   from bindu.server.middleware.auth.hydra import HydraMiddleware
   
   app.add_middleware(HydraMiddleware, auth_config=hydra_config)
   ```

3. Remove Auth0 dependencies:
   ```bash
   # Remove from pyproject.toml
   # Remove Auth0 environment variables
   ```

## Rollback Plan

If issues occur during migration:

1. **Immediate Rollback:**
   ```bash
   # Set in .env
   USE_HYDRA_AUTH=false
   ```
   This reverts to Auth0-only mode.

2. **Database Rollback:**
   ```bash
   alembic downgrade -1
   ```

3. **Service Rollback:**
   ```bash
   docker-compose -f docker-compose.hydra.yml down
   ```

## Troubleshooting

### Users Can't Login After Migration
- Check Kratos identity exists: `GET /admin/identities/{id}`
- Verify email in Kratos matches Auth0
- Check password was set (recovery email sent)

### OAuth Connections Lost
- Check Kratos identity traits for `oauth_connections`
- Re-authorize providers if needed
- Verify token expiration dates

### Performance Issues
- Check Hydra/Kratos are running: `docker-compose ps`
- Monitor token introspection latency
- Scale Hydra/Kratos if needed

## Post-Migration Cleanup

After 30 days of stable operation:

1. **Remove Auth0 Code:**
   ```bash
   rm bindu/server/middleware/auth/auth0.py
   rm bindu/server/middleware/auth/compat.py
   ```

2. **Clean Database:**
   ```sql
   -- Archive migration data
   CREATE TABLE auth_migration_archive AS 
   SELECT * FROM auth_migration;
   
   -- Drop migration table
   DROP TABLE auth_migration;
   
   -- Remove auth0_user_id columns
   ALTER TABLE users DROP COLUMN auth0_user_id;
   ```

3. **Update Documentation:**
   - Remove Auth0 references
   - Archive migration guide
   - Update API docs

## Support

For migration assistance:
- GitHub Issues: https://github.com/getbindu/Bindu/issues
- Discord: https://discord.gg/3w5zuYUuwt
- Email: raahul@getbindu.com
