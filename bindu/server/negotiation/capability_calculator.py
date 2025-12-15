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
from functools import cached_property
from typing import TYPE_CHECKING, Any

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.common.protocol.types import Skill

# Pre-compiled regex patterns for performance
_TOKEN_SPLIT_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable weights for scoring components.

    All weights must be non-negative and will be normalized to sum to 1.0.
    """

    skill_match: float = app_settings.negotiation.skill_match_weight
    io_compatibility: float = app_settings.negotiation.io_compatibility_weight
    performance: float = app_settings.negotiation.performance_weight
    load: float = app_settings.negotiation.load_weight
    cost: float = app_settings.negotiation.cost_weight

    def __post_init__(self) -> None:
        """Validate weights are non-negative."""
        for name in ("skill_match", "io_compatibility", "performance", "load", "cost"):
            if getattr(self, name) < 0:
                raise ValueError(f"Weight '{name}' must be non-negative")

    @cached_property
    def normalized(self) -> dict[str, float]:
        """Return weights normalized to sum to 1.0 (cached)."""
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

    DEFAULT_LATENCY_MS = app_settings.negotiation.default_latency_ms
    MAX_KEYWORD_LENGTH = app_settings.negotiation.max_keyword_length
    MAX_TASK_TEXT_LENGTH = app_settings.negotiation.max_task_text_length

    def __init__(
        self,
        skills: list[Skill],
        x402_extension: dict[str, Any] | None = None,
        embedding_api_key: str | None = None,
    ):
        """Initialize calculator with agent skills and optional pricing.

        Args:
            skills: List of skill definitions
            x402_extension: Optional x402 payment extension config
            embedding_api_key: Optional OpenRouter API key for embeddings
        """
        self._skills = skills
        self._x402_extension = x402_extension
        self._embedding_api_key = embedding_api_key
        self._embedder = None
        self._skill_embeddings = None
        self._use_embeddings = app_settings.negotiation.use_embeddings

        # Pre-compute skill metadata for faster matching
        self._skill_metadata = self._precompute_skill_metadata()

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
        normalized_weights = weights.normalized

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
            self._calculate_skill_match(
                task_keywords=task_keywords,
                task_summary=task_summary,
                task_details=task_details,
            )
        )
        io_score = self._calculate_io_compatibility(input_mime_types, output_mime_types)
        load_score = self._calculate_load_score(queue_depth)
        cost_score = self._calculate_cost_score(max_cost_amount)

        # Reject if cost too high
        if max_cost_amount and cost_score == 0.0:
            return AssessmentResult(
                accepted=False,
                score=0.0,
                confidence=0.9,
                rejection_reason="cost_exceeds_budget",
            )

        # Calculate latency estimate and check constraint
        latency_estimate_ms = None
        if skill_matches:
            latencies = []
            for skill in self._skills:
                perf = skill.get("performance", {})
                if isinstance(perf, dict) and "avg_processing_time_ms" in perf:
                    latencies.append(perf["avg_processing_time_ms"])
            if latencies:
                latency_estimate_ms = max(latencies)
            else:
                latency_estimate_ms = self.DEFAULT_LATENCY_MS

        # Reject if latency exceeds constraint by 2x
        if max_latency_ms and latency_estimate_ms:
            if latency_estimate_ms > max_latency_ms * 2:
                return AssessmentResult(
                    accepted=False,
                    score=0.0,
                    confidence=0.9,
                    rejection_reason="latency_exceeds_constraint",
                    latency_estimate_ms=latency_estimate_ms,
                )

        # Compute weighted final score
        subscores = {
            "skill_match": skill_match_score,
            "io_compatibility": io_score,
            "load": load_score,
            "cost": cost_score,
        }
        final_score = sum(normalized_weights[key] * subscores[key] for key in subscores)

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
            latency_estimate_ms=latency_estimate_ms,
            queue_depth=queue_depth,
            subscores=subscores,
        )

    def _extract_keywords(self, summary: str, details: str | None = None) -> set[str]:
        """Extract normalized keywords from task text."""
        text = summary[: self.MAX_TASK_TEXT_LENGTH]
        if details:
            text = f"{text} {details[: self.MAX_TASK_TEXT_LENGTH]}"
        tokens = _TOKEN_SPLIT_PATTERN.split(text.lower())
        return {token for token in tokens if 2 <= len(token) <= self.MAX_KEYWORD_LENGTH}

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

        # Check required tools
        if required_tools:
            available_tools = set()
            for skill in self._skills:
                available_tools.update(skill.get("allowed_tools", []))
            if not all(tool in available_tools for tool in required_tools):
                return "required_tool_missing"

        # Check forbidden tools
        if forbidden_tools:
            for skill in self._skills:
                skill_tools = set(skill.get("allowed_tools", []))
                if any(tool in skill_tools for tool in forbidden_tools):
                    return "forbidden_tool_present"

        return None

    def _precompute_skill_metadata(self) -> list[dict[str, Any]]:
        """Pre-compute skill metadata at initialization for faster matching.

        Returns list of dicts with:
        - skill_id, skill_name, tags, caps_detail, assessment
        - keywords: pre-extracted keyword set
        - anti_patterns: list of anti-patterns
        - specializations: list of specialization configs
        """
        metadata = []
        for skill in self._skills:
            skill_id = skill.get("id", "unknown")
            skill_name = skill.get("name", "unknown")
            tags = skill.get("tags", [])
            caps_detail = skill.get("capabilities_detail", {})
            assessment = skill.get("assessment", {})

            # Pre-extract keywords
            keywords: set[str] = set()

            # Assessment keywords (highest priority)
            if isinstance(assessment, dict) and "keywords" in assessment:
                keywords.update(k.lower() for k in assessment.get("keywords", []))

            # Tags
            for tag in tags:
                keywords.update(
                    t
                    for t in _TOKEN_SPLIT_PATTERN.split(tag.lower())
                    if 2 <= len(t) <= self.MAX_KEYWORD_LENGTH
                )

            # Skill name
            keywords.update(
                t
                for t in _TOKEN_SPLIT_PATTERN.split(skill_name.lower())
                if 2 <= len(t) <= self.MAX_KEYWORD_LENGTH
            )

            # Capability names
            if isinstance(caps_detail, dict):
                for cap_key in caps_detail.keys():
                    keywords.update(
                        t
                        for t in _TOKEN_SPLIT_PATTERN.split(cap_key.lower())
                        if 2 <= len(t) <= self.MAX_KEYWORD_LENGTH
                    )

            # Extract assessment fields
            anti_patterns = []
            specializations = []
            if isinstance(assessment, dict):
                anti_patterns = assessment.get("anti_patterns", [])
                specializations = assessment.get("specializations", [])

            metadata.append(
                {
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "tags": tags,
                    "caps_detail": caps_detail,
                    "assessment": assessment,
                    "keywords": keywords,
                    "anti_patterns": anti_patterns,
                    "specializations": specializations,
                }
            )

        return metadata

    def _ensure_embeddings(self) -> None:
        """Lazy load embedder and compute skill embeddings on first use."""
        if self._skill_embeddings is not None:
            return

        if not self._use_embeddings:
            return

        try:
            from bindu.server.negotiation.embedder import SkillEmbedder

            self._embedder = SkillEmbedder(api_key=self._embedding_api_key)
            self._skill_embeddings = self._embedder.compute_skill_embeddings(
                self._skills
            )
        except ImportError:
            logger = get_logger("bindu.server.negotiation.capability_calculator")
            logger.warning(
                "Required dependencies not available. Falling back to keyword matching."
            )
            self._use_embeddings = False
        except Exception as e:
            logger = get_logger("bindu.server.negotiation.capability_calculator")
            logger.warning(
                f"Failed to initialize embeddings: {e}. Using keyword matching."
            )
            self._use_embeddings = False

    def _calculate_skill_match(
        self,
        task_keywords: set[str],
        task_summary: str = "",
        task_details: str | None = None,
    ) -> tuple[float, list[SkillMatchResult], list[str], list[str]]:
        """Calculate skill match score using hybrid approach.

        Uses embeddings for semantic matching (if enabled) combined with
        keyword matching and assessment field boosting.
        """
        if not task_keywords and not task_summary:
            return 0.5, [], [], []

        skill_matches: list[SkillMatchResult] = []
        all_matched_tags: set[str] = set()
        all_matched_caps: set[str] = set()

        # Try to use embeddings if enabled
        task_embedding = None
        if self._use_embeddings and task_summary:
            self._ensure_embeddings()
            if self._embedder and self._skill_embeddings:
                try:
                    task_text = task_details or ""
                    task_embedding = self._embedder.embed_task_cached(
                        task_summary, task_text
                    )
                except Exception as e:
                    logger = get_logger(
                        "bindu.server.negotiation.capability_calculator"
                    )
                    logger.warning(f"Failed to embed task: {e}")

        for skill_meta in self._skill_metadata:
            skill_id = skill_meta["skill_id"]
            skill_name = skill_meta["skill_name"]
            tags = skill_meta["tags"]
            caps_detail = skill_meta["caps_detail"]
            assessment = skill_meta["assessment"]
            anti_patterns = skill_meta["anti_patterns"]
            specializations = skill_meta["specializations"]
            skill_keywords = skill_meta["keywords"]  # Pre-computed!

            # Check anti-patterns first (early rejection)
            if anti_patterns and task_summary:
                task_lower = task_summary.lower()
                if task_details:
                    task_lower += " " + task_details.lower()
                if any(pattern.lower() in task_lower for pattern in anti_patterns):
                    continue

            # Calculate embedding similarity if available
            embedding_score = 0.0
            if (
                task_embedding is not None
                and self._skill_embeddings
                and skill_id in self._skill_embeddings
            ):
                from bindu.server.negotiation.embedder import cosine_similarity

                skill_emb = self._skill_embeddings[skill_id]["embedding"]
                embedding_score = cosine_similarity(task_embedding, skill_emb)

            # Calculate Jaccard similarity
            intersection = task_keywords.intersection(skill_keywords)
            union = task_keywords.union(skill_keywords)
            keyword_score = len(intersection) / len(union) if union else 0.0

            # Hybrid score: combine embedding and keyword scores
            if task_embedding is not None and embedding_score > 0:
                emb_weight = app_settings.negotiation.embedding_weight
                kw_weight = app_settings.negotiation.keyword_weight
                base_score = (emb_weight * embedding_score) + (
                    kw_weight * keyword_score
                )
            else:
                base_score = keyword_score

            # Apply specialization boosts from assessment
            if isinstance(assessment, dict) and "specializations" in assessment:
                specializations = assessment.get("specializations", [])
                for spec in specializations:
                    if isinstance(spec, dict):
                        domain = spec.get("domain", "")
                        boost = spec.get("confidence_boost", 0.0)
                        if (
                            domain
                            and task_summary
                            and domain.lower() in task_summary.lower()
                        ):
                            base_score = min(1.0, base_score + boost)

            match_score = base_score

            # Track reasons for match
            reasons: list[str] = []
            if task_embedding is not None and embedding_score > 0:
                reasons.append(f"semantic similarity: {embedding_score:.2f}")

            matched_tags_for_skill = [
                tag
                for tag in tags
                if any(t.lower() in intersection for t in tag.lower().split())
            ]
            if matched_tags_for_skill:
                reasons.append(f"tags: {', '.join(matched_tags_for_skill)}")
                all_matched_tags.update(matched_tags_for_skill)

            matched_caps_for_skill = [
                cap
                for cap in caps_detail.keys()
                if isinstance(caps_detail, dict)
                if any(t in intersection for t in cap.lower().split("_"))
            ]
            if matched_caps_for_skill:
                reasons.append(f"capabilities: {', '.join(matched_caps_for_skill)}")
                all_matched_caps.update(matched_caps_for_skill)

            if match_score > 0:
                skill_matches.append(
                    SkillMatchResult(
                        skill_id=skill_id,
                        skill_name=skill_name,
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
            return 1.0

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
            agent_cost = self._parse_cost_amount(
                self._x402_extension.get("amount", "0")
            )
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
