# Bindu Skills System

The Bindu Skills System provides rich agent capability advertisement for intelligent orchestration and agent discovery. Inspired by Claude's skills architecture, it enables agents to provide detailed documentation about their capabilities for orchestrators to make informed routing decisions.

## Overview

Skills in Bindu serve as **rich advertisement metadata** that help orchestrators:
- Discover the right agent for a task
- Understand detailed capabilities and limitations
- Validate requirements before execution
- Estimate performance and resource needs
- Chain multiple agents intelligently

## Skill Definition Format

Bindu uses **YAML files** as the single source of truth for skill definitions. This provides:
- ✅ Human-readable and easy to write
- ✅ Structured data for programmatic access
- ✅ Rich documentation in one place
- ✅ LLM-friendly format
- ✅ No duplication

### Directory Structure

```
examples/skills/your-skill/
└── skill.yaml              # Single file - everything here!
```

## skill.yaml Format

Complete example with all fields:

```yaml
# Basic Metadata
id: skill-id-v1
name: skill-name
version: 1.0.0
author: your@email.com

# Description
description: |
  Brief description of what this skill does.
  Can be multi-line for detailed explanation.

# Tags and Modes
tags:
  - tag1
  - tag2
  - tag3

input_modes:
  - text/plain
  - application/json

output_modes:
  - application/json
  - text/plain

# Example Queries
examples:
  - "Example usage 1"
  - "Example usage 2"
  - "Example usage 3"

# Detailed Capabilities
capabilities_detail:
  feature_1:
    supported: true
    types:
      - type_a
      - type_b
    limitations: "Optional limitations description"
  
  feature_2:
    supported: false
    planned_version: "2.0.0"

# Requirements
requirements:
  packages:
    - package1>=1.0.0
    - package2>=2.0.0
  system:
    - system-dependency
  min_memory_mb: 512

# Performance Metrics
performance:
  avg_processing_time_ms: 2000
  max_file_size_mb: 50
  concurrent_requests: 5
  memory_per_request_mb: 500

# Tool Restrictions
allowed_tools:
  - Read
  - Write
  - Execute

# Rich Documentation
documentation:
  overview: |
    Comprehensive description of what this skill does and its purpose.
    Can include multiple paragraphs and detailed explanations.
  
  use_cases:
    when_to_use:
      - Scenario 1
      - Scenario 2
      - Scenario 3
    
    when_not_to_use:
      - Anti-pattern 1
      - Anti-pattern 2
  
  input_structure: |
    Description of expected input format with examples:
    
    ```json
    {
      "field": "value"
    }
    ```
  
  output_format: |
    Description of output format with examples:
    
    ```json
    {
      "result": "data"
    }
    ```
  
  error_handling:
    - "Error type 1: How it's handled"
    - "Error type 2: How it's handled"
  
  examples:
    - title: "Example 1"
      input: "input data"
      output: "output data"
    
    - title: "Example 2"
      input:
        field: "value"
      output:
        result: "data"
  
  best_practices:
    for_developers:
      - "Best practice 1"
      - "Best practice 2"
    
    for_orchestrators:
      - "Routing guideline 1"
      - "Chaining guideline 2"
```

## Configuration

### Using File-Based Skills

In your agent config:

```json
{
  "name": "my-agent",
  "skills": [
    "examples/skills/question-answering",
    "examples/skills/pdf-processing"
  ]
}
```

### Using Inline Skills (Legacy)

```json
{
  "name": "my-agent",
  "skills": [
    {
      "name": "simple-skill",
      "description": "A simple skill",
      "version": "1.0.0",
      "tags": ["basic"],
      "input_modes": ["text/plain"],
      "output_modes": ["text/plain"]
    }
  ]
}
```

### Mixed Approach

You can mix both formats:

```json
{
  "name": "my-agent",
  "skills": [
    "examples/skills/pdf-processing",
    {
      "name": "inline-skill",
      "description": "...",
      "version": "1.0.0"
    }
  ]
}
```

## API Endpoints

### List All Skills

```http
GET /agent/skills
```

