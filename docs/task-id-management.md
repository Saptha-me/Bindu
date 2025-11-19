# Task ID Management - A2A Protocol Compliance

## Overview

Bindu implements the A2A protocol's task immutability rules correctly across both backend and frontend.

## Backend Implementation

The backend (`memory_storage.py`) handles task continuation automatically:

```python
async def submit_task(self, context_id: UUID, message: Message) -> Task:
    """Create a new task or continue an existing non-terminal task.
    
    - If task exists and is in non-terminal state: Append message and reset to 'submitted'
    - If task exists and is in terminal state: Raise error (immutable)
    - If task doesn't exist: Create new task
    """
```

### Backend Logic

1. **Non-Terminal States** (`input-required`, `auth-required`):
   - Task is **mutable**
   - Appends new message to existing task's history
   - Resets state to `submitted` for re-execution

2. **Terminal States** (`completed`, `failed`, `canceled`):
   - Task is **immutable**
   - Raises `ValueError` if client tries to reuse task ID
   - Client must create new task with `referenceTaskIds`

## Frontend Implementation

The frontend (`app.js`) must send the correct task ID based on current state:

### Task ID Decision Logic

```javascript
// Non-terminal states (input-required, auth-required): REUSE task ID
if (isNonTerminalState && currentTaskId) {
    taskId = currentTaskId;  // Continue same task
}

// Terminal states (completed, failed, canceled): CREATE new task
else if (currentTaskId) {
    taskId = generateId();  // New task
    referenceTaskIds.push(currentTaskId);  // Link to previous
}
```

### State Tracking

The frontend tracks:
- `currentTaskId`: Last task ID
- `currentTaskState`: Current task state (e.g., `input-required`, `completed`)

This allows the frontend to decide whether to reuse or create a new task ID.

## Example Flow

### Scenario: Agent Asks for Clarification

```
User: "provide a sunset quote"
  → Creates Task A (new UUID)
  → State: submitted → working

Agent: "Do you want Instagram, Pinterest, or General?"
  → Task A state: input-required
  → currentTaskId = Task A
  → currentTaskState = "input-required"

User: "insta"
  → REUSES Task A (same UUID)
  → Backend appends message to Task A's history
  → Task A state: submitted → working → completed

Agent: "Chasing sunsets and dreams. 🌅✨"
  → Task A state: completed
  → currentTaskId = Task A
  → currentTaskState = "completed"

User: "make it shorter"
  → CREATES Task B (new UUID)
  → referenceTaskIds: [Task A]
  → Task B state: submitted → working → completed
```

## Key Differences

| State Type | Task Mutability | Frontend Action | Backend Action |
|------------|----------------|-----------------|----------------|
| `input-required` | Mutable | Reuse task ID | Append to history |
| `auth-required` | Mutable | Reuse task ID | Append to history |
| `completed` | Immutable | Create new task | Reject if reused |
| `failed` | Immutable | Create new task | Reject if reused |
| `canceled` | Immutable | Create new task | Reject if reused |

## A2A Protocol Compliance ✅

- ✅ **Task Immutability**: Terminal tasks cannot be modified
- ✅ **Task Continuation**: Non-terminal tasks can receive additional messages
- ✅ **Context Continuity**: All tasks share same `contextId`
- ✅ **Dependency Tracking**: `referenceTaskIds` links related tasks
- ✅ **Conversation Flow**: Natural multi-turn interactions

## Implementation Files

- **Backend**: `/bindu/server/storage/memory_storage.py` (lines 83-175)
- **Frontend**: `/bindu/ui/static/app.js` (lines 188-212, 320-350)
