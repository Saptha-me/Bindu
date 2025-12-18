#!/usr/bin/env bash
# Deployment script for Ory Hydra + Kratos stack

set -e

echo "🚀 Deploying Ory Stack for Bindu Authentication"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    echo "Please install docker-compose"
    exit 1
fi

echo ""
echo "📋 Pre-deployment checks..."

# Check if .env.hydra exists
if [ ! -f .env.hydra ]; then
    echo "⚠️  .env.hydra not found, creating from example..."
    cp .env.hydra.example .env.hydra
    echo "✅ Created .env.hydra - Please configure OAuth provider credentials"
    echo ""
    echo "Required configuration:"
    echo "  - GOOGLE_CLIENT_ID"
    echo "  - GOOGLE_CLIENT_SECRET"
    echo "  - NOTION_CLIENT_ID"
    echo "  - NOTION_CLIENT_SECRET"
    echo ""
    read -p "Press Enter after configuring .env.hydra..."
fi

echo ""
echo "🐳 Starting Ory services..."

# Start services
docker-compose -f docker-compose.hydra.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
until docker-compose -f docker-compose.hydra.yml exec -T postgres pg_isready -U bindu > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo " ✅"

# Wait for Hydra
echo -n "Waiting for Hydra..."
until curl -s http://localhost:4444/health/ready > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo " ✅"

# Wait for Kratos
echo -n "Waiting for Kratos..."
until curl -s http://localhost:4433/health/ready > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo " ✅"

echo ""
echo "✅ Ory stack deployed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.hydra.yml ps

echo ""
echo "🔗 Service URLs:"
echo "  - Hydra Public:  http://localhost:4444"
echo "  - Hydra Admin:   http://localhost:4445"
echo "  - Kratos Public: http://localhost:4433"
echo "  - Kratos Admin:  http://localhost:4434"
echo "  - MailSlurper:   http://localhost:4436"
echo ""
echo "📝 Next steps:"
echo "  1. Test health endpoints:"
echo "     curl http://localhost:4444/health/ready"
echo "     curl http://localhost:4433/health/ready"
echo ""
echo "  2. Enable Hydra in your .env:"
echo "     USE_HYDRA_AUTH=true"
echo ""
echo "  3. Run example agent:"
echo "     python examples/notion_agent_example.py"
echo ""
echo "  4. View logs:"
echo "     docker-compose -f docker-compose.hydra.yml logs -f"
echo ""
echo "🎉 Deployment complete!"
