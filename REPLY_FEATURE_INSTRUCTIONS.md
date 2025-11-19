# How to Use the Reply Feature

## Quick Start

1. **Start your agent** (if not already running):
   ```bash
   python examples/agno_example.py
   ```

2. **Send a message** to the agent (e.g., "hi" or "write a poem")

3. **Wait for the agent's response** (green message box)

4. **Click the 👍 (thumbs up) icon** on the right side of the agent's message

5. **See the reply indicator** appear above the input box:
   ```
   💬 Replying to task: 2a35ae09... - Type your reply below
   ```

6. **Type your follow-up message** (e.g., "make it shorter")

7. **Press Enter** to send - your message will include `referenceTaskIds` pointing to the original task

8. **To cancel the reply**, click the 👍 icon again to unlike the message

## What Happens Behind the Scenes

When you like a message and send a reply, the client sends:

```json
{
  "message": {
    "taskId": "new-task-uuid",
    "contextId": "conversation-context-uuid",
    "referenceTaskIds": ["2a35ae09-67a1-4fc1-b0bb-3a4c4850B78F"],
    "parts": [{"kind": "text", "text": "make it shorter"}]
  }
}
```

The agent receives the `referenceTaskIds` and can use it to understand which previous task you're referring to.

## Visual Guide

```
┌─────────────────────────────────────────────────────────────┐
│  research_agent - Bindu Interface 🌻                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: hi                                                   │
│                                                             │
│  ┌───────────────────────────────────────────────────┐ 👍  │  ← 1. Click the thumbs up!
│  │ Agent: Hello! How can I assist you today?         │     │
│  │ 📋 Task Details [COMPLETED]                       │     │
│  │   Task ID: 2a35ae09-67a1-4fc1-b0bb-3a4c4850B78F  │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┤  ← 2. This blue box appears!
│  │ 💬 Replying to task: 2a35ae09... - Type your reply below│
│  └─────────────────────────────────────────────────────────┤
│                                                             │
│  Chat Message                                               │
│  ┌───────────────────────────────────────────────────────┐ │  ← 3. Type your reply here
│  │ Type your message here... (👍 Like an agent message...) │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Location**: The reply indicator appears as a blue box **directly above the input textbox** and **below the chat history**.

## Debugging

If the reply indicator doesn't appear, check the terminal logs for:

```
INFO:bindu.ui.gradio_ui:Message liked: index=1, liked=True
INFO:bindu.ui.gradio_ui:Liked message: role=assistant, task_id=2a35ae09-67a1-4fc1-b0bb-3a4c4850B78F
INFO:bindu.ui.gradio_ui:Setting reply to task: 2a35ae09-67a1-4fc1-b0bb-3a4c4850B78F
```

If you see these logs, the feature is working correctly!

## Troubleshooting

### Issue: Like button doesn't appear
- **Solution**: Make sure you're using Gradio with `type="messages"` chatbot (already configured)

### Issue: Reply indicator doesn't show
- **Solution**: Check that the agent message has metadata with `task_id`. The logs will show if task_id is missing.

### Issue: Agent doesn't use the reference
- **Solution**: The agent needs to be programmed to use `referenceTaskIds`. This is passed in the message payload but the agent logic determines how to use it.

## Example Conversation

```
User: Write a poem about AI
Agent: [Task 1] Here's a long poem about artificial intelligence...
       [👍 Click here]

💬 Replying to task: abc12345...

User: make it shorter
Agent: [Task 2, references Task 1] Here's a shorter version...
```

The second agent response (Task 2) receives `referenceTaskIds: ["Task 1 UUID"]` so it knows you're asking to shorten the previous poem.
