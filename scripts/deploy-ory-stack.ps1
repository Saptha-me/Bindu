# Deploy Ory Stack (PowerShell)
# Windows deployment script for Ory Hydra + Kratos

Write-Host "🚀 Deploying Ory Stack for Bindu Authentication" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Error: Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

Write-Host "📋 Pre-deployment checks..." -ForegroundColor Yellow
Write-Host ""

# Check if .env.hydra exists
if (-not (Test-Path .env.hydra)) {
    Write-Host "⚠️  .env.hydra not found, creating from example..." -ForegroundColor Yellow
    Copy-Item .env.hydra.example .env.hydra
    Write-Host "✅ Created .env.hydra" -ForegroundColor Green
    Write-Host ""
    Write-Host "Required configuration:" -ForegroundColor Cyan
    Write-Host "  - GOOGLE_CLIENT_ID"
    Write-Host "  - GOOGLE_CLIENT_SECRET"
    Write-Host "  - NOTION_CLIENT_ID"
    Write-Host "  - NOTION_CLIENT_SECRET"
    Write-Host ""
    Read-Host "Press Enter after configuring .env.hydra"
}

Write-Host ""
Write-Host "🐳 Starting Ory services..." -ForegroundColor Cyan

# Start services
docker-compose -f docker-compose.hydra.yml up -d

Write-Host ""
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow

# Wait for Hydra
Write-Host -NoNewline "Waiting for Hydra..."
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4444/health/ready" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host " ✅" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for Kratos
Write-Host -NoNewline "Waiting for Kratos..."
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4433/health/ready" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host " ✅" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 2
    $attempt++
}

Write-Host ""
Write-Host "✅ Ory stack deployed successfully!" -ForegroundColor Green
Write-Host ""

Write-Host "📊 Service Status:" -ForegroundColor Cyan
docker-compose -f docker-compose.hydra.yml ps

Write-Host ""
Write-Host "🔗 Service URLs:" -ForegroundColor Cyan
Write-Host "  - Hydra Public:  http://localhost:4444"
Write-Host "  - Hydra Admin:   http://localhost:4445"
Write-Host "  - Kratos Public: http://localhost:4433"
Write-Host "  - Kratos Admin:  http://localhost:4434"
Write-Host "  - MailSlurper:   http://localhost:4436"

Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test health endpoints:"
Write-Host "     Invoke-WebRequest http://localhost:4444/health/ready"
Write-Host "     Invoke-WebRequest http://localhost:4433/health/ready"
Write-Host ""
Write-Host "  2. Enable Hydra in your .env:"
Write-Host "     USE_HYDRA_AUTH=true"
Write-Host ""
Write-Host "  3. Run example agent:"
Write-Host "     python examples/notion_agent_example.py"
Write-Host ""
Write-Host "  4. View logs:"
Write-Host "     docker-compose -f docker-compose.hydra.yml logs -f"
Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
