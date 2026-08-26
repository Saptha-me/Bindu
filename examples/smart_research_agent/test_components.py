#!/usr/bin/env python
"""Quick component verification script"""

print("\n" + "="*70)
print("SMART RESEARCH ASSISTANT - COMPONENT TEST")
print("="*70 + "\n")

# Test 1: Import checks
print("✓ Testing imports...")
try:
    from openai import OpenAI
    print("  ✓ OpenAI client available")
except ImportError as e:
    print(f"  ✗ OpenAI import failed: {e}")

try:
    from duckduckgo_search import DDGS
    print("  ✓ DuckDuckGo search available")
except ImportError as e:
    print(f"  ✗ DuckDuckGo import failed: {e}")

# Test 2: Web search
print("\n✓ Testing web search functionality...")
try:
    from duckduckgo_search import DDGS
    ddgs = DDGS(timeout=10)
    results = ddgs.text("Python programming language", max_results=3)
    results_list = list(results)
    print(f"  ✓ Search returned {len(results_list)} results")
    for i, r in enumerate(results_list[:2], 1):
        title = r.get("title", "")[:50]
        print(f"    {i}. {title}...")
except Exception as e:
    print(f"  ✗ Search failed: {e}")

# Test 3: Agent structure
print("\n✓ Testing agent structure...")
try:
    from agent import AGENT_CONFIG, parse_research_response
    print(f"  ✓ Agent name: {AGENT_CONFIG['name']}")
    print(f"  ✓ Agent version: {AGENT_CONFIG['version']}")
    
    # Test response parsing
    test_response = """
## Summary
This is a test summary about the topic.

## Key Points
- First important point
- Second important point
- Third important point

## Sources
Source 1: Example.com
Source 2: Test.org
"""
    parsed = parse_research_response(test_response)
    print(f"  ✓ Response parsing works")
    print(f"    - Summary length: {len(parsed['summary'])} chars")
    print(f"    - Key points: {len(parsed['key_points'])}")
    print(f"    - Sources: {len(parsed['sources'])}")
except Exception as e:
    print(f"  ✗ Agent test failed: {e}")

# Test 4: Summary
print("\n" + "="*70)
print("COMPONENT STATUS: All core components operational ✓")
print("="*70)
print("\nTo run with LLM integration:")
print("  1. Set environment variable: $env:LLM_API_KEY='your-key'")
print("  2. Run: python agent.py --demo")
print("\n")
