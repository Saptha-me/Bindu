# Task-First Agent Pattern - A2A Protocol Implementation

## Overview

Bindu implements a **Task-First Architecture** following the A2A Protocol specification. This pattern is optimized for **orchestration scenarios** where agents are coordinated by systems like Sapthami.

### Why Task-First?

Bindu agents are designed to be orchestrated by higher-level systems (e.g., Sapthami). In orchestration:
- **Every interaction must be trackable** via Task IDs
- **Parallel execution** requires clear task boundaries
- **Dependency management** needs explicit task states
- **Common protocol** across multiple agent endpoints

This aligns with the A2A "Task-only Agent" pattern where **all responses are Task objects**, even for simple interactions.

## Architecture Pattern

### Task-First vs Message-First

**Bindu uses Task-First** because:
1. Orchestrators (like Sapthami) need Task IDs to track work across multiple agents
2. Parallel task execution requires explicit task boundaries
3. State management is clearer with tasks from the start

**Alternative (Message-First)** is better for:
- Direct user-to-agent interactions
- Chatbot-style interfaces
- Discovery and negotiation phases

### Messages vs Artifacts

| Aspect | Messages | Artifacts |
|--------|----------|-----------|
| **Purpose** | Interaction, negotiation, status updates, explanations | Final deliverable, task output |
| **Task State** | `working`, `input-required`, `auth-required`, `completed`, `failed` | `completed` only |
| **When Used** | During task execution AND at completion | When task completes successfully |
| **Immutability** | Task still mutable (non-terminal) or immutable (terminal) | Task becomes immutable |
| **Content** | Agent's response text, explanations, error messages | Structured deliverable (files, data) |

**Key Distinction:**
- **Intermediate states** (`input-required`, `auth-required`): Message ONLY, no artifacts
- **Completed state**: Message (explanation) + Artifact (deliverable)
- **Failed state**: Message (error explanation) ONLY, no artifacts
- **Canceled state**: State change only, no new content

## Flow Diagram

### Single Agent Flow

```
Context1 (conversation session)
  │
  └─ Task1 (task_id: abc-123) ← CREATED IMMEDIATELY
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

### Orchestration Flow (Sapthami → Multiple Agents)

```
Sapthami (Orchestrator)
  │
  ├─ Task1 → Agent1: "Research Helsinki weather"
  │   ├─ State: working
  │   └─ State: completed → Artifact: weather-data.json
  │
  ├─ Task2 → Agent2: "Book flight" (depends on Task1)
  │   ├─ State: input-required → "How many travelers?"
  │   ├─ Sapthami provides: "2 adults"
  │   └─ State: completed → Artifact: booking.pdf
  │
  ├─ Task3 → Agent3: "Find hotel" (parallel with Task2)
  │   ├─ State: working
  │   └─ State: completed → Artifact: hotel-booking.pdf
  │
  └─ Task4 → Agent4: "Create itinerary" (depends on Task2, Task3)
      ├─ referenceTaskIds: [Task2, Task3]
      └─ State: completed → Artifact: itinerary.pdf

// Sapthami tracks all tasks by ID
// Can execute Task2 and Task3 in parallel
// Task4 waits for Task2 and Task3 to complete
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

### 2. Message and Artifact Handling by State

**Why Both Message and Artifact for Completed Tasks?**

1. **Message**: Provides context and explanation for the task history
   - "Here's your report with the requested analysis"
   - Maintains conversation continuity
   - Useful for debugging and audit trails

2. **Artifact**: Contains the actual deliverable
   - The PDF file, JSON data, or structured output
   - Immutable result that client requested
   - Signed with DID for verification

Both serve different purposes and are part of the complete task record.

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

### ✅ Task-Only Agent Pattern
- Bindu follows the **"Task-generating Agents"** pattern from A2A spec
- Every interaction creates or updates a Task (no standalone Messages)
- Optimized for orchestration and parallel execution

### ✅ Task Immutability
- Once a task reaches terminal state (`completed`, `failed`, `canceled`), it **cannot restart**
- Any refinement creates a **NEW task**

### ✅ Context Continuity
- Multiple tasks share the same `contextId`
- Conversation history preserved across tasks
- Agent infers context from `contextId` and `referenceTaskIds`

### ✅ Parallel Tasks (Critical for Orchestration)
- Multiple tasks can run in parallel within same context
- Each task tracked independently with unique Task ID
- Orchestrator (Sapthami) can manage dependencies via `referenceTaskIds`

### ✅ Artifact Versioning
- Client manages artifact versions (not server)
- Agent uses consistent `artifact-name` for refined versions
- New `artifactId` for each version

## Real-World Example: Scientific Discovery Orchestration

### Inspired by Robin (FutureHouse)

Robin is a multi-agent system that automated the discovery of ripasudil as a novel treatment for age-related macular degeneration. The orchestrator coordinated three specialized agents (Crow for literature review, Falcon for deep analysis, Finch for data analysis) through multiple iterative cycles. This demonstrates the power of Task-First orchestration in complex, real-world scenarios.

### Scenario: Drug Discovery Pipeline

**Goal:** Identify novel therapeutic candidates for a disease

**Orchestrator (Sapthami)** coordinates specialized Bindu agents:
- **LiteratureAgent**: Conducts broad literature reviews
- **HypothesisAgent**: Generates testable hypotheses from literature
- **ExperimentAgent**: Designs experimental protocols
- **AnalysisAgent**: Analyzes experimental data and identifies patterns

#### Phase 1: Initial Hypothesis Generation

