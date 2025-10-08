# Orchestration Architecture: Sapthami ↔ Bindu

## Overview

This document explains how **Sapthami (orchestrator)** coordinates multiple **Bindu agents** using the A2A protocol's Task-First pattern.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Sapthami (Orchestrator)              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Task Dependency Graph                   │   │
│  │                                                 │   │
│  │   Task1 ──┐                                     │   │
│  │           ├──> Task4 (depends on 1,2,3)         │   │
│  │   Task2 ──┤                                     │   │
│  │           │                                     │   │
│  │   Task3 ──┘                                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Task State Manager                      │   │
│  │  - Track all task states                        │   │
│  │  - Monitor progress                             │   │
│  │  - Handle input-required states                 │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Agent 1  │   │ Agent 2  │   │ Agent 3  │
    │ (Bindu)  │   │ (Bindu)  │   │ (Bindu)  │
    └──────────┘   └──────────┘   └──────────┘
```

## Why Task-First for Orchestration?

### Problem: Message-First Doesn't Scale

```
❌ Message-First Approach:

Sapthami → Agent1: "Research weather"
Agent1 → Sapthami: Message("Where?")  // No task ID!

Sapthami → Agent2: "Book flight"
Agent2 → Sapthami: Message("When?")   // No task ID!

Sapthami → Agent3: "Find hotel"
Agent3 → Sapthami: Message("Which city?")  // No task ID!

// Problem: How does Sapthami know which response belongs to which agent?
// Problem: How to track parallel execution?
// Problem: How to manage dependencies?
```

### Solution: Task-First Provides Structure

```
✅ Task-First Approach:

Sapthami → Agent1: "Research weather"
Agent1 → Sapthami: Task(id: "task-1", state: "input-required", msg: "Where?")

Sapthami → Agent2: "Book flight"
Agent2 → Sapthami: Task(id: "task-2", state: "input-required", msg: "When?")

Sapthami → Agent3: "Find hotel"
Agent3 → Sapthami: Task(id: "task-3", state: "input-required", msg: "Which city?")

// Solution: Clear task IDs for tracking
// Solution: Parallel execution with independent tasks
// Solution: Dependencies via referenceTaskIds
```

## Real-World Orchestration: Scientific Discovery

### Inspired by Robin (FutureHouse)

Robin is a multi-agent system that successfully discovered ripasudil as a novel treatment for age-related macular degeneration in just 2.5 months. The system orchestrated three specialized agents (Crow, Falcon, Finch) through iterative cycles of hypothesis generation, experimental design, and data analysis. This demonstrates how Task-First orchestration enables complex, real-world scientific workflows.

**Key Achievement:** All hypotheses, experimental plans, data analyses, and figures were AI-generated and traceable through task history.

## Orchestration Flow Example

### Scenario: Scientific Discovery (Robin-Inspired)

This example shows how Sapthami orchestrates specialized Bindu agents for drug discovery, mirroring Robin's successful approach.

```
Step 1: Initial Literature Review
Sapthami → LiteratureAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "parts": [{"text": "Review literature on RPE phagocytosis in macular degeneration"}]
  }
}

LiteratureAgent → Sapthami: {
  "kind": "task",
  "id": "task-lit-review-100",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "literature-review.json",
    "parts": [{"data": {"papers_analyzed": 500, "key_findings": [...]}}]
  }]
}

Step 2: Hypothesis Generation
Sapthami → HypothesisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-lit-review-100"],
    "parts": [{"text": "Generate therapeutic hypotheses from literature"}]
  }
}

HypothesisAgent → Sapthami: {
  "kind": "task",
  "id": "task-hypothesis-200",
  "status": {"state": "input-required"},
  "history": [{
    "role": "agent",
    "parts": [{"text": "Should we focus on small molecules or biologics?"}]
  }]
}

Sapthami → HypothesisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "taskId": "task-hypothesis-200",
    "parts": [{"text": "Small molecules"}]
  }
}

