# Bindu Negotiation System: Capability-Based Agent Selection

## Overview

Implement a capability assessment system that enables orchestrator agents to intelligently select the best Bindu agent for a task from multiple available agents. This system allows agents to advertise their capabilities, current load, and pricing, enabling orchestrators to make informed routing decisions.

---

## Goals

- Enable orchestrators to query multiple Bindu agents for task capability
- Allow agents to self-assess their fitness for specific tasks
- Provide multi-factor scoring for intelligent agent selection
- Support future multi-round negotiation capabilities
- Maintain backward compatibility with existing Bindu protocol

---

## Architecture

```
┌─────────────┐
│ Orchestrator│
│   Agent     │
└──────┬──────┘
       │
       │ 1. Broadcast Assessment Request
       ├──────────────────────────────────┐
       │                                  │
       ▼                                  ▼
┌──────────────┐                  ┌──────────────┐
│  Bindu Agent │                  │  Bindu Agent │
│      #1      │                  │      #N      │
└──────┬───────┘                  └──────┬───────┘
       │                                  │
       │ 2. Calculate Capability          │
       │    - Skill matching              │
       │    - Load assessment             │
       │    - Performance metrics         │
       │                                  │
       │ 3. Return Assessment             │
       └──────────────┬───────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ Orchestrator │
              │   Ranking    │
              │   Algorithm  │
              └──────┬───────┘
                     │
                     │ 4. Select Winner
                     ▼
              ┌──────────────┐
              │  Execute     │
              │  Task        │
              └──────────────┘
```

---

## Phase 1: Single-Turn Assessment (MVP)

### 1.1 New Components

#### **CapabilityCalculator** (`bindu/server/capability_calculator.py`)

**Purpose:** Calculate how well an agent can handle a specific task

**Key Methods:**
- `calculate_capability_score(task_request: dict) -> dict`
  - Extracts required skills from task description
  - Matches against agent's skill registry
  - Factors in current queue load
  - Returns confidence score (0-1)

- `_extract_required_skills(task_request: dict) -> list[str]`
  - Keyword matching against skill names and tags
  - Parses task description for skill indicators
  - Returns list of required skill IDs

- `_calculate_skill_match(required_skills: list[str]) -> float`
  - Compares required skills vs agent skills
  - Returns match percentage (0-1)
  - Perfect match = 1.0, no match = 0.0

- `_check_capabilities(task_request: dict) -> float`
  - Checks for special requirements (streaming, tools, etc.)
  - Validates against agent's capabilities
  - Returns capability match score (0-1)

- `_calculate_load_factor() -> float`
  - Queries scheduler for current queue length
  - Calculates availability score
  - Empty queue = 1.0, full queue = 0.0

- `_get_matched_skills(required_skills: list[str]) -> list[dict]`
  - Returns detailed information about matched skills
  - Includes skill ID, name, version, specialization

- `_get_missing_requirements(required_skills: list[str]) -> list[str]`
  - Identifies skills the agent lacks
  - Used for transparency in assessment response

**Scoring Formula:**
```python
confidence_score = (
    skill_match_score * 0.6 +      # Primary factor
    capability_score * 0.3 +        # Secondary factor
    load_factor * 0.1               # Availability factor
)
```

---

#### **NegotiationHandlers** (`bindu/server/handlers/negotiation.py`)

**Purpose:** Handle negotiation/assessment endpoint requests

**Key Methods:**
- `assess_task(request: dict) -> dict`
  - Main entry point for assessment requests
  - Orchestrates capability calculation
  - Builds assessment response
  - Returns structured JSON response

- `_estimate_completion_time(task: dict) -> int`
  - Estimates task completion time in seconds
  - Uses skill performance metrics if available
  - Falls back to default estimate

**Response Structure:**
```json
{
  "agent_id": "uuid",
  "agent_name": "string",
  "assessment": {
    "can_handle": boolean,
    "confidence_score": float,
    "skill_matches": [
      {
        "id": "skill-id",
        "name": "skill-name",
        "version": "1.0.0",
        "specialization": "domain",
        "confidence": float
      }
    ],
    "missing_requirements": ["skill-name"]
  },
  "performance_metrics": {
    "current_queue_length": int,
    "avg_completion_time_estimate": int
  },
  "pricing": {
    "execution_cost": {
      "amount": "string",
      "token": "string",
      "network": "string"
    }
  },
  "timestamp": "ISO-8601"
}
```

