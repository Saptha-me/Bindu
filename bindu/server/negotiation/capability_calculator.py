# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Capability calculator for agent task assessment.

This module provides the core scoring logic for evaluating how well
an agent can handle a given task based on skill metadata, load,
performance characteristics, and pricing constraints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bindu.common.protocol.types import Skill


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable weights for scoring components.

    All weights must be non-negative and will be normalized to sum to 1.0.
    """

    skill_match: float = 0.55
    io_compatibility: float = 0.20
    performance: float = 0.15
    load: float = 0.05
    cost: float = 0.05

    def __post_init__(self) -> None:
        """Validate weights are non-negative."""
        for name in ("skill_match", "io_compatibility", "performance", "load", "cost"):
            if getattr(self, name) < 0:
                raise ValueError(f"Weight '{name}' must be non-negative")

    def normalized(self) -> dict[str, float]:
        """Return weights normalized to sum to 1.0."""
        total = (
            self.skill_match
            + self.io_compatibility
            + self.performance
            + self.load
            + self.cost
        )
        if total == 0:
            return {
                "skill_match": 0.2,
                "io_compatibility": 0.2,
                "performance": 0.2,
                "load": 0.2,
                "cost": 0.2,
            }
        return {
            "skill_match": self.skill_match / total,
            "io_compatibility": self.io_compatibility / total,
            "performance": self.performance / total,
            "load": self.load / total,
            "cost": self.cost / total,
        }


@dataclass
class SkillMatchResult:
    """Result of matching a skill against task requirements."""

    skill_id: str
    skill_name: str
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    """Complete assessment result from capability calculation."""

    accepted: bool
    score: float
    confidence: float
    rejection_reason: str | None = None
    skill_matches: list[SkillMatchResult] = field(default_factory=list)
    matched_tags: list[str] = field(default_factory=list)
    matched_capabilities: list[str] = field(default_factory=list)
    latency_estimate_ms: int | None = None
    queue_depth: int | None = None
    subscores: dict[str, float] = field(default_factory=dict)


class CapabilityCalculator:
    """Stateless, deterministic capability calculator for agent task assessment.

    This calculator evaluates how well an agent can handle a task based on:
    - Skill metadata (tags, capabilities, IO modes)
    - Current load (queue depth, when available)
    - Performance characteristics
    - Pricing constraints

    Thread-safe and side-effect free.
    """

    DEFAULT_LATENCY_MS = 5000
    MAX_KEYWORD_LENGTH = 100
    MAX_TASK_TEXT_LENGTH = 10000

    def __init__(
        self, skills: list[Skill], x402_extension: dict[str, Any] | None = None
    ):
        """Initialize calculator with agent skills and optional pricing."""
        self._skills = skills
        self._x402_extension = x402_extension

    def calculate(
        self,
        task_summary: str,
        task_details: str | None = None,
        input_mime_types: list[str] | None = None,
        output_mime_types: list[str] | None = None,
        max_latency_ms: int | None = None,
        max_cost_amount: str | None = None,
        required_tools: list[str] | None = None,
        forbidden_tools: list[str] | None = None,
        queue_depth: int | None = None,
        weights: ScoringWeights | None = None,
        min_score: float = 0.0,
    ) -> AssessmentResult:
        """Calculate capability score for a task."""
        weights = weights or ScoringWeights()
        normalized_weights = weights.normalized()

        # No skills = immediate rejection
        if not self._skills:
            return AssessmentResult(
                accepted=False,
                score=0.0,
                confidence=1.0,
                rejection_reason="no_skills_advertised",
            )

        # Extract keywords from task description
        task_keywords = self._extract_keywords(task_summary, task_details)

        # Check hard constraints first
        hard_fail = self._check_hard_constraints(
            input_mime_types=input_mime_types,
            output_mime_types=output_mime_types,
            required_tools=required_tools,
            forbidden_tools=forbidden_tools,
        )
        if hard_fail:
            return AssessmentResult(
                accepted=False,
                score=0.0,
                confidence=1.0,
                rejection_reason=hard_fail,
            )

        # Calculate component scores
        skill_match_score, skill_matches, matched_tags, matched_caps = (
            self._calculate_skill_match(task_keywords)
        )
        io_score = self._calculate_io_compatibility(input_mime_types, output_mime_types)
        perf_score, latency_estimate = self._calculate_performance_score(
            max_latency_ms, skill_matches
        )
        load_score = self._calculate_load_score(queue_depth)
        cost_score = self._calculate_cost_score(max_cost_amount)

        # Reject if latency is too high
        if max_latency_ms and latency_estimate and latency_estimate > max_latency_ms * 2:
            return AssessmentResult(
                accepted=False,
                score=0.0,
                confidence=0.8,
                rejection_reason="latency_exceeds_constraint",
                latency_estimate_ms=latency_estimate,
            )

        # Reject if cost too high
        if max_cost_amount and cost_score == 0.0:
            return AssessmentResult(
                accepted=False,
                score=0.0,
                confidence=0.9,
                rejection_reason="cost_exceeds_budget",
            )

        # Compute weighted final score
        subscores = {
            "skill_match": skill_match_score,
            "io_compatibility": io_score,
            "performance": perf_score,
            "load": load_score,
            "cost": cost_score,
        }
        final_score = sum(
            normalized_weights[key] * subscores[key] for key in subscores
        )

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(
            skill_matches=skill_matches,
            has_io_constraints=bool(input_mime_types or output_mime_types),
            has_latency_constraint=bool(max_latency_ms),
            has_queue_depth=queue_depth is not None,
        )

        # Accept if score meets threshold and there's a skill match
        accepted = final_score >= min_score and skill_match_score > 0

        return AssessmentResult(
            accepted=accepted,
            score=round(final_score, 4),
            confidence=round(confidence, 4),
            rejection_reason=None if accepted else "score_below_threshold",
            skill_matches=skill_matches,
            matched_tags=matched_tags,
            matched_capabilities=matched_caps,
            latency_estimate_ms=latency_estimate,
            queue_depth=queue_depth,
            subscores=subscores,
        )

    def _extract_keywords(self, summary: str, details: str | None = None) -> set[str]:
        """Extract normalized keywords from task text."""
        text = summary[: self.MAX_TASK_TEXT_LENGTH]
        if details:
            text = f"{text} {details[: self.MAX_TASK_TEXT_LENGTH]}"
        tokens = re.split(r"[^a-z0-9]+", text.lower())
        return {
            token
            for token in tokens
            if 2 <= len(token) <= self.MAX_KEYWORD_LENGTH
        }

    def _check_hard_constraints(
        self,
        input_mime_types: list[str] | None,
        output_mime_types: list[str] | None,
        required_tools: list[str] | None,
        forbidden_tools: list[str] | None,
    ) -> str | None:
        """Check hard constraints that cause immediate rejection."""
        # Check if input mime types are supported
        if input_mime_types:
            if not any(
                any(im in skill.get("input_modes", []) for im in input_mime_types)
                for skill in self._skills
            ):
                return "input_mime_unsupported"

        # Check if output mime types are supported
        if output_mime_types:
            if not any(
                any(om in skill.get("output_modes", []) for om in output_mime_types)
                for skill in self._skills
            ):
                return "output_mime_unsupported"

        # Check for forbidden tools
        if forbidden_tools:
            for skill in self._skills:
                allowed = set(skill.get("allowed_tools", []))
                if allowed and allowed.intersection(forbidden_tools):
                    return "forbidden_tool_present"

        # Check for required tools
        if required_tools:
            required_set = set(required_tools)
            if not any(
                required_set.issubset(set(skill.get("allowed_tools", [])))
                for skill in self._skills
                if skill.get("allowed_tools")
            ):
                skills_with_tools = [s for s in self._skills if s.get("allowed_tools")]
                if skills_with_tools:
                    return "required_tool_missing"

        return None

    def _calculate_skill_match(
        self, task_keywords: set[str]
    ) -> tuple[float, list[SkillMatchResult], list[str], list[str]]:
        """Calculate skill match score using keyword overlap."""
        if not task_keywords:
            return 0.5, [], [], []

        skill_matches: list[SkillMatchResult] = []
        all_matched_tags: set[str] = set()
        all_matched_caps: set[str] = set()

        for skill in self._skills:
            skill_keywords: set[str] = set()

            # Extract keywords from tags
            tags = skill.get("tags", [])
            for tag in tags:
                skill_keywords.update(
                    t.lower()
                    for t in re.split(r"[^a-z0-9]+", tag.lower())
                    if len(t) >= 2
                )

            # Extract keywords from skill name
            skill_keywords.update(
                t.lower()
                for t in re.split(r"[^a-z0-9]+", skill.get("name", "").lower())
                if len(t) >= 2
            )

            # Extract keywords from skill ID
            skill_keywords.update(
                t.lower()
                for t in re.split(r"[^a-z0-9]+", skill.get("id", "").lower())
                if len(t) >= 2
            )

            # Extract keywords from capability names
            caps_detail = skill.get("capabilities_detail", {})
            if isinstance(caps_detail, dict):
                for cap_key in caps_detail.keys():
                    skill_keywords.update(
                        t.lower()
                        for t in re.split(r"[^a-z0-9]+", cap_key.lower())
                        if len(t) >= 2
                    )

            # Calculate Jaccard similarity
            intersection = task_keywords.intersection(skill_keywords)
            union = task_keywords.union(skill_keywords)
            match_score = len(intersection) / len(union) if union else 0.0

            # Track reasons for match
            reasons: list[str] = []
            matched_tags_for_skill = [
                tag
                for tag in tags
                if any(t.lower() in intersection for t in tag.lower().split())
            ]
            if matched_tags_for_skill:
                reasons.append(f"tags matched: {', '.join(matched_tags_for_skill)}")
                all_matched_tags.update(matched_tags_for_skill)

            matched_caps_for_skill = [
                cap
                for cap in caps_detail.keys()
                if any(t in intersection for t in cap.lower().split("_"))
            ]
            if matched_caps_for_skill:
                reasons.append(f"capabilities: {', '.join(matched_caps_for_skill)}")
                all_matched_caps.update(matched_caps_for_skill)

            if match_score > 0:
                skill_matches.append(
                    SkillMatchResult(
                        skill_id=skill.get("id", "unknown"),
                        skill_name=skill.get("name", "unknown"),
                        score=round(match_score, 4),
                        reasons=reasons,
                    )
                )

        # Sort by score descending
        skill_matches.sort(key=lambda x: x.score, reverse=True)
        best_score = skill_matches[0].score if skill_matches else 0.0

        return best_score, skill_matches, list(all_matched_tags), list(all_matched_caps)

    def _calculate_io_compatibility(
        self,
        input_mime_types: list[str] | None,
        output_mime_types: list[str] | None,
    ) -> float:
        """Calculate IO compatibility score."""
        if not input_mime_types and not output_mime_types:
            return 0.5

        input_match = False
        output_match = False

        if input_mime_types:
            input_match = any(
                any(im in skill.get("input_modes", []) for im in input_mime_types)
                for skill in self._skills
            )

        if output_mime_types:
            output_match = any(
                any(om in skill.get("output_modes", []) for om in output_mime_types)
                for skill in self._skills
            )

        if input_mime_types and output_mime_types:
            if input_match and output_match:
                return 1.0
            elif input_match or output_match:
                return 0.5
            return 0.0
        elif input_mime_types:
            return 1.0 if input_match else 0.0
        else:
            return 1.0 if output_match else 0.0

    def _calculate_performance_score(
        self,
        max_latency_ms: int | None,
        skill_matches: list[SkillMatchResult],
    ) -> tuple[float, int | None]:
        """Calculate performance score based on latency estimation."""
        latency_estimate: int | None = None

        # Find the best (lowest) latency from matched skills
        for match in skill_matches:
            skill = next(
                (s for s in self._skills if s.get("id") == match.skill_id), None
            )
            if skill and skill.get("performance"):
                perf = skill["performance"]
                if "avg_processing_time_ms" in perf:
                    est = int(perf["avg_processing_time_ms"])
                    if latency_estimate is None or est < latency_estimate:
                        latency_estimate = est

        if latency_estimate is None:
            latency_estimate = self.DEFAULT_LATENCY_MS

        # Score based on constraint
        if max_latency_ms is None:
            # No constraint: gentle decay function
            score = 1.0 / (1.0 + latency_estimate / 10000.0)
        else:
            if latency_estimate <= max_latency_ms:
                score = 1.0
            elif latency_estimate <= max_latency_ms * 2:
                score = 1.0 - (latency_estimate - max_latency_ms) / max_latency_ms
            else:
                score = 0.0

        return round(score, 4), latency_estimate

    def _calculate_load_score(self, queue_depth: int | None) -> float:
        """Calculate load score based on queue depth."""
        if queue_depth is None:
            return 0.5
        return round(1.0 / (1.0 + queue_depth), 4)

    def _calculate_cost_score(self, max_cost_amount: str | None) -> float:
        """Calculate cost score based on pricing constraint."""
        if not self._x402_extension:
            return 1.0

        if not max_cost_amount:
            return 0.5

        try:
            agent_cost = self._parse_cost_amount(self._x402_extension.get("amount", "0"))
            max_cost = self._parse_cost_amount(max_cost_amount)

            if max_cost <= 0:
                return 0.5

            if agent_cost <= max_cost:
                # Linear discount: max cost gets 1.0, zero cost gets 0.5
                return round(1.0 - (agent_cost / max_cost) * 0.5, 4)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.5

    def _parse_cost_amount(self, amount: str | float | int) -> float:
        """Parse cost amount string to float."""
        if isinstance(amount, (int, float)):
            return float(amount)
        cleaned = re.sub(r"[^\d.]", "", str(amount))
        return float(cleaned) if cleaned else 0.0

    def _calculate_confidence(
        self,
        skill_matches: list[SkillMatchResult],
        has_io_constraints: bool,
        has_latency_constraint: bool,
        has_queue_depth: bool,
    ) -> float:
        """Calculate confidence level based on data quality."""
        confidence = 0.5

        if skill_matches and skill_matches[0].score > 0.3:
            confidence += 0.2
        elif skill_matches:
            confidence += 0.1

        if has_io_constraints:
            confidence += 0.1

        if has_latency_constraint:
            confidence += 0.1

        if has_queue_depth:
            confidence += 0.1

        return min(confidence, 1.0)
