# Reply Feature in Gradio UI

## Overview

The Bindu Gradio UI now supports replying to specific agent messages using the A2A protocol's `referenceTaskIds` field. This allows users to create contextual follow-up messages that reference previous tasks.

## How It Works

### User Experience

1. **Click the 👍 (like) button** on any agent message to select it for reply
2. A **reply indicator** appears above the input box showing which task you're replying to
3. Type your message and submit - it will include the selected task ID as a reference
4. The agent receives the `referenceTaskIds` in the message payload and can use it for context
5. **Click 👍 again** to unlike and clear the reply selection

### Visual Indicators

- **Like button**: Each agent message has a 👍 button on the right side
- **Reply indicator**: Shows `💬 Replying to task: abc12345... - Type your reply below` when a message is liked
- **User message prefix**: When replying, user messages show `↩️ Replying to task abc12345...`

### Technical Implementation

#### Client Side (`bindu/ui/client.py`)

```python
async def send_message(
    self, 
    message: str, 
    history: list[dict[str, Any]] | None = None, 
    reply_to_task_id: str | None = None
) -> tuple[str, str, str]:
    """Send message with optional reply-to task ID."""
    
    # Build reference task IDs
    reference_task_ids = [reply_to_task_id] if reply_to_task_id else []
    
    # Include in message payload
    jsonrpc_request = {
        "params": {
            "message": {
                "taskId": task_id,
                "referenceTaskIds": reference_task_ids,  # A2A protocol field
                ...
            }
        }
    }
```

#### UI Side (`bindu/ui/gradio_ui.py`)

```python
# State management
reply_to_task = gr.State(None)  # Stores selected task ID
reply_indicator = gr.Markdown("", visible=False)  # Shows reply indicator

# Event handler for message selection
def set_reply_to(history, evt: gr.SelectData):
    """Set task ID when user clicks on agent message."""
    msg = history[evt.index]
    if msg.get("role") == "assistant":
        task_id = msg.get("metadata", {}).get("task_id")
        return task_id, gr.Markdown(f"💬 Replying to: {task_id[:8]}...", visible=True)
    return None, gr.Markdown("", visible=False)

# Connect click event
chatbot.select(set_reply_to, [chatbot], [reply_to_task, reply_indicator])
```

### A2A Protocol Compliance

The implementation follows the A2A protocol specification:

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "make it shorter"}],
      "kind": "message",
      "messageId": "550e8400-e29b-41d4-a716-446655440027",
      "contextId": "550e8400-e29b-41d4-a716-446655440027",
      "taskId": "550e8400-e29b-41d4-a716-446655440042",
      "referenceTaskIds": ["550e8400-e29b-41d4-a716-446655440078"]
    }
  }
}
```

## Benefits

1. **Explicit Context**: Users explicitly choose which message to reference
2. **Better UX**: Clear visual feedback about reply relationships
3. **Protocol Compliant**: Uses standard A2A `referenceTaskIds` field
4. **Flexible**: Agent can use references for context or ignore them
5. **Simple**: No complex automatic context tracking needed

## Future Enhancements

- **Multiple references**: Allow selecting multiple messages to reference
- **Thread view**: Visualize reply chains in the UI
- **Smart suggestions**: Suggest relevant messages to reply to
- **Reference preview**: Show referenced message content in tooltip

## Example Use Cases

### 1. Refinement Request
```
User: "Write a poem about AI"
Agent: [Task 1] "Here's a long poem..."
User: [Clicks Task 1] "make it shorter"
Agent: [Receives referenceTaskIds: [Task 1]] "Here's a shorter version..."
```

### 2. Follow-up Question
```
User: "Explain quantum computing"
Agent: [Task 1] "Quantum computing uses qubits..."
User: [Clicks Task 1] "What are qubits made of?"
Agent: [Receives referenceTaskIds: [Task 1]] "Qubits can be made from..."
```

### 3. Error Correction
```
User: "Calculate 123 * 456"
Agent: [Task 1] "The result is 56088"
User: [Clicks Task 1] "That's correct, thanks!"
Agent: [Receives referenceTaskIds: [Task 1]] "You're welcome!"
```

## Testing

Run the Gradio UI and test the reply feature:

```bash
python examples/agno_example.py
```

Then:
1. Send a message to the agent
2. Click on the agent's response
3. Verify the reply indicator appears
4. Send a follow-up message
5. Check server logs to confirm `referenceTaskIds` is included
