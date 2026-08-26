# 🎯 Planner Agent - Multi-Agent Task Orchestrator

A **Bindu-native orchestration agent** that coordinates multiple specialized agents to complete complex tasks. This demonstrates the "Internet of Agents" vision where agents collaborate based on capabilities rather than working in isolation.

**Author:** Prachet Dev Singh (prachetdevsingh@gmail.com)

---

## What This Agent Does

The Planner Agent takes a complex user goal and:

1. **Decomposes** it into smaller sub-tasks
2. **Discovers** agents with the right capabilities
3. **Coordinates** execution across multiple agents
4. **Aggregates** results into a coherent response

**Example:**
```
User: "Create a summary of recent AI developments"

Planner Agent:
├─ Step 1: Research AI trends → Research Agent
├─ Step 2: Summarize findings → Summary Agent
└─ Returns: Aggregated final summary
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              User Request                       │
│   "Create a summary of AI developments"         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │  PLANNER AGENT     │
        │  (Orchestrator)    │
        └────────┬───────────┘
                 │
                 ├─────► Task Decomposer
                 │       (Breaks goal into steps)
                 │
                 ├─────► Agent Registry
                 │       (Finds capable agents)
                 │
                 ├─────► Executor
                 │       (Sends HTTP/JSON-RPC requests)
                 │
                 └─────► Aggregator
                         (Merges results)
```

---

## Key Features

### ✅ Bindu-Native Integration
- Uses `bindufy()` pattern for agent creation
- Skill-based architecture with YAML definitions
- Discovers agents via `/.well-known/agent.json`
- Compatible with Bindu frontend and directory

### ✅ Intelligent Orchestration
- **Task Decomposition:** Rule-based logic for breaking down goals (AI-ready for Claude/GPT)
- **Capability Matching:** Finds best agent for each sub-task based on skills
- **HTTP/JSON-RPC Communication:** Standard protocol for agent-to-agent messaging
- **Result Aggregation:** Combines outputs into user-friendly format

### ✅ Production Quality
- Comprehensive error handling (timeouts, connection failures, invalid responses)
- Detailed logging for debugging
- 13 unit tests with 100% pass rate
- Full documentation

---

## Project Structure

```
planner-agent/
├── planner_agent.py              # Main orchestrator
├── core/
│   ├── executor.py               # A2A communication (HTTP/JSON-RPC)
│   ├── task_decomposer.py        # Task breakdown logic
│   ├── agent_registry.py         # Capability-based discovery
│   └── aggregator.py             # Result merging
├── skills/
│   └── orchestration/
│       └── skill.yaml            # Planner's capabilities
├── mock_agents/                  # For testing
│   ├── research_agent.py         # Mock research worker
│   ├── summary_agent.py          # Mock summary worker
│   └── skills/                   # Worker skill definitions
├── tests/
│   ├── test_executor.py          # A2A communication tests
│   ├── test_decomposer.py        # Decomposition logic tests
│   └── test_registry.py          # Discovery tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Bindu installed (`uv sync` from repo root)

### Installation

```bash
cd examples/planner-agent

# Install dependencies
pip install -r requirements.txt

# Copy environment template (optional)
cp .env.example .env
```

### Running the Demo

**Terminal 1: Start Research Agent**
```bash
python mock_agents/research_agent.py
```
Output: `🤖 Research Agent running on http://localhost:3775`

**Terminal 2: Start Summary Agent**
```bash
python mock_agents/summary_agent.py
```
Output: `📝 Summary Agent running on http://localhost:3776`

**Terminal 3: Start Planner Agent**
```bash
python planner_agent.py
```
Output: `🎯 Planner Agent running on http://localhost:3774`

**Terminal 4: Test Orchestration**
```bash
curl -X POST http://localhost:3774/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "content": "Create a summary of recent AI developments"
      }
    },
    "id": 1
  }'
```

**Expected Console Output:**
```
🎯 Planner received goal: Create a summary of recent AI developments
📋 Decomposed into 2 sub-tasks:
   Step 1: Research and retrieve relevant information
   Step 2: Summarize the information
✅ Registered agent: research_agent at http://localhost:3775
✅ Registered agent: summary_agent at http://localhost:3776
🤖 Step 1 → research_agent
🤖 Step 2 → summary_agent
⚡ Executing 2 tasks...
   ✅ Step 1 completed
   ✅ Step 2 completed
✨ Orchestration complete!
```

---

## How It Works

### 1. Task Decomposition
The `TaskDecomposer` analyzes the user's goal and breaks it into steps:

