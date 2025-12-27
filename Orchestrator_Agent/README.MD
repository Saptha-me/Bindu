> **Note:** This is the README for the Bindu Orchestrator Engine, a component of the main [Bindu project](https://github.com/Saptha-me/Bindu). For setup, contribution guidelines, and overall project information, please refer to the [main README file](../README.md).

Bindu Orchestrator Engine
Production-Ready Multi-Agent Task Orchestration System

🎯 Overview
Bindu Orchestrator Engine is a complete, production-ready multi-agent orchestration system that enables:

✅ Automatic task decomposition by capability

✅ Agent discovery & capability matching (DID-based)

✅ Price negotiation (X402 protocol)

✅ Parallel task execution (A2A protocol)

✅ Result aggregation from multiple agents

✅ Autonomous payment settlement

✅ Cost optimization strategies

✅ Real-time monitoring with Prometheus

✅ Complete test coverage (45+ tests)

🏗️ Architecture
text
┌─────────────────────────────────────────────────────────────┐
│                    Bindu Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Task Submission                                        │
│     ↓                                                       │
│  2. Task Decomposition (TaskDecomposer)                    │
│     ↓                                                       │
│  3. Agent Discovery (AgentRegistry)                        │
│     ↓                                                       │
│  4. Price Negotiation (AgentNegotiator - X402)             │
│     ↓                                                       │
│  5. Task Execution (AgentExecutor - A2A)                   │
│     ↓                                                       │
│  6. Result Aggregation (ResultAggregator)                  │
│     ↓                                                       │
│  7. Payment Settlement (PaymentHandler - X402)             │
│     ↓                                                       │
│  Database (PostgreSQL) + Cache (Redis)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘

🚀 Quick Start
To run the Orchestrator Engine, please see the main project's [contributing guidelines](../.github/contributing.md) for instructions on how to set up the development environment and run the services using Docker Compose.

📡 API Endpoints
Health & Status
bash
GET /health              # Basic health check
GET /status              # Detailed service status
GET /metrics             # Prometheus metrics
Task Management
bash
POST /tasks/submit       # Submit new task
POST /tasks/execute      # Execute orchestration workflow
Submit Task Example:

bash
curl -X POST http://localhost:8000/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Market Research Report",
    "description": "Research and analyze AI market trends",
    "required_capabilities": ["web-research", "data-analysis", "text-generation"],
    "max_budget": 100.0,
    "deadline_hours": 24
  }'
Agent Management
bash
GET /agents              # List all agents
GET /agents/search       # Search by capability
⚙️ Configuration
Environment Variables (.env)
bash
# Orchestrator
ORCHESTRATOR_DID=did:bindu:orchestrator:main:001
BINDU_ENV=production
LOG_LEVEL=INFO

# Database
POSTGRES_USER=bindu
POSTGRES_PASSWORD=your_password
DB_URL=postgresql://bindu:password@postgres:5432/orchestrator

# Cache
REDIS_URL=redis://redis:6379

# X402 Payment
X402_ENABLED=true
X402_SETTLEMENT_INTERVAL=3600
X402_AUTO_SETTLE=true

🔄 Complete Workflow Example
1. Submit Task
python
POST /tasks/submit
{
  "title": "Research AI Market Trends",
  "description": "Analyze current AI market size and growth",
  "required_capabilities": ["web-research", "data-analysis", "text-generation"],
  "max_budget": 100.0
}
2. Execute Workflow
python
POST /tasks/execute
{
  "task_id": "task_001"
}
Workflow Stages:

Decompose: Break into research → analysis → generation → verification

Discover: Find agents with matching capabilities

Negotiate: X402 price negotiation with each agent

Execute: A2A protocol task execution in parallel

Aggregate: Combine results from all agents

Settle: Autonomous X402 payment settlement

3. Monitor Execution
bash
# View real-time logs
docker-compose logs -f orchestrator

# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=up