```
Task1 → LiteratureAgent: "Review literature on RPE phagocytosis in macular degeneration"
  State: working
  State: completed
  Artifact: literature-review.json (500 papers analyzed)

Task2 → HypothesisAgent: "Generate therapeutic hypotheses from literature review"
  referenceTaskIds: [Task1]
  State: working
  State: input-required → "Should we focus on small molecules or biologics?"

Sapthami provides: "Small molecules"

  State: completed
  Artifact: hypotheses.json (10 candidate mechanisms identified)
```

#### Phase 2: Experimental Design

```
Task3 → ExperimentAgent: "Design screening assay for candidate molecules"
  referenceTaskIds: [Task2]
  State: working
  State: input-required → "What cell line should we use?"

Sapthami provides: "Primary RPE cells"

  State: completed
  Artifact: experimental-protocol.pdf

Task4 → ExperimentAgent: "Select top 10 molecules for initial screen"
  referenceTaskIds: [Task2, Task3]
  State: working
  State: completed
  Artifact: candidate-molecules.csv (including Y-27632, a ROCK inhibitor)
```

#### Phase 3: Data Analysis (First Round)

```
// Human researchers execute physical experiment
// Upload results to system

Task5 → AnalysisAgent: "Analyze phagocytosis screening data"
  referenceTaskIds: [Task3, Task4]
  State: working
  State: completed
  Artifact: analysis-report.json
    - Finding: Y-27632 shows 40% increase in phagocytosis
    - Recommendation: Investigate mechanism via RNA-seq
```

#### Phase 4: Mechanism Investigation

```
Task6 → ExperimentAgent: "Design RNA-seq experiment for Y-27632 mechanism"
  referenceTaskIds: [Task5]
  State: working
  State: completed
  Artifact: rnaseq-protocol.pdf

// Human researchers execute RNA-seq
// Upload sequencing data

Task7 → AnalysisAgent: "Analyze RNA-seq data for Y-27632 treatment"
  referenceTaskIds: [Task6]
  State: working
  State: completed
  Artifact: differential-expression.csv
    - Finding: ABCA1 upregulated 3.2-fold
    - Finding: Lipid efflux pathway activated
```

#### Phase 5: Clinical Translation

```
Task8 → HypothesisAgent: "Identify clinically-approved ROCK inhibitors"
  referenceTaskIds: [Task5, Task7]
  State: working
  State: completed
  Artifact: clinical-candidates.json
    - Ripasudil (approved for glaucoma)
    - Netarsudil (approved for glaucoma)

Task9 → ExperimentAgent: "Design validation assay for ripasudil"
  referenceTaskIds: [Task8]
  State: working
  State: completed
  Artifact: validation-protocol.pdf

// Human researchers validate ripasudil
// Upload validation data

Task10 → AnalysisAgent: "Analyze ripasudil validation results"
  referenceTaskIds: [Task9]
  State: working
  State: completed
  Artifact: final-report.pdf
    - Discovery: Ripasudil shows superior phagocytosis enhancement
    - Novel therapeutic candidate identified
```

### Why Task-First Enables This

**Without Task IDs (Message-First):**
- Sapthami couldn't track which agent is analyzing which dataset
- Parallel execution impossible (Task3 and Task4 couldn't run simultaneously)
- No clear dependency chain (Task7 depends on Task6 completion)
- Difficult to resume after human-in-the-loop steps

**With Task-First:**
- ✅ Each agent's work tracked by unique Task ID
- ✅ Parallel execution when dependencies allow
- ✅ Clear audit trail: Task1 → Task2 → Task5 → Task7 → Task10
- ✅ Human-in-the-loop integration via task state management
- ✅ Reproducible scientific workflow

### Key Insights from Robin's Success

1. **Orchestration Complexity**: Robin coordinated 3 specialized agents through multiple iterative cycles—impossible without Task IDs for tracking

2. **Human-in-the-Loop**: Physical experiments required human execution, but agents designed and analyzed them—Task states managed the handoff

3. **Dependency Management**: Later tasks (mechanism investigation) depended on earlier results (initial screening)—`referenceTaskIds` made this explicit

4. **Speed**: Entire discovery completed in 2.5 months because agents could work in parallel when dependencies allowed

5. **Reproducibility**: Every hypothesis, analysis, and figure was AI-generated and traceable through task history

## Storage Interface

The storage layer supports this pattern through:


## Key Takeaways

1. **Task-First for Orchestration** - Every interaction creates a Task immediately
2. **Messages = Interaction** (task open) - Used within tasks for multi-turn collaboration
3. **Artifacts = Deliverable** (task complete) - Final output attached to task
4. **Terminal tasks are immutable** (A2A protocol)
5. **Refinements create new tasks** (same contextId)
6. **Parallel execution via Task IDs** - Critical for orchestrators like Sapthami
7. **Client manages versions** (not server)

## Orchestration Benefits

### For Sapthami (Orchestrator):
- ✅ **Track multiple agents** via Task IDs
- ✅ **Manage dependencies** using `referenceTaskIds`
- ✅ **Parallel execution** with clear task boundaries
- ✅ **State monitoring** across all agent tasks
- ✅ **Common protocol** for all Bindu agents

### For Bindu Agents:
- ✅ **Consistent interface** - always return Tasks
- ✅ **Clear state transitions** - working → input-required → completed
- ✅ **Artifact delivery** - structured output format
- ✅ **Context awareness** - access to conversation history

---

*This Task-First pattern ensures Bindu agents are optimized for orchestration scenarios while maintaining full A2A protocol compliance.*