---

### 1.2 Integration Points

#### **TaskManager Updates** (`bindu/server/task_manager.py`)

**Changes Required:**

1. **Import NegotiationHandlers:**
```python
from .handlers.negotiation import NegotiationHandlers
```

2. **Initialize in `__aenter__`:**
```python
self._negotiation_handlers = NegotiationHandlers(
    scheduler=self.scheduler,
    storage=self.storage,
    manifest=self.manifest,
)
```

3. **Add to `__getattr__` delegation:**
```python
# Negotiation handler methods
if name in ("assess_task", "get_assessment"):
    return getattr(self._negotiation_handlers, name)
```

---

#### **REST Endpoint** (`bindu/server/endpoints/negotiation.py`)

**New Endpoint:** `POST /negotiate/assess`

**Purpose:** Accept assessment requests from orchestrators

**Implementation:**
```python
@handle_endpoint_errors("task assessment")
async def assess_task_endpoint(app: BinduApplication, request: Request) -> Response:
    """
    Assess agent capability for a task.

    Request Body:
    {
      "task": {
        "description": "string",
        "requirements": {
          "skills": ["skill-name"],
          "domain": "string",
          ...
        }
      }
    }

    Returns:
    - 200: Assessment response
    - 400: Invalid request
    - 500: Server error
    """
```

**Error Handling:**
- Invalid JSON → 400 Bad Request
- Missing manifest → 500 Internal Server Error
- Calculation errors → 500 with error details

---

#### **Router Registration** (`bindu/server/endpoints/__init__.py`)

**Add Route:**
```python
Route("/negotiate/assess", assess_task_endpoint, methods=["POST"])
```

---

### 1.3 Protocol Extensions

#### **Update Protocol Types** (`bindu/common/protocol/types.py`)

**New Types to Add:**

```python
class TaskAssessmentRequest(TypedDict):
    """Request for task capability assessment."""
    task: TaskDescription
    orchestrator_id: NotRequired[str]
    assessment_id: NotRequired[str]

class TaskDescription(TypedDict):
    """Description of task for assessment."""
    description: str
    requirements: NotRequired[Dict[str, Any]]
    priority: NotRequired[Literal["low", "medium", "high"]]
    deadline: NotRequired[str]

class CapabilityAssessment(TypedDict):
    """Agent's self-assessment of task capability."""
    can_handle: bool
    confidence_score: float
    skill_matches: List[SkillMatch]
    missing_requirements: List[str]

class SkillMatch(TypedDict):
    """Details of a matched skill."""
    id: str
    name: str
    version: NotRequired[str]
    specialization: NotRequired[str]
    confidence: float

class AssessmentResponse(TypedDict):
    """Complete assessment response from agent."""
    agent_id: str
    agent_name: str
    assessment: CapabilityAssessment
    performance_metrics: PerformanceMetrics
    pricing: NotRequired[ExecutionCost]
    timestamp: str

class PerformanceMetrics(TypedDict):
    """Current agent performance metrics."""
    current_queue_length: int
    avg_completion_time_estimate: int
    success_rate: NotRequired[float]
    uptime_percentage: NotRequired[float]
```

---

### 1.4 Configuration Extensions

#### **Agent Config Updates** (`examples/simple_agent_config.json`)

**Add Negotiation Section:**
```json
{
  "execution_cost": {
    "amount": "$0.0001",
    "token": "USDC",
    "network": "base-sepolia",
    "pay_to_address": "0x...",
    "protected_methods": ["message/send"]
  },
  "negotiation": {
    "enabled": true,
    "strategy": "rule_based",
    "assessment_timeout_ms": 5000,
    "factors": {
      "skill_match_weight": 0.6,
      "capability_weight": 0.3,
      "load_weight": 0.1
    }
  }
}
```

**Configuration Fields:**
- `enabled`: Enable/disable negotiation endpoint
- `strategy`: `"rule_based"` or `"llm_enhanced"` (future)
- `assessment_timeout_ms`: Max time for assessment calculation
- `factors`: Weights for scoring algorithm (customizable per agent)

---

### 1.5 Skill System Enhancements

#### **Skill YAML Extensions** (`examples/skills/*/skill.yaml`)