```python
# Input: "Create a summary of AI trends"
# Output:
[
  {
    "step": 1,
    "description": "Research AI trends",
    "required_capabilities": ["research", "web_search"]
  },
  {
    "step": 2,
    "description": "Summarize findings",
    "required_capabilities": ["text_summarization"]
  }
]
```

### 2. Agent Discovery
The `AgentRegistry` queries each worker agent's capabilities:

```python
# GET http://localhost:3775/.well-known/agent.json
{
  "name": "research_agent",
  "skills": [
    {"capabilities": ["research", "web_search"]}
  ]
}

# Matches: Step 1 → Research Agent, Step 2 → Summary Agent
```

### 3. Task Execution
The `Executor` sends HTTP/JSON-RPC requests to matched agents:

```python
POST http://localhost:3775/
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {"role": "user", "content": "Research AI trends"}
  }
}
```

### 4. Result Aggregation
The `Aggregator` combines results from all agents:

```
✅ Orchestration Complete
Step 1: [Research findings...]
Step 2: [Summary of findings...]
*Orchestrated by Planner Agent*
```

---

## Testing

### Run Unit Tests

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/ -v
```

**Expected Output:**
```
===== 13 passed in 0.14s =====
✅ test_decompose_summary_task
✅ test_decompose_report_task
✅ test_execute_on_agent_success
✅ test_registry_initialization
... and 9 more
```

### Test Coverage
- **Task Decomposition:** 5 tests (summary, report, comparison, simple tasks)
- **Agent Communication:** 4 tests (success, timeout, connection error, invalid response)
- **Agent Discovery:** 4 tests

---

## Configuration

The agent is already configured with your email (`prachetdevsingh@gmail.com`). The only optional configuration is:

### Understanding Localhost vs Production

**What is Localhost?**
- `localhost` means "this computer" (your own machine)
- Used for **local testing and development**
- Each agent runs on a different **port** (3774, 3775, 3776) on your computer
- Think of it like: Your computer is a building, each port is a different apartment

**For This Assignment (Testing):**
```bash
# Default configuration - perfect for testing/demo
WORKER_AGENTS=http://localhost:3775,http://localhost:3776
```
✅ Reviewers will run the agents on **their own computer** - no changes needed!

**For Production Deployment (Future):**
When you deploy real agents to the internet, just update the environment variable:
```bash
# Example: Production with real URLs
WORKER_AGENTS=https://research-agent.myapp.com,https://summary-agent.myapp.com
```
✅ **No code changes required** - just update `.env` file!

### Environment Variables (Optional)

```bash
# Worker agent URLs (comma-separated)
# Default: http://localhost:3775,http://localhost:3776
WORKER_AGENTS=http://localhost:3775,http://localhost:3776

# Optional: AI API key for intelligent decomposition
ANTHROPIC_API_KEY=your_key_here
```

**Note:** The default localhost configuration is **perfect for the assignment**. Reviewers just run the 3 Python files - everything works automatically!

---

## Using with Bindu Frontend

1. Start all agents (planner + workers)
2. Start Bindu frontend:
   ```bash
   cd ../../frontend
   npm run dev
   ```
3. Navigate to `http://localhost:5173`
4. Select "Planner Agent" from dropdown
5. Send: `"Create a summary of AI trends"`

---

## Future Enhancements

