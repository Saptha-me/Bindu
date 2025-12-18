# Files Requiring OAuth Credentials Configuration

## Summary
To enable the full OAuth credential flow with Kratos, you need to configure real OAuth credentials from Google and Notion. Currently, placeholder values are causing Kratos to fail readiness checks.

---

## File 1: `config/kratos/kratos.yml`

**Location:** `c:\Users\user\PycharmProjects\Bindu\config\kratos\kratos.yml`

**Lines to Fix:** 37-57 (currently commented out)

**What to Change:**

### Google OAuth Provider (Lines 41-48)
```yaml
- id: google
  provider: google
  client_id: YOUR_GOOGLE_CLIENT_ID          # ← REPLACE THIS
  client_secret: YOUR_GOOGLE_CLIENT_SECRET  # ← REPLACE THIS
  mapper_url: file:///etc/config/kratos/oidc.google.jsonnet
  scope:
    - email
    - profile
```

**How to Get Google Credentials:**
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Web application)
3. Set authorized redirect URI: `http://localhost:4433/self-service/methods/oidc/callback/google`
4. Copy the Client ID and Client Secret

### Notion OAuth Provider (Lines 49-57)
```yaml
- id: notion
  provider: generic
  client_id: YOUR_NOTION_CLIENT_ID          # ← REPLACE THIS
  client_secret: YOUR_NOTION_CLIENT_SECRET  # ← REPLACE THIS
  issuer_url: https://api.notion.com/v1/oauth
  mapper_url: file:///etc/config/kratos/oidc.notion.jsonnet
  scope:
    - read_content
    - search
```

**How to Get Notion Credentials:**
1. Go to: https://www.notion.so/my-integrations
2. Create a new integration (Public integration)
3. Set OAuth redirect URI: `http://localhost:4433/self-service/methods/oidc/callback/notion`
4. Copy the OAuth client ID and OAuth client secret

### After Replacing Credentials

**Uncomment the OIDC section** (remove the `#` from lines 37-57):

```yaml
selfservice:
  methods:
    password:
      enabled: true
    oidc:  # ← Remove the # here
      enabled: true  # ← Remove the # here
      config:  # ← Remove the # here
        providers:  # ← Remove the # here
          # ... rest of the configuration
```

---

## File 2: `.env.hydra` (Optional but Recommended)

**Location:** `c:\Users\user\PycharmProjects\Bindu\.env.hydra`

**What to Add:**

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_actual_google_client_id
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret

# Notion OAuth  
NOTION_CLIENT_ID=your_actual_notion_client_id
NOTION_CLIENT_SECRET=your_actual_notion_client_secret

# Slack OAuth (optional)
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret

# GitHub OAuth (optional)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

**Note:** This file is for reference. The actual credentials need to go in `kratos.yml`.

---

## Quick Reference: OAuth Provider Setup

### Google OAuth 2.0
- **Console:** https://console.cloud.google.com/apis/credentials
- **Redirect URI:** `http://localhost:4433/self-service/methods/oidc/callback/google`
- **Scopes:** `email`, `profile`

### Notion OAuth
- **Console:** https://www.notion.so/my-integrations
- **Redirect URI:** `http://localhost:4433/self-service/methods/oidc/callback/notion`
- **Scopes:** `read_content`, `search`

### Slack OAuth (Future)
- **Console:** https://api.slack.com/apps
- **Redirect URI:** `http://localhost:4433/self-service/methods/oidc/callback/slack`

### GitHub OAuth (Future)
- **Console:** https://github.com/settings/developers
- **Redirect URI:** `http://localhost:4433/self-service/methods/oidc/callback/github`

---

## After Configuration

### Step 1: Update `kratos.yml`
Replace placeholder credentials and uncomment the OIDC section.

### Step 2: Restart Kratos
```bash
docker-compose -f docker-compose.hydra.yml restart kratos
```

### Step 3: Verify Kratos is Healthy
```powershell
Invoke-WebRequest -Uri http://localhost:4433/health/ready -UseBasicParsing
# Should return: StatusCode 200
```

### Step 4: Test OAuth Flow
```bash
# Visit the authorization URL
http://localhost:4433/self-service/registration/browser

# Or test with the OAuth test agent
python oauth_test_agent.py
```

---

## Current Status

**Before Configuration:**
- ❌ Kratos: Not ready (503 error)
- ❌ OAuth providers: Placeholder credentials
- ❌ OAuth flow: Not available

**After Configuration:**
- ✅ Kratos: Healthy (200 OK)
- ✅ OAuth providers: Real credentials
- ✅ OAuth flow: Fully functional

---

## Troubleshooting

### Issue: Kratos still not ready after configuration
**Solution:** Check Kratos logs for specific errors
```bash
docker logs bindu-kratos --tail 50
```

### Issue: OAuth redirect fails
**Solution:** Verify redirect URIs match exactly in provider console and Kratos config

### Issue: Invalid client credentials
**Solution:** Double-check client ID and secret are copied correctly (no extra spaces)

---

## Summary

**Only 1 file needs editing:** `config/kratos/kratos.yml`

**Changes needed:**
1. Replace `YOUR_GOOGLE_CLIENT_ID` with real Google client ID
2. Replace `YOUR_GOOGLE_CLIENT_SECRET` with real Google client secret  
3. Replace `YOUR_NOTION_CLIENT_ID` with real Notion client ID
4. Replace `YOUR_NOTION_CLIENT_SECRET` with real Notion client secret
5. Uncomment the OIDC section (remove `#` from lines 37-57)

**After editing, restart Kratos and it should become healthy!**