# Access pgAdmin (database UI)
http://localhost:5050  (admin@bindu.io / admin)
🧪 Testing
Run All Tests
bash
pytest tests/ -v
pytest tests/ --cov=orchestrator  # With coverage
Run Specific Test Suite
bash
pytest tests/unit/ -v             # Unit tests (30 tests)
pytest tests/integration/ -v      # Integration tests (9 tests)
pytest tests/e2e/ -v              # End-to-end tests (6 tests)
Test Coverage
✅ 45+ test cases covering all components

✅ Unit tests for individual functions

✅ Integration tests for component interactions

✅ E2E tests for complete workflows

✅ 15 pytest fixtures for test setup

📊 Monitoring
Prometheus (http://localhost:9090)
Metrics automatically scraped:

Service uptime

Request latency

Agent success rates

Task completion rates

Cache hit/miss rates

pgAdmin (http://localhost:5050)
Database management UI:

Query builder

Database browser

SQL execution

Backup/restore

Application Logs
bash
docker-compose logs orchestrator      # Orchestrator logs
docker-compose logs postgres          # Database logs
docker-compose logs redis             # Cache logs
docker-compose logs prometheus        # Monitoring logs
🔒 Security Features
DID-Based Identity
✅ Ed25519 cryptographic keys

✅ DID specification compliant

✅ Agent authentication & verification

X402 Price Negotiation
✅ Secure agent-orchestrator negotiation

✅ Budget validation

✅ Quote acceptance/rejection

A2A Protocol Security
✅ Encrypted agent-agent communication

✅ Message authentication

✅ Request/response validation

Credential Management
✅ Secure API key storage

✅ .env isolation (git-ignored)

✅ Per-agent credentials

🚢 Deployment
The services in this directory are intended to be run via Docker Compose from the root of the project.

📈 Performance
Resource Requirements
Component	CPU	Memory	Notes
Orchestrator	2	2GB	Main service
PostgreSQL	2	2GB	Database
Redis	1	1GB	Cache
Total	~5	~5GB	Adjustable
Scalability
Horizontal: Add agent instances

Vertical: Increase resource limits

Caching: Redis layer improves response times

Async: FastAPI handles 10K+ concurrent requests

🤝 Contributing
Please refer to the main project's [contributing guidelines](../.github/contributing.md).

📚 Documentation
DEPLOYMENT.md - Production deployment guide

.bindu/README.md - Identity & DID setup

API Docs - http://localhost:8000/docs (Swagger UI)

Code Comments - Extensive inline documentation

🐛 Troubleshooting
Services not starting
bash
docker-compose logs        # Check error messages
docker-compose restart     # Restart services
docker-compose build --no-cache  # Rebuild images
Database connection errors
bash
docker exec bindu-postgres psql -U bindu -d orchestrator -c "SELECT 1"
Agent communication issues
bash
# This service does not manage agents directly. See the main project.
High memory usage
bash
docker stats                       # Check container usage
docker-compose down -v             # Reset volumes
📋 Requirements
Python: 3.11+

Docker: 20.10+

Docker Compose: 2.0+

PostgreSQL: 15 (via Docker)

Redis: 7 (via Docker)

📦 Dependencies
See `requirements.txt` for a complete list of dependencies.

📄 License
MIT License - See LICENSE file

🙋 Support
GitHub Issues: Report bugs

Documentation: Full docs

Community: Discord

Email: support@bindu.io

🎉 Features Checklist
Core Orchestration
✅ Task decomposition by capability

✅ Agent discovery & matching

✅ X402 price negotiation

✅ A2A protocol execution

✅ Result aggregation

✅ Payment settlement

Infrastructure
✅ PostgreSQL persistence

✅ Redis caching

✅ Prometheus monitoring

✅ pgAdmin UI

✅ Docker Compose setup

Quality
✅ 45+ test cases

✅ Type hints throughout

✅ Comprehensive logging

✅ Error handling

✅ Health checks

Security
✅ DID-based identity

✅ Ed25519 cryptography

✅ X402 security

✅ Credential isolation

✅ Audit logging

📌 Version
Current: v1.0.0
Status: Production Ready
Last Updated: December 2025