**Add Assessment Hints:**
```yaml
# Existing fields...
name: translation
description: "Translate documents between languages"

# New assessment fields
assessment:
  keywords:
    - translate
    - translation
    - language
    - español
    - spanish

  specializations:
    - domain: technical
      confidence_boost: 0.2
    - domain: legal
      confidence_boost: 0.1

  anti_patterns:
    - "real-time voice"
    - "simultaneous interpretation"

  complexity_indicators:
    simple:
      - "short text"
      - "single sentence"
    medium:
      - "document"
      - "article"
    complex:
      - "technical manual"
      - "legal contract"
```

**Purpose:**
- `keywords`: Help identify when this skill is needed
- `specializations`: Boost confidence for domain matches
- `anti_patterns`: Reduce confidence for unsupported use cases
- `complexity_indicators`: Estimate task difficulty

---

## Phase 2: Enhanced Assessment (Future)

### 2.1 LLM-Based Task Analysis

**Purpose:** Use agent's LLM to analyze task semantics

**Implementation:**
```python
class LLMCapabilityAnalyzer:
    async def analyze_task(self, task_description: str, agent_skills: list) -> dict:
        """
        Use LLM to deeply understand task requirements.

        Prompt:
        "You are {agent_name} with skills: {skills}.
        Analyze this task: {task_description}

        Provide:
        1. Confidence (0-1) you can handle it
        2. Which skills you'll use
        3. Estimated complexity
        4. Any concerns or limitations

        Return JSON."
        """
```

**Benefits:**
- Understands nuanced task descriptions
- Better handles ambiguous requirements
- Can reason about edge cases

**Tradeoffs:**
- Slower (LLM call required)
- Costs money (API usage)
- Less deterministic

**Configuration:**
```json
"negotiation": {
  "strategy": "llm_enhanced",
  "llm_analysis": {
    "enabled": true,
    "model": "gpt-4",
    "max_tokens": 500,
    "temperature": 0.3,
    "cache_results": true
  }
}
```

---

### 2.2 Historical Performance Tracking

**Purpose:** Use past performance to improve confidence scores

**New Storage:**
```python
# bindu/server/storage/performance_tracker.py

class PerformanceTracker:
    async def record_task_result(
        self,
        task_id: str,
        skill_used: str,
        success: bool,
        completion_time: int,
        confidence_claimed: float
    ):
        """Track actual vs claimed performance."""

    async def get_skill_performance(self, skill_id: str) -> dict:
        """
        Returns:
        {
            "success_rate": 0.95,
            "avg_completion_time": 45,
            "confidence_accuracy": 0.92,
            "total_tasks": 150
        }
        """
```

**Usage in Assessment:**
```python
# Adjust confidence based on historical accuracy
historical_data = await tracker.get_skill_performance(skill_id)
adjusted_confidence = base_confidence * historical_data["confidence_accuracy"]
```

---

### 2.3 Dynamic Pricing

**Purpose:** Adjust pricing based on demand and capability

**Implementation:**
```python
class DynamicPricingCalculator:
    def calculate_price(
        self,
        base_price: float,
        confidence: float,
        queue_length: int,
        task_complexity: str
    ) -> dict:
        """
        Returns:
        {
            "min_price": float,
            "max_price": float,
            "recommended_price": float
        }
        """

        # Higher confidence = can charge more
        confidence_multiplier = 0.8 + (confidence * 0.4)

        # Higher load = charge more
        load_multiplier = 1.0 + (queue_length * 0.1)

        # Complex tasks = charge more
        complexity_multipliers = {
            "simple": 0.8,
            "medium": 1.0,
            "complex": 1.5
        }

        final_price = (
            base_price *
            confidence_multiplier *
            load_multiplier *
            complexity_multipliers[task_complexity]
        )
```

---

## Phase 3: Multi-Round Negotiation (Future)

### 3.1 Negotiation State Management

**Purpose:** Support back-and-forth negotiation

**New Components:**
- `NegotiationSession`: Track negotiation state
- `NegotiationRound`: Individual offer/counter-offer
- `NegotiationStrategy`: Agent's negotiation logic

**Flow:**
```
1. Orchestrator: Initial request
2. Agent: Initial bid
3. Orchestrator: Counter-offer
4. Agent: Accept/Reject/Counter
5. ... (multiple rounds)
6. Final: Agreement or rejection
```

---

## Real-World Example

### Scenario: User Needs Spanish Translation

**Step 1: User Request**
```
User: "Translate this technical manual from English to Spanish"
UI: Shows 10 available translation agents
User: Selects all 10 agents
```