**Response:**
```json
{
  "skills": [
    {
      "id": "skill-id",
      "name": "skill-name",
      "description": "...",
      "version": "1.0.0",
      "tags": ["tag1", "tag2"],
      "input_modes": ["text/plain"],
      "output_modes": ["application/json"],
      "examples": ["example1", "example2"],
      "documentation_path": "examples/skills/skill-name/skill.yaml"
    }
  ],
  "total": 1
}
```

### Get Skill Details

```http
GET /agent/skills/{skill_id}
```

**Response:**
```json
{
  "id": "skill-id",
  "name": "skill-name",
  "description": "...",
  "version": "1.0.0",
  "tags": ["tag1", "tag2"],
  "capabilities_detail": {...},
  "requirements": {...},
  "performance": {...},
  "has_documentation": true
}
```

### Get Skill Documentation

```http
GET /agent/skills/{skill_id}/documentation
```

**Response:** (application/yaml)
```yaml
id: skill-id
name: skill-name
description: ...
documentation:
  overview: ...
```

## Orchestrator Integration

### Discovery Example

```python
import httpx
import yaml

async def find_best_agent(task_description: str):
    """Find the best agent for a task using skill documentation."""
    
    # 1. Get all available agents
    agents = await get_available_agents()
    
    # 2. For each agent, fetch skill details
    candidates = []
    for agent in agents:
        skills_response = await httpx.get(f"{agent.url}/agent/skills")
        skills = skills_response.json()["skills"]
        
        # 3. Load full YAML documentation for matching
        for skill in skills:
            if matches_task(skill, task_description):
                doc_response = await httpx.get(
                    f"{agent.url}/agent/skills/{skill['id']}/documentation"
                )
                skill_yaml = yaml.safe_load(doc_response.text)
                
                # 4. Score based on detailed capabilities
                score = calculate_match_score(skill_yaml, task_description)
                candidates.append((agent, skill_yaml, score))
    
    # 5. Select best match
    best_agent, best_skill, score = max(candidates, key=lambda x: x[2])
    return best_agent, best_skill
```

### Capability Matching

```python
def check_requirements(skill: dict) -> bool:
    """Validate agent requirements before routing."""
    requirements = skill.get("requirements", {})
    
    # Check system dependencies
    for sys_dep in requirements.get("system", []):
        if not system_has(sys_dep):
            return False
    
    # Check memory availability
    min_memory = requirements.get("min_memory_mb", 0)
    if available_memory_mb() < min_memory:
        return False
    
    return True
```

### Performance Estimation

```python
def estimate_execution_time(skill: dict, input_size: int) -> float:
    """Estimate execution time based on skill performance metrics."""
    performance = skill.get("performance", {})
    
    avg_time = performance.get("avg_processing_time_ms", 1000)
    max_size = performance.get("max_file_size_mb", 10)
    
    # Scale based on input size
    size_factor = input_size / max_size
    estimated_time = avg_time * size_factor
    
    return estimated_time
```

### LLM-Based Orchestration

```python
async def llm_find_agent(user_query: str, agents: list):
    """Use LLM to understand skill YAML and match to user query."""
    
    # Get all skill YAMLs
    skill_yamls = []
    for agent in agents:
        doc_response = await httpx.get(
            f"{agent.url}/agent/skills/{agent.skill_id}/documentation"
        )
        skill_yamls.append({
            "agent": agent,
            "yaml": doc_response.text
        })
    
    # LLM can understand YAML directly
    prompt = f"""
    User query: {user_query}
    
    Available skills:
    {yaml.dump([s["yaml"] for s in skill_yamls])}
    
    Which skill best matches the user query? Consider:
    - Capabilities and limitations
    - Performance requirements
    - Input/output formats
    - Use cases and anti-patterns
    """
    
    best_match = await llm.analyze(prompt)
    return best_match
```

## Best Practices

### For Skill Authors

1. **Be Specific**: Provide detailed capability descriptions
2. **Document Limitations**: Clearly state what the skill cannot do
3. **Include Examples**: Show concrete usage patterns with input/output
4. **Update Performance Metrics**: Keep performance data current
5. **Version Carefully**: Use semantic versioning
6. **Use Rich Documentation**: Leverage the `documentation` section fully

