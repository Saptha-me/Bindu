# Smart Research Assistant - Quick Reference

## 🚀 QUICKSTART (5 minutes)

### 1. Install
```bash
pip install openai duckduckgo-search requests python-dotenv
```

### 2. Set API Key
```powershell
$env:LLM_API_KEY='sk-your-openai-key-here'
```

### 3. Run Demo
```bash
python agent.py --demo
```

---

## ⚙️ CORE REQUIREMENTS (Absolute Minimum)

### Must Have
1. **Python 3.12+** - Programming language
2. **OpenAI API Key** - LLM functionality (get from https://platform.openai.com)
3. **openai package** - `pip install openai`
4. **duckduckgo-search package** - `pip install duckduckgo-search`

### Optional But Recommended
- Virtual environment (venv) - Isolate dependencies
- .env file - Store configuration safely
- python-dotenv - Load environment variables

---

## 📦 ALL PACKAGES (requirements.txt)

```
openai>=1.12.0                    # OpenAI LLM API
duckduckgo-search>=3.9.0          # Web search
requests>=2.31.0                  # HTTP requests
httpx>=0.25.0                     # Async HTTP client
python-dotenv>=1.0.0              # Environmental variables
pydantic>=2.0.0                   # Data validation
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🔑 API KEYS

### OpenAI (REQUIRED)
- Get: https://platform.openai.com/account/api-keys
- Format: `sk-...` (50+ characters)
- Cost: Pay-as-you-go (typically $0.001-$0.05 per query)
- Models: gpt-4-turbo, gpt-4, gpt-3.5-turbo

**Set API Key:**
```bash
# Option 1: Environment Variable
$env:LLM_API_KEY='sk-...'

# Option 2: .env file
echo "LLM_API_KEY=sk-..." > .env

# Option 3: Code (not recommended)
os.environ['LLM_API_KEY'] = 'sk-...'
```

### DuckDuckGo (FREE - No API Key)
- No registration needed
- No rate limits
- Works worldwide

---

## 🌍 ENVIRONMENT VARIABLES

| Name | Required | Value | Example |
|------|----------|-------|---------|
| `LLM_API_KEY` | YES | OpenAI API key | `sk-...` |
| `LLM_PROVIDER` | NO | Provider name | `openai` |
| `LLM_MODEL` | NO | Model ID | `gpt-4-turbo` |
| `SEARCH_MAX_RESULTS` | NO | Number (1-100) | `10` |
| `SEARCH_TIMEOUT` | NO | Seconds (1-300) | `30` |

---

## 📋 FILE REQUIREMENTS

```
Project Root/
├── agent.py                   # Main agent code (given)
├── requirements.txt           # Package list (given)
├── README.md                  # Documentation (given)
├── architecture.md            # System design (given)
├── test_components.py         # Tests (given)
├── .env                       # CREATE THIS - API key
└── venv/                      # CREATE THIS - Virtual environment
```

---

## 🏗️ SYSTEM REQUIREMENTS

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.12 | 3.12.x (latest) |
| RAM | 4GB | 8GB |
| Disk | 500MB | 1GB |
| CPU | 2 cores | 4+ cores |
| Internet | Required | Required |
| OS | Windows/Mac/Linux | Any |

---

## 🔧 CONFIGURATION EXAMPLES

### Using Environment Variables
```powershell
$env:LLM_API_KEY='sk-proj-...'
$env:LLM_MODEL='gpt-4-turbo'
$env:LLM_PROVIDER='openai'
python agent.py --demo
```

### Using .env File
```
# .env file
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-4-turbo
LLM_PROVIDER=openai
```

### Using In Code
```python
import os
os.environ['LLM_API_KEY'] = 'sk-proj-...'
from agent import handler

messages = [{"role": "user", "content": "query"}]
response = handler(messages)
```

---

## 📊 LLM MODEL OPTIONS

| Model | Cost (1K tokens) | Speed | Quality |
|-------|-----------------|-------|---------|
| gpt-3.5-turbo | $0.0005/$0.0015 | Fast | Good |
| gpt-4 | $0.03/$0.06 | Slow | Best |
| gpt-4-turbo | $0.01/$0.03 | Medium | Best |

**Recommended**: `gpt-4-turbo` (best balance)

---

## 🎯 COMMON TASKS

### Run Demo
```bash
python agent.py --demo
```

### Test Components
```bash
python test_components.py
```

### Import in Code
```python
from agent import handler

result = handler([{"role": "user", "content": "query"}])
print(result)
```

### Use as HTTP Service
```bash
# Requires Bindu setup
python -m bindu.server --agent agent.py

# Send request
curl -X POST http://localhost:3773/handler \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "query"}]}'
```

---

## ✅ VERIFICATION STEPS

```bash
# 1. Check Python version
python --version  # Should be 3.12+

# 2. Install packages
pip install -r requirements.txt

# 3. Set API key
$env:LLM_API_KEY='sk-...'

# 4. Test components
python test_components.py  # Should show ✓

# 5. Run demo
python agent.py --demo  # Should research and respond
```

---

## ❌ COMMON ERRORS & FIXES

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: openai` | `pip install openai` |
| `LLM_API_KEY not set` | `$env:LLM_API_KEY='sk-...'` |
| `Python 3.11 or lower` | Install Python 3.12+ from python.org |
| `API Key invalid` | Check key at openai.com/account/api-keys |
| `No internet connection` | Required for search and LLM API |

---

## 🌐 EXTERNAL RESOURCES

- **OpenAI API**: https://platform.openai.com
- **API Docs**: https://platform.openai.com/docs
- **Pricing**: https://openai.com/pricing
- **Python**: https://www.python.org
- **Bindu**: https://github.com/binduthq/bindu

---

## 💡 IMPORTANT NOTES

1. **API Key Security**: Never commit `.env` to git
2. **Rate Limiting**: OpenAI has rate limits - respect them
3. **Costs**: Monitor usage to avoid large bills
4. **Search**: DuckDuckGo is free (API limitations apply)
5. **Python Version**: Requires 3.12+ for compatibility

---

**Version**: 1.0.0  
**Updated**: March 4, 2026  
**Status**: Ready to Use ✓