HypothesisAgent → Sapthami: {
  "kind": "task",
  "id": "task-hypothesis-200",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "hypotheses.json",
    "parts": [{"data": {"mechanisms": 10, "top_target": "ROCK pathway"}}]
  }]
}

Step 3: Parallel Experimental Design
// Task 3a: Design screening assay
Sapthami → ExperimentAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-hypothesis-200"],
    "parts": [{"text": "Design screening assay for candidate molecules"}]
  }
}

// Task 3b: Select candidate molecules (parallel with 3a)
Sapthami → ExperimentAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-hypothesis-200"],
    "parts": [{"text": "Select top 10 molecules targeting ROCK pathway"}]
  }
}

// Both tasks complete in parallel
ExperimentAgent → Sapthami: {
  "kind": "task",
  "id": "task-assay-design-300",
  "status": {"state": "completed"},
  "artifacts": [{"name": "screening-protocol.pdf"}]
}

ExperimentAgent → Sapthami: {
  "kind": "task",
  "id": "task-molecule-selection-301",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "candidate-molecules.csv",
    "parts": [{"data": {"molecules": ["Y-27632", "Ripasudil", ...]}}]
  }]
}

Step 4: Human-in-the-Loop Experiment Execution
// Human researchers execute physical experiment
// Upload experimental data to system

Step 5: Data Analysis
Sapthami → AnalysisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-assay-design-300", "task-molecule-selection-301"],
    "parts": [{"text": "Analyze phagocytosis screening data"}]
  }
}

AnalysisAgent → Sapthami: {
  "kind": "task",
  "id": "task-analysis-400",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "analysis-report.json",
    "parts": [{
      "data": {
        "top_hit": "Y-27632",
        "effect_size": "40% increase",
        "recommendation": "Investigate mechanism via RNA-seq"
      }
    }]
  }]
}

Step 6: Iterative Mechanism Investigation
// Sapthami creates new task for RNA-seq design
Sapthami → ExperimentAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-analysis-400"],
    "parts": [{"text": "Design RNA-seq experiment for Y-27632 mechanism"}]
  }
}

// After human execution and data upload
Sapthami → AnalysisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-rnaseq-design-500"],
    "parts": [{"text": "Analyze RNA-seq differential expression"}]
  }
}

AnalysisAgent → Sapthami: {
  "kind": "task",
  "id": "task-rnaseq-analysis-600",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "differential-expression.csv",
    "parts": [{
      "data": {
        "top_gene": "ABCA1",
        "fold_change": 3.2,
        "pathway": "lipid efflux"
      }
    }]
  }]
}

Step 7: Clinical Translation
Sapthami → HypothesisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-analysis-400", "task-rnaseq-analysis-600"],
    "parts": [{"text": "Identify clinically-approved ROCK inhibitors"}]
  }
}

HypothesisAgent → Sapthami: {
  "kind": "task",
  "id": "task-clinical-700",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "clinical-candidates.json",
    "parts": [{
      "data": {
        "candidates": [
          {"name": "Ripasudil", "indication": "glaucoma", "status": "approved"},
          {"name": "Netarsudil", "indication": "glaucoma", "status": "approved"}
        ]
      }
    }]
  }]
}

Step 8: Final Validation
// Design validation → Human execution → Analysis
// Final task completes the discovery

Sapthami → AnalysisAgent: {
  "message": {
    "contextId": "ctx-discovery-001",
    "referenceTaskIds": ["task-validation-design-800"],
    "parts": [{"text": "Analyze ripasudil validation results"}]
  }
}

AnalysisAgent → Sapthami: {
  "kind": "task",
  "id": "task-final-analysis-900",
  "status": {"state": "completed"},
  "artifacts": [{
    "name": "discovery-report.pdf",
    "parts": [{
      "data": {
        "discovery": "Ripasudil shows superior phagocytosis enhancement",
        "novel_target": "ABCA1 upregulation",
        "clinical_potential": "Novel treatment for macular degeneration"
      }
    }]
  }]
}

Step 9: Sapthami synthesizes results
Sapthami → User: "Discovery complete! Ripasudil identified as novel therapeutic candidate."

