# Smart Research Assistant Agent - Complete Requirements Guide

## 📋 TABLE OF CONTENTS
1. System Requirements
2. Environment Setup
3. Dependencies & Packages
4. API Keys & Credentials
5. Configuration Variables
6. File Structure
7. Running the Project
8. Usage Examples
9. Troubleshooting

---

## 1. SYSTEM REQUIREMENTS

### Operating System
- Windows, macOS, or Linux
- Windows PowerShell or Command Prompt recommended for Windows

### Python Version
- **Required**: Python 3.12 or higher
- **Recommended**: Python 3.12.x (latest stable)

### Hardware Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for project + dependencies
- **Network**: Internet connection required (for web search and LLM API)

### Internet Connection
- Required for:
  - DuckDuckGo web search
  - OpenAI API calls
  - Package downloads

---

## 2. ENVIRONMENT SETUP

### 2.1 Virtual Environment (Recommended)

**Windows:**
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2.2 Directory Structure
```
d:\smart_research_agent\           # Project root
├── agent.py                        # Main agent implementation
├── requirements.txt                # Dependencies list
├── README.md                      # Documentation
├── architecture.md                # System design
├── test_components.py             # Component verification
├── .env                           # Environment variables (create this)
└── venv/                          # Virtual environment (created by venv)
```

### 2.3 Environment File (.env)

Create `.env` file in project root:

```bash
# Create .env file
cat > .env << EOF
# OpenAI API Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
LLM_API_KEY=your-actual-api-key-here
LLM_BASE_URL=

# Search Configuration (optional)
SEARCH_MAX_RESULTS=10
SEARCH_TIMEOUT=30
EOF
```

Alternatively, set environment variables directly:

**Windows PowerShell:**
```powershell
$env:LLM_API_KEY='your-api-key-here'
$env:LLM_MODEL='gpt-4-turbo'
$env:LLM_PROVIDER='openai'
```

**Windows Command Prompt:**
```cmd
set LLM_API_KEY=your-api-key-here
set LLM_MODEL=gpt-4-turbo
set LLM_PROVIDER=openai
```

**macOS/Linux:**
```bash
export LLM_API_KEY='your-api-key-here'
export LLM_MODEL='gpt-4-turbo'
export LLM_PROVIDER='openai'
```

---

## 3. DEPENDENCIES & PACKAGES

### 3.1 Core Dependencies

All packages are listed in `requirements.txt`:

```
# Core packages
openai>=1.12.0                    # OpenAI API client
duckduckgo-search>=3.9.0          # Web search tool
requests>=2.31.0                  # HTTP requests
httpx>=0.25.0                     # Async HTTP
python-dotenv>=1.0.0              # Environment variables
pydantic>=2.0.0                   # Data validation

# Optional (for Bindu integration)
bindu-client>=1.0.0               # Bindu framework
bindu>=1.0.0                      # Bindu core
agno>=0.1.0                       # Agent framework
```

### 3.2 Installation

**Install all dependencies:**
```bash
pip install -r requirements.txt
```

**Install individual packages:**
```bash
pip install openai duckduckgo-search requests httpx python-dotenv pydantic
```

**Upgrade packages:**
```bash
pip install --upgrade openai duckduckgo-search
```

### 3.3 Verify Installation

```bash
# Test imports
python test_components.py

# Expected output
# ✓ OpenAI client available
# ✓ DuckDuckGo search available
# ✓ Agent name: Smart Research Assistant
# ✓ Response parsing works
```

---

## 4. API KEYS & CREDENTIALS

### 4.1 OpenAI API Key (REQUIRED)

**Where to get it:**
1. Visit https://platform.openai.com/account/api-keys
2. Sign up if you don't have an account (requires payment method)
3. Create new API key
4. Copy the key (only shown once!)

**Available Models:**
- `gpt-4-turbo` (Recommended - $0.01/$0.03 per 1K tokens)
- `gpt-4` (More expensive - $0.03/$0.06 per 1K tokens)
- `gpt-3.5-turbo` (Budget option - $0.0005/$0.0015 per 1K tokens)

**Cost Estimation:**
- Simple query: ~$0.001 - $0.005
- Complex query: ~$0.01 - $0.05
- Typical usage (10 queries): ~$0.10 - $0.30

**Set the API Key:**

Option 1 - Environment Variable:
```powershell
# Windows PowerShell
$env:LLM_API_KEY='sk-...'
```

Option 2 - .env File:
```
LLM_API_KEY=sk-...
```

### 4.2 DuckDuckGo (No API Key Required)

- DuckDuckGo search is free
- No registration needed
- No rate limiting (reasonable use)
- Works globally

---

## 5. CONFIGURATION VARIABLES

### 5.1 Required Configuration

| Variable | Default | Value | Purpose |
|----------|---------|-------|---------|
| `LLM_API_KEY` | None | Your OpenAI API key | **REQUIRED** - Authenticate with OpenAI |
| `LLM_PROVIDER` | `openai` | `openai` | LLM provider selection |
| `LLM_MODEL` | `gpt-4-turbo` | See Available Models | Which LLM model to use |

### 5.2 Optional Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_BASE_URL` | (empty) | Custom LLM endpoint |
| `SEARCH_MAX_RESULTS` | 10 | Max web search results |
| `SEARCH_TIMEOUT` | 30 | Search timeout in seconds |

### 5.3 Agent Configuration (in code)