**Step 2: Orchestrator Broadcasts**
```json
POST http://translation-agent-{1-10}:3773/negotiate/assess
{
  "task": {
    "description": "Translate technical manual from English to Spanish",
    "requirements": {
      "source_language": "en",
      "target_language": "es",
      "domain": "technical"
    }
  }
}
```

**Step 3: Agent Responses**

**Agent 1 (Technical Specialist):**
```json
{
  "agent_id": "translation-agent-1",
  "agent_name": "TechTranslate Pro",
  "assessment": {
    "can_handle": true,
    "confidence_score": 0.98,
    "skill_matches": [
      {
        "id": "translation-v1",
        "name": "translation",
        "specialization": "technical",
        "language_pairs": ["en-es"]
      }
    ],
    "missing_requirements": []
  },
  "performance_metrics": {
    "current_queue_length": 2,
    "avg_completion_time_estimate": 45
  },
  "pricing": {
    "execution_cost": {
      "amount": "0.0002",
      "token": "USDC"
    }
  }
}
```

**Agent 2 (General Translation):**
```json
{
  "agent_id": "translation-agent-2",
  "agent_name": "QuickTranslate",
  "assessment": {
    "can_handle": true,
    "confidence_score": 0.73,
    "skill_matches": [
      {
        "id": "translation-v1",
        "name": "translation",
        "language_pairs": ["en-es"]
      }
    ],
    "missing_requirements": ["technical_specialization"]
  },
  "performance_metrics": {
    "current_queue_length": 0,
    "avg_completion_time_estimate": 30
  },
  "pricing": {
    "execution_cost": {
      "amount": "0.0001",
      "token": "USDC"
    }
  }
}
```

**Step 4: Orchestrator Ranking**

| Rank | Agent | Confidence | Queue | Price | Speed | **Score** |
|------|-------|-----------|-------|-------|-------|-----------|
| 🥇 1 | TechTranslate Pro | 0.98 | 2 | $0.0002 | 45s | **0.89** |
| 🥈 2 | QuickTranslate | 0.73 | 0 | $0.0001 | 30s | **0.82** |

**Step 5: Execute with Winner**
```json
POST http://translation-agent-1:3773/message/send
{
  "message": "Translate this technical manual...",
  "context_id": "user-session-123"
}
```

---

## Testing Strategy

### Unit Tests

**Test Files to Create:**

1. **`tests/unit/test_capability_calculator.py`**
   - Test skill matching logic
   - Test load factor calculation
   - Test confidence scoring
   - Test edge cases (no skills, empty queue, etc.)

2. **`tests/unit/test_negotiation_handlers.py`**
   - Test assessment request handling
   - Test response formatting
   - Test error handling
   - Test with various agent configurations

3. **`tests/unit/test_negotiation_endpoints.py`**
   - Test HTTP endpoint
   - Test request validation
   - Test response codes
   - Test authentication (if required)

### Integration Tests

**Test Scenarios:**

1. **Single Agent Assessment**
   - Orchestrator queries one agent
   - Agent returns valid assessment
   - Verify response structure

2. **Multiple Agent Selection**
   - Orchestrator queries 10 agents
   - Agents return varying assessments
   - Orchestrator ranks and selects winner
   - Verify correct agent selected

3. **Skill Matching**
   - Task requires specific skills
   - Agents with/without skills respond
   - Verify confidence scores differ appropriately

4. **Load Balancing**
   - Multiple identical agents
   - Different queue lengths
   - Verify less-busy agent ranked higher

5. **Missing Skills**
   - Task requires unavailable skill
   - Agent returns `can_handle: false`
   - Verify missing_requirements populated

### Performance Tests

**Benchmarks:**
- Assessment calculation time: < 50ms
- Endpoint response time: < 100ms
- Concurrent assessments: 100+ requests/second

---

## Documentation

### Developer Documentation

**Files to Create/Update:**

1. **`docs/negotiation/overview.md`**
   - System architecture
   - Use cases
   - Design decisions

2. **`docs/negotiation/api-reference.md`**
   - Endpoint specifications
   - Request/response schemas
   - Error codes

3. **`docs/negotiation/orchestrator-guide.md`**
   - How to query agents
   - Ranking algorithms
   - Best practices

4. **`docs/negotiation/agent-configuration.md`**
   - Configuration options
   - Skill setup for assessment
   - Customizing scoring weights

### Examples

**Create Example Files:**