// Task dependency chain:
// task-100 → task-200 → [task-300, task-301] → task-400 → task-500 → task-600 → task-700 → task-800 → task-900
// Total: 9 tasks across 4 specialized agents, completed in 2.5 months (Robin's actual timeline)
```

### Why This Works with Task-First

**Critical Success Factors:**

1. **Task Tracking**: Each agent's work (literature review, hypothesis, analysis) has unique Task ID
2. **Parallel Execution**: Task-300 and Task-301 run simultaneously when dependencies allow
3. **Dependency Chain**: Task-600 (RNA-seq analysis) explicitly depends on Task-400 (initial screening)
4. **Human-in-the-Loop**: Task states manage handoff between AI planning and human execution
5. **Reproducibility**: Complete audit trail from initial literature review to final discovery
6. **Iterative Refinement**: New tasks reference previous results via `referenceTaskIds`

**Without Task IDs, this would be impossible:**
- No way to track which analysis corresponds to which experiment
- Parallel execution blocked (can't run assay design and molecule selection together)
- Dependency management unclear (when can RNA-seq analysis start?)
- Human handoff ambiguous (which task needs experimental data?)

## Task State Management

### Sapthami's Responsibilities

The orchestrator manages task lifecycle, dependency resolution, and state transitions across multiple agents:

- **Decompose user requests** into subtasks mapped to specialized agents
- **Build dependency graphs** to determine execution order
- **Execute tasks** respecting dependencies and parallel opportunities
- **Track task states** across all agents (working, input-required, completed)
- **Handle input-required states** by providing context or user input
- **Monitor completion** and trigger dependent tasks

## Parallel Execution

### Task Dependency Graph

The orchestrator maintains a dependency graph to enable parallel execution:

- **Add tasks** with explicit dependencies via `referenceTaskIds`
- **Check readiness** by verifying all dependencies are completed
- **Get ready tasks** that can execute immediately
- **Execute in parallel** when multiple tasks have no blocking dependencies
- **Topological sort** ensures correct execution order

## Benefits of Task-First for Orchestration

### 1. **Clear Tracking**
Sapthami can track all tasks by unique ID, knowing which agent owns each task and its current state.

### 2. **Dependency Management**
Tasks explicitly declare dependencies via `referenceTaskIds`, making it clear when a task can start execution.

### 3. **Parallel Execution**
Multiple tasks can run simultaneously when dependencies allow, significantly reducing total execution time.

### 4. **State Monitoring**
Orchestrator monitors all agent states and handles different conditions (input-required, failed, completed) appropriately.

### 5. **Common Protocol**
All Bindu agents use the same interface - always returning Task objects with consistent structure and IDs.

## Comparison: Task-First vs Message-First

| Aspect | Task-First (Bindu) | Message-First |
|--------|-------------------|---------------|
| **Tracking** | ✅ Task ID from start | ❌ No ID until task created |
| **Parallel Execution** | ✅ Clear task boundaries | ❌ Ambiguous message threads |
| **Dependencies** | ✅ `referenceTaskIds` | ❌ Hard to track |
| **State Management** | ✅ Task state per agent | ❌ Must infer from messages |
| **Orchestration** | ✅ Perfect for Sapthami | ❌ Complex to coordinate |
| **User Chat** | ⚠️ Creates many tasks | ✅ Lightweight messages |

## Key Takeaways

1. **Task-First is optimal for orchestration** - Sapthami needs Task IDs to coordinate multiple agents
2. **Every Bindu agent returns Tasks** - Consistent protocol across all endpoints
3. **Parallel execution via Task IDs** - Clear boundaries for concurrent work
4. **Dependency management via `referenceTaskIds`** - Explicit task relationships
5. **State tracking per task** - Sapthami monitors all agent progress
6. **A2A compliant** - Follows "Task-generating Agents" pattern

---

*This architecture ensures Sapthami can efficiently orchestrate multiple Bindu agents using a common, trackable protocol.*
