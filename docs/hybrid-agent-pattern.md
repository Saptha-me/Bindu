# Hybrid Agent Pattern - A2A Protocol Implementation

## Overview

Bindu implements a **Hybrid Agent Architecture** following the A2A Protocol specification. This pattern combines the flexibility of Messages for interaction with the reliability of Artifacts for final deliverables.

## Architecture Pattern

### Messages vs Artifacts

| Aspect | Messages | Artifacts |
|--------|----------|-----------|
| **Purpose** | Interaction, negotiation, status updates | Final deliverable, task output |
| **Task State** | `working`, `input-required`, `auth-required` | `completed` (terminal) |
| **When Used** | During task execution | When task completes |
| **Immutability** | Task still mutable | Task becomes immutable |

## Flow Diagram

```
Context1 (conversation session)
  │
  └─ Task1 (task_id: abc-123)
      │
      ├─ [1] User Input: "Create a report"
      │   └─> Agent Processing...
      │       └─> State: working
      │
      ├─ [2] Agent Response: "What format would you like?"
      │   └─> Message (no artifact)
      │   └─> State: input-required
      │   └─> Task still OPEN
      │
      ├─ [3] User Input: "PDF format"
      │   └─> Agent Processing...
      │       └─> State: working
      │
      └─ [4] Agent Response: "Here's your report"
          └─> Message + Artifact (PDF file)
          └─> State: completed
          └─> Task now IMMUTABLE ✓
```

## Refinement Flow (New Task)

When a user wants to refine a completed task, a **NEW task** is created:

```
Context1 (same conversation)
  │
  ├─ Task1 (completed, immutable)
  │   └─ Artifact: report.pdf
  │
  └─ Task2 (new task, references Task1)
      │
      ├─ User Input: "Make it shorter"
      │   └─> referenceTaskIds: [Task1]
      │   └─> contextId: Context1 (same)
      │
      └─ Agent Response: "Here's the shorter version"
          └─> Message + Artifact (new report.pdf)
          └─> State: completed
          └─> New artifactId, same artifact name
```

## Implementation Details

### 1. Task States

```python
# Non-Terminal States (Task Open)
- "submitted"      # Initial state
- "working"        # Agent processing
- "input-required" # Waiting for user input
- "auth-required"  # Waiting for authentication

# Terminal States (Task Immutable)
- "completed"      # Success with artifacts
- "failed"         # Error occurred
- "canceled"       # User canceled
- "rejected"       # Agent rejected
```

### 2. Worker Logic

```python
async def run_task(self, params: TaskSendParams):
    # 1. Load task and set to 'working'
    task = await self.storage.load_task(params["task_id"])
    await self.storage.update_task(task["task_id"], state="working")
    
    # 2. Execute agent
    results = self.manifest.run(conversation_context)
    
    # 3. Determine response type
    if self._is_input_required(results):
        # Message only, keep task open
        await self.storage.update_task(
            task["task_id"], 
            state="input-required"
        )
        # Save message to context
        agent_messages = MessageConverter.to_protocol_messages(results, ...)
        await self.storage.append_to_contexts(task["context_id"], agent_messages)
        
    elif self._is_auth_required(results):
        # Message only, keep task open
        await self.storage.update_task(
            task["task_id"], 
            state="auth-required"
        )
        # Save message to context
        agent_messages = MessageConverter.to_protocol_messages(results, ...)
        await self.storage.append_to_contexts(task["context_id"], agent_messages)
        
    else:
        # Message + Artifact, complete task
        agent_messages = MessageConverter.to_protocol_messages(results, ...)
        artifacts = self.build_artifacts(results)
        
        await self.storage.update_task(
            task["task_id"], 
            state="completed",
            new_artifacts=artifacts,
            new_messages=agent_messages
        )
```

### 3. Structured Response Format

Agents can return structured JSON to control state transitions:

```json
// Input Required
{
  "state": "input-required",
  "prompt": "What format would you like for the report?"
}

// Auth Required
{
  "state": "auth-required",
  "prompt": "Please provide your API key",
  "auth_type": "api_key",
  "service": "openai"
}

// Normal Response (will complete with artifact)
"Here's your report: [content]"
```

## A2A Protocol Compliance

### ✅ Task Immutability
- Once a task reaches terminal state (`completed`, `failed`, `canceled`), it **cannot restart**
- Any refinement creates a **NEW task**

### ✅ Context Continuity
- Multiple tasks share the same `contextId`
- Conversation history preserved across tasks
- Agent infers context from `contextId` and `referenceTaskIds`

### ✅ Parallel Tasks
- Multiple tasks can run in parallel within same context
- Each task tracked independently

### ✅ Artifact Versioning
- Client manages artifact versions (not server)
- Agent uses consistent `artifact-name` for refined versions
- New `artifactId` for each version

## Example Scenarios

### Scenario 1: Simple Completion

```
User: "What's 2+2?"
Agent: "4" → Message + Artifact → completed
```

### Scenario 2: Multi-turn Interaction

```
User: "Book a flight"
Agent: "Where to?" → Message → input-required

User: "Helsinki"
Agent: "When?" → Message → input-required

User: "Next Monday"
Agent: "Booked!" → Message + Artifact → completed
```

### Scenario 3: Refinement (New Task)

```
Task1:
  User: "Generate logo"
  Agent: [logo.png] → Artifact → completed

Task2 (references Task1):
  User: "Make it blue"
  Agent: [logo.png v2] → Artifact → completed
```

## Storage Interface

The storage layer supports this pattern through:

```python
class Storage(ABC):
    # Task operations
    async def submit_task(context_id, message) -> Task
    async def update_task(task_id, state, artifacts?, messages?) -> Task
    async def load_task(task_id) -> Task
    
    # Context operations
    async def append_to_contexts(context_id, messages) -> None
    async def load_context(context_id) -> Context
    async def list_tasks_by_context(context_id) -> list[Task]
```

## Key Takeaways

1. **Messages = Interaction** (task open)
2. **Artifacts = Deliverable** (task complete)
3. **Terminal tasks are immutable** (A2A protocol)
4. **Refinements create new tasks** (same contextId)
5. **Client manages versions** (not server)

---

*This pattern ensures clean separation between conversation flow (Messages) and final outputs (Artifacts) while maintaining A2A protocol compliance.*