```python
AGENT_CONFIG = {
    "author": "Bindu Contributors",
    "name": "Smart Research Assistant",
    "description": "An AI agent that researches topics...",
    "version": "1.0.0",
    "deployment": {
        "host": "localhost",
        "port": 3773,
        "protocol": "http"
    }
}
```

---

## 6. FILE STRUCTURE & DESCRIPTIONS

### 6.1 Project Files

**agent.py** (442 lines)
- Main agent implementation
- Contains `handler()` function (entry point)
- Search and synthesis logic
- Response parsing
- Demo mode for testing

**requirements.txt**
- List of all dependencies
- Version specifications
- Package management file

**README.md** (400+ lines)
- Complete project documentation
- Setup instructions
- Usage examples
- Architecture overview
- Troubleshooting guide

**architecture.md** (350+ lines)
- Detailed system architecture
- Data flow diagrams
- Component descriptions
- Performance metrics

**test_components.py**
- Verification script
- Tests all core components
- Validates API connectivity
- No LLM API key required

### 6.2 Generated Files

**.env** (Create this)
```
LLM_API_KEY=your-key
LLM_MODEL=gpt-4-turbo
LLM_PROVIDER=openai
```

**venv/** (Virtual environment)
- Created by `python -m venv venv`
- Contains isolated Python environment
- All packages installed here

---

## 7. RUNNING THE PROJECT

### 7.1 Initial Setup (One Time)

```bash
# Step 1: Navigate to project
cd d:\smart_research_agent

# Step 2: Create virtual environment
python -m venv venv

# Step 3: Activate virtual environment
venv\Scripts\activate    # Windows
# OR
source venv/bin/activate  # macOS/Linux

# Step 4: Install dependencies
pip install -r requirements.txt

# Step 5: Create .env file with API key
$env:LLM_API_KEY='sk-...'
```

### 7.2 Test Components

```bash
# Verify everything is working
python test_components.py
```

Expected output:
```
✓ OpenAI client available
✓ DuckDuckGo search available
✓ Agent name: Smart Research Assistant
✓ Response parsing works
```

### 7.3 Run Demo Mode

```bash
# Activate venv first
venv\Scripts\activate

# Run demo
python agent.py --demo
```

### 7.4 Run Without API Key (Testing Structure Only)

```bash
# Just test the agent structure
python agent.py
```

---

## 8. USAGE EXAMPLES

### 8.1 Via Python Direct

```python
from agent import handler

# Create message
messages = [
    {"role": "user", "content": "What are the latest trends in AI?"}
]

# Get response
result = handler(messages)

# Response format
{
    "status": "success",
    "response": {
        "summary": "...",
        "key_points": [...],
        "sources": [...],
        "timestamp": "2024-03-04T..."
    },
    "error": None
}
```

### 8.2 Via HTTP (Bindu Server)

```bash
# Start Bindu server
python -m bindu.server --agent agent.py

# Send request
curl -X POST http://localhost:3773/handler \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Your question"}
    ]
  }'
```

### 8.3 Example Queries

1. **Technology Topics**
   - "What are the latest trends in machine learning?"
   - "Explain quantum computing"
   - "What's new in Python 3.12?"

2. **Research Questions**
   - "What are the benefits of renewable energy?"
   - "How does blockchain technology work?"
   - "What is the current state of AI safety?"

3. **Comparative Questions**
   - "Compare React vs Vue.js"
   - "Python vs Go for backend development"
   - "AWS vs Azure cloud platforms"

---

## 9. TROUBLESHOOTING

### 9.1 "ModuleNotFoundError: No module named 'openai'"

```bash
# Solution: Install missing package
pip install openai duckduckgo-search

# Or reinstall all
pip install -r requirements.txt
```

### 9.2 "LLM_API_KEY environment variable not set"

```powershell
# Set the API key
$env:LLM_API_KEY='your-key-here'

# Or create .env file
# LLM_API_KEY=your-key-here
```

### 9.3 "Python 3.12+ Required"

```bash
# Check Python version
python --version

# If Python 3.11 or lower, download 3.12+
# Visit: https://www.python.org/downloads/
```

### 9.4 Web Search Returns 0 Results

- This is expected with `duckduckgo-search` package (API changed)
- Agent will still work with LLM context
- Alternative: Use `ddgs` package instead

### 9.5 OpenAI API Rate Limited

- Wait before making more requests
- Check usage at: https://openai.com/account/usage
- Consider different model (cheaper options available)

---

## 📊 QUICK START CHECKLIST

- [ ] Python 3.12+ installed
- [ ] Project files in `d:\smart_research_agent\`
- [ ] Virtual environment created (`venv/`)
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] OpenAI API key obtained
- [ ] `LLM_API_KEY` environment variable set
- [ ] Components verified: `python test_components.py`
- [ ] Demo runs: `python agent.py --demo`

---

## 🔗 USEFUL LINKS

- OpenAI API: https://platform.openai.com/
- API Documentation: https://platform.openai.com/docs/
- Model Pricing: https://openai.com/pricing/
- DuckDuckGo: https://duckduckgo.com/
- Python Official: https://www.python.org/
- Bindu Framework: https://github.com/binduthq/bindu
- Agno Framework: https://github.com/agno-ai/agno

---

## 📞 SUPPORT

For issues:
1. Check troubleshooting section above
2. Verify all requirements are installed
3. Check `test_components.py` output
4. Review README.md for detailed docs
5. Check architecture.md for system design

---

**Last Updated**: March 4, 2026  
**Project Version**: 1.0.0  
**Status**: Production Ready ✓
