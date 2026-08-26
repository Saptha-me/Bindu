---
name: issue-analyzer
description: Analyzes GitHub issue descriptions to determine classification (Bug, Feature, Question) and assigns a priority level.
---

# Issue Analyzer Skill

## Instructions
When you receive a raw string representing a GitHub issue, follow these exact steps:

1. **Classification**: Determine if the issue is a `Bug` (unexpected behavior), `Feature` (new request), or `Question` (usage help).
2. **Prioritization**:
   - Assign `High` priority to critical bugs or security flaws.
   - Assign `Medium` priority to standard features and non-critical bugs.
   - Assign `Low` priority to general questions or minor typos.
3. **Response Generation**: Draft a polite, automated reply acknowledging the user's submission, stating the assigned classification and priority.

## Output Format
Always return the result matching the `IssueTriage` structured data model.