1. **`examples/orchestrator_assessment.py`**
   - Complete orchestrator implementation
   - Query multiple agents
   - Rank and select winner
   - Execute task

2. **`examples/custom_scoring.py`**
   - Custom ranking algorithm
   - Multi-factor optimization
   - Domain-specific selection logic

3. **`examples/skills/translation/skill.yaml`**
   - Enhanced skill with assessment hints
   - Specialization definitions
   - Complexity indicators

---

## Migration Path

### Backward Compatibility

**Ensure:**
- Existing agents work without negotiation
- `/message/send` endpoint unchanged
- Optional negotiation configuration
- Default behavior: negotiation disabled

### Rollout Strategy

**Phase 1: Internal Testing**
- Deploy to staging environment
- Test with sample agents
- Validate performance

**Phase 2: Opt-in Beta**
- Enable for select agents
- Gather feedback
- Iterate on design

**Phase 3: General Availability**
- Enable by default for new agents
- Provide migration guide for existing agents
- Monitor adoption

---

## Success Metrics

### Technical Metrics
- Assessment latency: < 100ms p95
- Endpoint availability: > 99.9%
- Assessment accuracy: > 90% (agent confidence matches actual performance)

### Business Metrics
- Agent adoption rate: % of agents with negotiation enabled
- Orchestrator usage: # of assessment requests per day
- Selection accuracy: % of tasks successfully completed by selected agent

### User Experience Metrics
- Task routing time: Time from user request to agent selection
- Task success rate: % of tasks completed successfully
- User satisfaction: Feedback on agent selection quality

---

## Implementation Checklist

### Core Implementation
- [ ] Create `CapabilityCalculator` class
- [ ] Create `NegotiationHandlers` class
- [ ] Add negotiation endpoint
- [ ] Update `TaskManager` integration
- [ ] Add protocol types
- [ ] Update agent configuration schema

### Skill System
- [ ] Add assessment hints to skill YAML
- [ ] Update skill loader to parse assessment data
- [ ] Create example skills with assessment metadata

### Testing
- [ ] Unit tests for `CapabilityCalculator`
- [ ] Unit tests for `NegotiationHandlers`
- [ ] Integration tests for endpoint
- [ ] End-to-end orchestrator tests
- [ ] Performance benchmarks

### Documentation
- [ ] API reference documentation
- [ ] Orchestrator integration guide
- [ ] Agent configuration guide
- [ ] Example implementations
- [ ] Migration guide

### Deployment
- [ ] Staging environment testing
- [ ] Beta rollout plan
- [ ] Monitoring and alerting setup
- [ ] Performance dashboard
- [ ] Rollback procedure

---

## Timeline Estimate

### Phase 1 (MVP): 2-3 weeks
- **Week 1:** Core implementation (CapabilityCalculator, handlers, endpoint)
- **Week 2:** Integration, testing, documentation
- **Week 3:** Bug fixes, refinement, staging deployment

### Phase 2 (Enhanced): 3-4 weeks
- LLM-based analysis
- Historical performance tracking
- Dynamic pricing
- Extended testing

### Phase 3 (Multi-round): 4-6 weeks
- Negotiation state management
- Multi-round protocol
- Advanced strategies
- Comprehensive testing

---

## Open Questions

1. **Authentication:** Should assessment endpoint require authentication?
2. **Rate Limiting:** How many assessment requests per second per orchestrator?
3. **Caching:** Should assessment results be cached? For how long?
4. **Monitoring:** What metrics should be tracked in production?
5. **Pricing Strategy:** Should agents be able to refuse tasks based on price?
6. **Skill Registry:** Should there be a central skill registry for standardization?
7. **Assessment Expiry:** How long is an assessment valid before re-querying?

---

## References

- **NegotiationArena Paper:** https://arxiv.org/abs/2402.05863
- **A2A Protocol:** https://a2a-protocol.org/
- **Bindu Skills System:** `bindu/utils/skill_loader.py`
- **Existing Handler Pattern:** `bindu/server/handlers/`
- **Protocol Types:** `bindu/common/protocol/types.py`

---

## Contact & Support

For questions or clarifications about this implementation plan:
- Create an issue in the Bindu GitHub repository
- Tag: `enhancement`, `negotiation`, `orchestration`
- Assign to: Architecture team

---

**Document Version:** 1.0
**Last Updated:** December 14, 2025
**Status:** Draft - Ready for Review
