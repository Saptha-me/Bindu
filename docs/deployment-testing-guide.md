# Deployment and Testing Guide

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Python 3.12+
- OAuth provider credentials (Google, Notion, etc.)

### 1. Deploy Ory Stack

**Windows (PowerShell):**
```powershell
.\scripts\deploy-ory-stack.ps1
```

**Linux/Mac (Bash):**
```bash
chmod +x scripts/deploy-ory-stack.sh
./scripts/deploy-ory-stack.sh
```

**Manual Deployment:**
```bash
# Start Docker Desktop first!

# Start services
docker-compose -f docker-compose.hydra.yml up -d

# Check status
docker-compose -f docker-compose.hydra.yml ps

# View logs
docker-compose -f docker-compose.hydra.yml logs -f
```

### 2. Configure OAuth Providers

Edit `.env.hydra` with your credentials:

```bash
# Google OAuth (get from https://console.cloud.google.com)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Notion OAuth (get from https://www.notion.so/my-integrations)
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
```

### 3. Enable Hydra Authentication

In your `.env` file:
```bash
USE_HYDRA_AUTH=true
HYDRA_ADMIN_URL=http://localhost:4445
KRATOS_ADMIN_URL=http://localhost:4434
```

### 4. Test with Example Agent

```bash
python examples/notion_agent_example.py
```

## Testing OAuth Flows

### Manual Testing

1. **Start the example agent:**
   ```bash
   python examples/notion_agent_example.py
   ```

2. **Get a Hydra token:**
   ```bash
   # Register user via Kratos
   curl http://localhost:4433/self-service/registration/browser
   
   # Login and get token
   curl -X POST http://localhost:4444/oauth2/token \
     -d "grant_type=password" \
     -d "username=user@example.com" \
     -d "password=yourpassword" \
     -d "client_id=bindu-web" \
     -d "client_secret=bindu_web_client_secret_change_in_production"
   ```

3. **Call agent without credentials:**
   ```bash
   curl -X POST http://localhost:3773/ \
     -H "Authorization: Bearer <your_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "method": "message/send",
       "params": {
         "message": {
           "role": "user",
           "parts": [{"kind": "text", "text": "Search Notion"}]
         }
       },
       "id": "1"
     }'
   ```

   **Expected response:**
   ```json
   {
     "error": "authorization_required",
     "missing_providers": ["notion"],
     "authorization_urls": {
       "notion": "http://localhost:3773/oauth/authorize/notion"
     }
   }
   ```

4. **Authorize Notion:**
   - Open the authorization URL in your browser
   - Authorize the integration
   - You'll be redirected back

5. **Call agent again:**
   - Same curl command as step 3
   - Should now succeed with Notion credentials injected

### Automated Testing

Run the test suite (when Docker is running):

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# All tests with coverage
pytest tests/ -v --cov=bindu --cov-report=html
```

## Monitoring and Debugging

### Check Service Health

```bash
# Hydra
curl http://localhost:4444/health/ready

# Kratos
curl http://localhost:4433/health/ready

# PostgreSQL
docker-compose -f docker-compose.hydra.yml exec postgres pg_isready -U bindu
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.hydra.yml logs -f

# Specific service
docker-compose -f docker-compose.hydra.yml logs -f hydra
docker-compose -f docker-compose.hydra.yml logs -f kratos
```

### Common Issues

**Docker not running:**
```
Error: Cannot connect to Docker daemon
Solution: Start Docker Desktop
```

**Port already in use:**
```
Error: Port 4444 is already allocated
Solution: Stop conflicting service or change port in docker-compose.hydra.yml
```

**OAuth callback fails:**
```
Error: Invalid redirect URI
Solution: Check redirect URI matches in OAuth provider settings
```

## Performance Testing

### Token Validation Latency

```bash
# Use Apache Bench
ab -n 1000 -c 10 -H "Authorization: Bearer <token>" http://localhost:3773/

# Target: p99 < 50ms
```

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class BinduUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def call_agent(self):
        self.client.post("/", 
            json={
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "test"}]}},
                "id": "1"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
EOF

# Run load test
locust -f locustfile.py --host=http://localhost:3773
```

## Migration Testing

### Test Dual-Auth Mode

1. **Enable compatibility mode:**
   ```python
   from bindu.server.middleware.auth.compat import CompatAuthMiddleware
   
   app.add_middleware(
       CompatAuthMiddleware,
       auth_config=auth0_config,
       hydra_config=hydra_config
   )
   ```

2. **Test with Auth0 token:**
   ```bash
   curl -X POST http://localhost:3773/ \
     -H "Authorization: Bearer <auth0_token>" \
     -d '...'
   ```

3. **Test with Hydra token:**
   ```bash
   curl -X POST http://localhost:3773/ \
     -H "Authorization: Bearer <hydra_token>" \
     -d '...'
   ```

Both should work!

## Production Deployment

### Pre-deployment Checklist

- [ ] Change all secrets in `.env.hydra`
- [ ] Configure HTTPS for all URLs
- [ ] Set up Redis for state storage
- [ ] Enable rate limiting
- [ ] Configure backup for PostgreSQL
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Test disaster recovery

### Deployment Steps

1. **Deploy to staging:**
   ```bash
   # Use production docker-compose
   docker-compose -f docker-compose.hydra.prod.yml up -d
   ```

2. **Run smoke tests:**
   ```bash
   pytest tests/e2e/ --env=staging
   ```

3. **Monitor for 24 hours:**
   - Check error rates
   - Monitor latency
   - Review logs

4. **Deploy to production:**
   - Blue-green deployment
   - Gradual rollout (10% → 50% → 100%)
   - Monitor metrics

## Rollback Plan

If issues occur:

1. **Immediate rollback:**
   ```bash
   # Disable Hydra
   USE_HYDRA_AUTH=false
   
   # Restart services
   docker-compose restart
   ```

2. **Database rollback:**
   ```bash
   alembic downgrade -1
   ```

3. **Full rollback:**
   ```bash
   docker-compose -f docker-compose.hydra.yml down
   # Revert to previous deployment
   ```

## Next Steps

### Immediate
- ✅ Deploy Ory stack locally
- ✅ Test OAuth flows with Notion
- ⏳ Implement actual test files

### Short-term
- Monitor performance metrics
- Gather user feedback
- Migrate internal users

### Long-term
- Deprecate Auth0 completely
- Add more OAuth providers
- Implement automatic token refresh
