---
name: Question Answering
description: Provides intelligent question answering capabilities for general knowledge queries. Use when users ask factual questions, need explanations, or require information retrieval.
version: 1.0.0
author: raahul@saptha.me
allowed-tools: Read, Search, Reason
---

# Question Answering

## Overview
This skill enables the agent to answer a wide range of questions using reasoning and knowledge retrieval. It's designed for general-purpose question answering across various domains including science, history, technology, and everyday topics.

## Capabilities

### Factual Questions
- **Direct answers**: Provides concise, accurate responses to factual queries
- **Explanations**: Offers detailed explanations when needed
- **Multi-step reasoning**: Breaks down complex questions into logical steps
- **Source awareness**: Can indicate confidence levels and knowledge boundaries

### Question Types Supported
- **What/Who/Where/When**: Factual information retrieval
- **How**: Process explanations and instructions
- **Why**: Causal reasoning and explanations
- **Comparison**: Analyzing similarities and differences
- **Definition**: Explaining concepts and terminology

## Use Cases

### When to Use This Skill
- User asks a direct factual question
- User needs an explanation of a concept
- User wants to understand how something works
- User requests information about historical events, scientific facts, or general knowledge
- User needs help understanding a topic

### When NOT to Use This Skill
- Real-time information (use web-search skill)
- Personal data or user-specific information (use context-retrieval skill)
- Complex calculations (use calculator skill)
- Code generation (use code-assistant skill)
- Document processing (use document-analysis skill)

## Input Requirements

### Accepted Formats
- `text/plain`: Natural language questions
- `application/json`: Structured query format

### Input Structure
```json
{
  "question": "What is photosynthesis?",
  "context": "optional context or constraints",
  "detail_level": "brief|detailed|comprehensive"
}
```

Or simple text:
```
What is photosynthesis?
```

## Output Format

### Standard Response
```json
{
  "answer": "Photosynthesis is the process by which plants...",
  "confidence": 0.95,
  "sources": ["general_knowledge"],
  "follow_up_suggestions": [
    "Would you like to know about the chemical equation?",
    "Interested in learning about different types of photosynthesis?"
  ]
}
```

### Brief Response (text/plain)
```
Photosynthesis is the process by which plants convert light energy into chemical energy...
```

## Performance Characteristics
- **Average response time**: 500-1000ms
- **Concurrent requests**: Up to 10
- **Memory usage**: ~100MB per request
- **Scalability**: Horizontal scaling supported

## Quality Guidelines

### Answer Quality
1. **Accuracy**: Prioritize factual correctness
2. **Clarity**: Use clear, understandable language
3. **Completeness**: Address all aspects of the question
4. **Conciseness**: Be thorough but not verbose
5. **Honesty**: Acknowledge uncertainty when appropriate

### Response Patterns
- Start with direct answer
- Provide supporting details
- Offer examples when helpful
- Suggest related topics if relevant

## Error Handling
- **Ambiguous questions**: Ask for clarification
- **Out of scope**: Politely indicate limitations
- **Insufficient information**: Request additional context
- **Controversial topics**: Present balanced perspectives

## Examples

### Example 1: Simple Factual Question
**Input:**
```
What is the capital of France?
```

**Output:**
```json
{
  "answer": "The capital of France is Paris.",
  "confidence": 1.0,
  "sources": ["general_knowledge"]
}
```

### Example 2: Explanation Request
**Input:**
```json
{
  "question": "How does a refrigerator work?",
  "detail_level": "detailed"
}
```

**Output:**
```json
{
  "answer": "A refrigerator works by using a refrigeration cycle to remove heat from its interior...\n\n1. Compression: The compressor pressurizes refrigerant gas...\n2. Condensation: The hot gas flows through condenser coils...\n3. Expansion: The liquid refrigerant passes through an expansion valve...\n4. Evaporation: The cold refrigerant absorbs heat from the interior...",
  "confidence": 0.92,
  "sources": ["general_knowledge", "physics"],
  "follow_up_suggestions": [
    "Would you like to know about different types of refrigerants?",
    "Interested in energy efficiency tips for refrigerators?"
  ]
}
```

### Example 3: Complex Reasoning
**Input:**
```
Why do we see different phases of the moon?
```

**Output:**
```json
{
  "answer": "We see different phases of the moon because of the changing positions of the Moon, Earth, and Sun. As the Moon orbits Earth, the amount of its sunlit surface visible from Earth varies:\n\n- New Moon: Moon is between Earth and Sun (dark side faces us)\n- First Quarter: Moon is 90° from the Sun (half illuminated)\n- Full Moon: Earth is between Moon and Sun (fully illuminated)\n- Last Quarter: Moon is 270° from the Sun (half illuminated)\n\nThe cycle takes about 29.5 days to complete.",
  "confidence": 0.96,
  "sources": ["astronomy", "general_knowledge"]
}
```

## Dependencies
- None (uses built-in reasoning capabilities)

## Versioning
- **v1.0.0**: Initial release with general question answering
- Future: Enhanced with specialized domain knowledge modules

## Best Practices

### For Developers
1. Provide clear questions in natural language
2. Include context when available
3. Specify desired detail level
4. Handle follow-up questions in conversation flow

### For Orchestrators
1. Route factual questions to this skill
2. Chain with web-search for real-time information
3. Combine with document-analysis for context-aware answers
4. Use confidence scores for answer validation
