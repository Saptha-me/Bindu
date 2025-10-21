# Bindu Skills System

The Bindu Skills System provides rich agent capability advertisement for intelligent orchestration and agent discovery. Inspired by Claude's skills architecture, it enables agents to provide detailed documentation about their capabilities for orchestrators to make informed routing decisions.

## Overview

Skills in Bindu serve as **rich advertisement metadata** that help orchestrators:
- Discover the right agent for a task
- Understand detailed capabilities and limitations
- Validate requirements before execution
- Estimate performance and resource needs
- Chain multiple agents intelligently

## Skill Types

Bindu supports two skill definition formats:

### 1. File-Based Skills (Claude-Style)
Rich documentation with SKILL.md files for orchestrator discovery.

```
examples/skills/pdf-processing/
├── manifest.json          # Structured metadata
└── SKILL.md              # Rich documentation
```

### 2. Inline Skills (Legacy)
Simple JSON definitions in config files.

```json
{
  "name": "skill-name",
  "description": "...",
  "version": "1.0.0"
}
```

## File-Based Skills

### Directory Structure

```
.bindu/skills/your-skill/
├── manifest.json          # Required: Structured metadata
├── SKILL.md              # Required: Rich documentation
├── EXAMPLES.md           # Optional: Usage examples
└── REFERENCE.md          # Optional: API reference
```

### manifest.json

Contains structured metadata for programmatic access:

```json
{
  "id": "skill-id-v1",
  "name": "skill-name",
  "description": "Brief description of the skill",
  "version": "1.0.0",
  "tags": ["tag1", "tag2"],
  "examples": [
    "Example usage 1",
    "Example usage 2"
  ],
  "input_modes": ["text/plain", "application/json"],
  "output_modes": ["application/json"],
  "documentation_path": "path/to/SKILL.md",
  
  "capabilities_detail": {
    "feature_1": {
      "supported": true,
      "types": ["type_a", "type_b"],
      "limitations": "Optional limitations description"
    },
    "feature_2": {
      "supported": false,
      "planned_version": "2.0.0"
    }
  },
  
  "requirements": {
    "packages": ["package1>=1.0.0", "package2>=2.0.0"],
    "system": ["system-dependency"],
    "min_memory_mb": 512
  },
  
  "performance": {
    "avg_processing_time_ms": 2000,
    "max_file_size_mb": 50,
    "concurrent_requests": 5,
    "memory_per_request_mb": 500
  },
  
  "allowed_tools": ["Read", "Write", "Execute"]
}
```

### SKILL.md

Provides rich documentation for orchestrators:

```markdown
---
name: Skill Name
description: Detailed description for orchestrator matching
version: 1.0.0
author: your@email.com
allowed-tools: Read, Write, Execute
---

# Skill Name

## Overview
Comprehensive description of what this skill does and its purpose.

## Capabilities

### Feature 1
- Details about feature 1
- Supported types and formats
- Limitations

### Feature 2
- Details about feature 2

## Use Cases

### When to Use This Skill
- Scenario 1
- Scenario 2

### When NOT to Use This Skill
- Anti-pattern 1
- Anti-pattern 2

## Input Requirements

### Accepted Formats
- `application/pdf`
- `text/plain`

### Input Structure
\```json
{
  "field": "value"
}
\```

## Output Format

### Standard Response
\```json
{
  "result": "data"
}
\```

## Performance Characteristics
- Average processing time: X ms
- Concurrent requests: Y
- Memory usage: Z MB

## Error Handling
- Error type 1: How it's handled
- Error type 2: How it's handled

## Examples

### Example 1: Basic Usage
**Input:**
\```
Input example
\```

**Output:**
\```json
{
  "output": "example"
}
\```

## Dependencies
- package1>=1.0.0
- package2>=2.0.0

## Versioning
- v1.0.0: Initial release
- v1.1.0: Added feature X

## Best Practices

### For Developers
1. Best practice 1
2. Best practice 2

### For Orchestrators
1. Routing guideline 1
2. Chaining guideline 2
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

### Using Inline Skills

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
      "documentation_path": "path/to/SKILL.md"
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

**Response:** (text/markdown)
```markdown
---
name: Skill Name
...
---

# Skill Name

Full SKILL.md content...
```

## Orchestrator Integration

### Discovery Example

```python
import httpx

async def find_best_agent(task_description: str):
    """Find the best agent for a task using skill documentation."""
    
    # 1. Get all available agents
    agents = await get_available_agents()
    
    # 2. For each agent, fetch skill details
    candidates = []
    for agent in agents:
        skills_response = await httpx.get(f"{agent.url}/agent/skills")
        skills = skills_response.json()["skills"]
        
        # 3. Load full documentation for matching
        for skill in skills:
            if matches_task(skill, task_description):
                doc_response = await httpx.get(
                    f"{agent.url}/agent/skills/{skill['id']}/documentation"
                )
                skill["documentation"] = doc_response.text
                
                # 4. Score based on detailed capabilities
                score = calculate_match_score(skill, task_description)
                candidates.append((agent, skill, score))
    
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

## Best Practices

### For Skill Authors

1. **Be Specific**: Provide detailed capability descriptions
2. **Document Limitations**: Clearly state what the skill cannot do
3. **Include Examples**: Show concrete usage patterns
4. **Update Performance Metrics**: Keep performance data current
5. **Version Carefully**: Use semantic versioning

### For Agent Developers

1. **Use File-Based Skills**: For complex capabilities requiring rich documentation
2. **Use Inline Skills**: For simple, self-explanatory capabilities
3. **Keep Skills Focused**: One skill per capability domain
4. **Document Requirements**: List all dependencies clearly
5. **Test Documentation**: Ensure orchestrators can parse and use it

### For Orchestrators

1. **Cache Skill Data**: Avoid repeated fetches
2. **Validate Requirements**: Check before routing
3. **Use Performance Metrics**: For load balancing
4. **Handle Errors**: Gracefully handle missing skills
5. **Semantic Matching**: Use documentation content for intelligent routing

## Migration Guide

### From Inline to File-Based Skills

1. Create skill directory:
```bash
mkdir -p .bindu/skills/my-skill
```

2. Create manifest.json from inline definition:
```json
{
  "id": "my-skill-v1",
  "name": "my-skill",
  "description": "...",
  "version": "1.0.0",
  "tags": [...],
  "input_modes": [...],
  "output_modes": [...]
}
```

3. Create SKILL.md with rich documentation

4. Update config:
```json
{
  "skills": [
    ".bindu/skills/my-skill"  // Changed from inline object
  ]
}
```

## Examples

See the `examples/skills/` directory for complete examples:
- `question-answering/`: General Q&A skill
- `pdf-processing/`: PDF document processing skill

## Troubleshooting

### Skill Not Loading

**Problem:** Skill directory not found

**Solution:** Ensure path is relative to config file location or use absolute path

### Missing Documentation

**Problem:** `/agent/skills/{id}/documentation` returns 404

**Solution:** Ensure SKILL.md exists and is loaded (check `has_documentation` field)

### Invalid Manifest

**Problem:** Skill fails to load with JSON error

**Solution:** Validate manifest.json syntax and required fields (id, name, description)

## Future Enhancements

- Skill versioning and compatibility checking
- Skill marketplace and registry
- Automatic skill discovery from agent behavior
- Skill composition and chaining recommendations
- Performance benchmarking and optimization suggestions