### Dynamic Discovery
Integrate with [Bindu Directory](https://bindus.directory) for real-time agent discovery:

```python
from bindu.directory import discover_agents
agents = discover_agents(capabilities=["research"])
```

### AI-Powered Decomposition
Replace rule-based logic with Claude/GPT:

```python
# In task_decomposer.py
response = anthropic_client.messages.create(
    model="claude-sonnet-4",
    messages=[{"role": "user", "content": f"Break down: {goal}"}]
)
```

### Parallel Execution
Execute independent tasks concurrently:

```python
import asyncio
results = await asyncio.gather(
    execute_on_agent(agent1_url, task1),
    execute_on_agent(agent2_url, task2)
)
```

### Payment Integration
Add value exchange between agents:

```python
config = {
    "execution_cost": {"amount": "$0.001", "token": "USDC"}
}
```

---

## Troubleshooting

### Agent Connection Failed
**Error:** `Connection failed - agent may not be running`

**Solution:**
- Verify agents are running: `curl http://localhost:3775/.well-known/agent.json`
- Check `WORKER_AGENTS` environment variable
- Ensure no port conflicts

### No Agent Found
**Error:** `⚠️  No agent found for step X`

**Solution:**
- Verify worker agent skills match required capabilities
- Check `/.well-known/agent.json` returns valid skills
- Add mock agent with required capability

### Import Errors
**Error:** `ModuleNotFoundError: No module named 'bindu'`

**Solution:**
```bash
cd ../../  # Go to Bindu repo root
uv sync
```

---

## Why This Matters

This Planner Agent demonstrates:

1. ✅ **Agents can collaborate** - Not just respond to prompts
2. ✅ **Skill-based discovery** - Agents find each other dynamically
3. ✅ **Scalable architecture** - Easy to add new specialized agents
4. ✅ **Production-ready** - Error handling, testing, logging

**This is the foundation for the Internet of Agents.**

---

## Submission Guide

### Step 1: Fork the Bindu Repository

1. Go to https://github.com/getbindu/bindu
2. Click the **Fork** button (top right)
3. Wait for fork to complete

### Step 2: Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/bindu.git
cd bindu
```

### Step 3: Create Feature Branch

```bash
git checkout -b feat/planner-agent
```

### Step 4: Verify Files

The planner-agent folder is already in `examples/planner-agent/`. Verify all files are present:

```bash
ls examples/planner-agent/
```

You should see:
- `planner_agent.py`
- `core/` (4 modules)
- `skills/orchestration/`
- `mock_agents/` (2 agents + skills)
- `tests/` (3 test files)
- `README.md`
- `requirements.txt`
- `.env.example`

### Step 5: Commit Changes

```bash
git add examples/planner-agent/

git commit -m "feat: Add Planner Agent for multi-agent orchestration

Implements a Bindu-native orchestration agent that:
- Decomposes complex goals into sub-tasks
- Discovers agents via capability-based matching  
- Coordinates execution via HTTP/JSON-RPC
- Aggregates results into coherent output

Includes:
- 4 core modules (executor, decomposer, registry, aggregator)
- 2 mock worker agents for testing
- 13 unit tests (100% passing)
- Comprehensive documentation"
```

### Step 6: Push to Your Fork

```bash
git push origin feat/planner-agent
```

### Step 7: Create Pull Request

1. Go to your fork: `https://github.com/YOUR_USERNAME/bindu`
2. Click **"Compare & pull request"** button
3. Use this PR description:

```markdown
## feat: Add Planner Agent for Multi-Agent Task Orchestration

### Summary
Implements a Bindu-native Planner Agent that orchestrates complex tasks across multiple specialized agents, demonstrating the "Internet of Agents" vision.

### Architecture
User Goal → Task Decomposer → Agent Registry → Worker Agents → Aggregator → Final Result

### Features
✅ **Bindu Integration**
- Uses bindufy() pattern
- Skill-based agent discovery via /.well-known/agent.json
- Compatible with Bindu Directory
- Works with Bindu frontend

✅ **Orchestration Capabilities**
- Rule-based task decomposition (AI-ready)
- Capability-based agent matching
- HTTP/JSON-RPC agent communication
- Intelligent result aggregation

✅ **Production Quality**
- Comprehensive error handling
- 13 unit tests (100% pass rate)
- Detailed logging and documentation

### Testing
```bash
cd examples/planner-agent
pytest tests/ -v
# Result: 13 passed ✅
```

### Files Added
- `planner_agent.py` - Main orchestrator
- `core/executor.py` - A2A communication
- `core/task_decomposer.py` - Task breakdown
- `core/agent_registry.py` - Agent discovery
- `core/aggregator.py` - Result merging
- `skills/orchestration/skill.yaml`
- `mock_agents/` - 2 test agents with skills
- `tests/` - 13 test cases
- `README.md` - Complete documentation

### Demo Example
**Input:** "Create a summary of recent AI developments"

**Actions:**
1. Decomposes → Research + Summarize
2. Discovers agents with matching capabilities
3. Executes via JSON-RPC
4. Aggregates results

### Why This Matters
Demonstrates that agents can **collaborate** based on capabilities rather than just respond to prompts. This is the foundation for the Internet of Agents.

---
**Author:** Prachet Dev Singh (prachetdevsingh@gmail.com)
**Built for:** Bindu Internship Application
```

---

## License

Same as Bindu - see [LICENSE.md](../../LICENSE.md)

## Author

**Prachet Dev Singh**  
Email: prachetdevsingh@gmail.com  

Built for Bindu internship application - demonstrates systems thinking and Bindu-native development patterns.
