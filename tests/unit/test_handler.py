# test_handler.py - Test the improved handler logic

def handler(messages):
    """Handle incoming messages by echoing back the user's latest input."""
    if not messages:
        return [{
            "role": "assistant", 
            "content": "Error: No messages received. Please send at least one message in the format: [{'role': 'user', 'content': 'Your message here'}]"
        }]
    
    last_message = messages[-1]
    
    if not isinstance(last_message, dict):
        return [{
            "role": "assistant", 
            "content": f"Error: Expected dictionary for message, got {type(last_message).__name__}. Value: {last_message}"
        }]
    
    if "content" not in last_message:
        return [{
            "role": "assistant", 
            "content": f"Error: Message missing 'content' field. Received keys: {list(last_message.keys())}"
        }]
    
    if last_message.get("role") != "user":
        return [{
            "role": "assistant", 
            "content": f"Note: Last message role was '{last_message.get('role')}', expected 'user'. Echoing anyway: {last_message['content']}"
        }]
    
    return [{"role": "assistant", "content": last_message["content"]}]

# Test cases
test_cases = [
    {
        "name": "Empty messages list",
        "input": [],
        "expected_contains": "Error: No messages received"
    },
    {
        "name": "Message without content",
        "input": [{"role": "user"}],
        "expected_contains": "Error: Message missing 'content' field"
    },
    {
        "name": "Valid user message",
        "input": [{"role": "user", "content": "Hello"}],
        "expected_contains": "Hello"
    },
    {
        "name": "Non-dict message",
        "input": ["not a dict"],
        "expected_contains": "Error: Expected dictionary"
    },
]

print("🧪 Testing Echo Agent Handler\n")
for test in test_cases:
    result = handler(test["input"])
    content = result[0]["content"]
    passed = test["expected_contains"] in content
    print(f"{'✅' if passed else '❌'} {test['name']}")
    print(f"   Input: {test['input']}")
    print(f"   Output: {content[:50]}...")
    print()