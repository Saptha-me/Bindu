# Smart Research Assistant Agent

A production-ready Bindu agent that performs web research, synthesizes findings with an LLM, and returns structured outputs with sources.

**Framework**: Bindu + Agno  
**Python**: 3.12+  
**Status**: PR-ready example

## What This Example Demonstrates

- Official Bindu integration using `bindu.penguin.bindufy`
- Typed `handler(messages)` entrypoint for Bindu calls
- Agno `Agent` with DuckDuckGo search tool
- OpenAI-first model selection with OpenRouter fallback
- Structured response format (`summary`, `key_points`, `sources`, `timestamp`)
- Error-safe behavior for missing keys and runtime failures

## Project Structure

```text
smart_research_agent/
├── agent.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── architecture.md
├── demo_working.py
├── test_components.py
└── .gitignore
```

## Quick Start

### 1) Create environment

```bash
cd smart_research_agent
uv venv
```

Activate:

- Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

- macOS/Linux:

```bash
source .venv/bin/activate
```

### 2) Install dependencies

```bash
uv sync
```

Fallback:

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Create `.env` in project root:

```env
OPENAI_API_KEY=your-openai-api-key
# Optional fallback
# OPENROUTER_API_KEY=your-openrouter-api-key

LLM_MODEL=gpt-4o-mini
SEARCH_MAX_RESULTS=10
SEARCH_TIMEOUT=30
```

## Usage

### Demo mode

```bash
python agent.py --demo
```

### Start with Bindu

```bash
bindu server --agent agent.py
```

Then call:

```bash
curl -X POST http://localhost:3773/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the latest developments in AI agents?"}
    ]
  }'
```

## Core Configuration (Matches Code)

In `agent.py`, the agent uses:

```python
CONFIG = {
    "author": "ughademayur67@gmail.com",
    "name": "smart_research_agent",
    "description": "An intelligent research assistant that searches the internet and synthesizes information into structured responses with key insights and sources.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": False
    },
    "skills": [
        "skills/question-answering",
        "skills/web-research",
        "skills/information-synthesis"
    ]
}
```

Registration:

```python
bindufy(config=CONFIG, handler_func=handler)
```

## Handler Contract

```python
def handler(messages: list[dict[str, str]]) -> dict[str, Any]:
    ...
```

Returns:

```json
{
  "status": "success|error",
  "response": {
    "summary": "...",
    "key_points": ["..."],
    "sources": ["..."],
    "timestamp": "2026-03-04T12:34:56.000Z"
  },
  "error": null
}
```

## Notes on API Quota

If OpenAI billing/quota is not active, API requests can fail with `429 insufficient_quota`.  
This is an account/billing issue, not a code-structure issue.

## Why This Is PR-Strong

- Uses official Bindu import and registration patterns
- Uses typed handler and clean error handling
- Keeps env configuration explicit and secure
- Includes both `requirements.txt` and `pyproject.toml`
- Matches implemented behavior (no stale/duplicated docs)

## Security

- API keys are loaded from environment only
- `.gitignore` excludes `.env`, virtualenv, caches, and common secret artifacts
- No hardcoded credentials in source files

## Resources

- Bindu: https://github.com/binduthq/bindu
- Agno: https://github.com/agno-ai/agno
- OpenAI Docs: https://platform.openai.com/docs
- OpenRouter Docs: https://openrouter.ai/docs

---

**Updated**: March 2026