### For Agent Developers

1. **Use File-Based Skills**: For complex capabilities requiring rich documentation
2. **Use Inline Skills**: For simple, self-explanatory capabilities
3. **Keep Skills Focused**: One skill per capability domain
4. **Document Requirements**: List all dependencies clearly
5. **Test YAML Syntax**: Validate YAML before deployment

### For Orchestrators

1. **Cache Skill Data**: Avoid repeated fetches
2. **Validate Requirements**: Check before routing
3. **Use Performance Metrics**: For load balancing
4. **Handle Errors**: Gracefully handle missing skills
5. **Semantic Matching**: Use YAML content for intelligent routing
6. **LLM Integration**: Leverage LLMs to understand skill documentation

## Creating a New Skill

### Step 1: Create Directory

```bash
mkdir -p examples/skills/my-skill
```

### Step 2: Create skill.yaml

```bash
cd examples/skills/my-skill
touch skill.yaml
```

### Step 3: Define Skill

```yaml
id: my-skill-v1
name: my-skill
version: 1.0.0
author: your@email.com

description: |
  What your skill does

tags:
  - relevant
  - tags

input_modes:
  - text/plain

output_modes:
  - application/json

capabilities_detail:
  main_feature:
    supported: true
    description: "What it does"

requirements:
  packages: []
  system: []
  min_memory_mb: 100

performance:
  avg_processing_time_ms: 500
  concurrent_requests: 10

documentation:
  overview: |
    Detailed description
  
  use_cases:
    when_to_use:
      - Use case 1
    when_not_to_use:
      - Anti-pattern 1
```

### Step 4: Reference in Config

```json
{
  "skills": [
    "examples/skills/my-skill"
  ]
}
```

### Step 5: Test

```bash
# Start agent
python your_agent.py

# Test endpoint
curl http://localhost:8030/agent/skills
curl http://localhost:8030/agent/skills/my-skill-v1
curl http://localhost:8030/agent/skills/my-skill-v1/documentation
```

## Examples

See the `examples/skills/` directory for complete examples:
- `question-answering/skill.yaml`: General Q&A skill
- `pdf-processing/skill.yaml`: PDF document processing skill

## Troubleshooting

### Skill Not Loading

**Problem:** Skill directory not found

**Solution:** Ensure path is relative to config file location or use absolute path

### Invalid YAML

**Problem:** Skill fails to load with YAML error

**Solution:** Validate YAML syntax using online validator or `yamllint`

### Missing Documentation

**Problem:** `/agent/skills/{id}/documentation` returns 404

**Solution:** Ensure skill.yaml exists and is properly formatted

### Fields Not Showing

**Problem:** Some fields missing in API response

**Solution:** Check that fields are properly indented in YAML (YAML is whitespace-sensitive)

## Why YAML Only?

### Advantages

✅ **Single Source of Truth** - One file to maintain  
✅ **Human-Friendly** - Easy to read and write  
✅ **Structured** - Easy to parse programmatically  
✅ **LLM-Friendly** - LLMs understand YAML well  
✅ **Rich Content** - Supports multi-line strings, nested structures  
✅ **No Duplication** - No need to sync multiple files  
✅ **Version Control Friendly** - Clean diffs  

### Comparison with Other Formats

| Format | Readability | Structure | Rich Content | LLM-Friendly |
|--------|-------------|-----------|--------------|--------------|
| YAML | ✅ Excellent | ✅ Yes | ✅ Yes | ✅ Yes |
| JSON | ⚠️ Moderate | ✅ Yes | ⚠️ Limited | ✅ Yes |
| Markdown | ✅ Excellent | ❌ No | ✅ Yes | ✅ Yes |
| JSON + MD | ⚠️ Moderate | ✅ Yes | ✅ Yes | ⚠️ Requires both |

## Future Enhancements

- Skill versioning and compatibility checking
- Skill marketplace and registry
- Automatic skill discovery from agent behavior
- Skill composition and chaining recommendations
- Performance benchmarking and optimization suggestions
- YAML schema validation
- CLI tool for skill creation and validation
