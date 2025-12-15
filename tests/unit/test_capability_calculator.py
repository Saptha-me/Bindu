# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for negotiation capability calculator."""

import pytest

from bindu.server.negotiation.capability_calculator import (
    CapabilityCalculator,
    ScoringWeights,
)


def test_scoring_weights_defaults():
    """Test default scoring weights."""
    weights = ScoringWeights()
    assert weights.skill_match == 0.55
    assert weights.io_compatibility == 0.20
    assert weights.performance == 0.15
    assert weights.load == 0.05
    assert weights.cost == 0.05


def test_scoring_weights_normalized():
    """Test weight normalization."""
    weights = ScoringWeights(skill_match=2.0, io_compatibility=1.0, performance=1.0)
    normalized = weights.normalized
    # Total is 4.05, so normalized should sum to 1.0
    total = sum(normalized.values())
    assert abs(total - 1.0) < 0.001


def test_scoring_weights_negative_raises():
    """Test that negative weights raise error."""
    with pytest.raises(ValueError, match="must be non-negative"):
        ScoringWeights(skill_match=-0.5)


def test_no_skills_rejection():
    """Test immediate rejection when agent has no skills."""
    calculator = CapabilityCalculator(skills=[], x402_extension=None)
    result = calculator.calculate(task_summary="summarize this document")

    assert result.accepted is False
    assert result.score == 0.0
    assert result.confidence == 1.0
    assert result.rejection_reason == "no_skills_advertised"


def test_basic_skill_match():
    """Test basic skill matching with keywords."""
    skills = [
        {
            "id": "summarizer",
            "name": "Document Summarizer",
            "tags": ["summarization", "text-processing"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)
    result = calculator.calculate(task_summary="summarize this document")

    assert result.accepted is True
    assert result.score > 0
    assert len(result.skill_matches) > 0
    assert result.skill_matches[0].skill_id == "summarizer"


def test_input_mime_type_constraint():
    """Test hard rejection when input mime type is unsupported."""
    skills = [
        {
            "id": "text-processor",
            "name": "Text Processor",
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)
    result = calculator.calculate(
        task_summary="process this", input_mime_types=["application/pdf"]
    )

    assert result.accepted is False
    assert result.rejection_reason == "input_mime_unsupported"


def test_output_mime_type_constraint():
    """Test hard rejection when output mime type is unsupported."""
    skills = [
        {
            "id": "text-processor",
            "name": "Text Processor",
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)
    result = calculator.calculate(
        task_summary="process this", output_mime_types=["application/pdf"]
    )

    assert result.accepted is False
    assert result.rejection_reason == "output_mime_unsupported"


def test_required_tools():
    """Test required tools constraint."""
    skills = [
        {
            "id": "web-scraper",
            "name": "Web Scraper",
            "tags": ["scraping", "web", "scrape", "website"],
            "allowed_tools": ["web_browser"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # Should accept when required tool is available and keywords match
    result = calculator.calculate(
        task_summary="scrape website", required_tools=["web_browser"]
    )
    assert result.accepted is True
    assert result.score > 0

    # Should reject when required tool is not available (hard constraint)
    result = calculator.calculate(
        task_summary="scrape website with browser", required_tools=["database"]
    )
    assert result.accepted is False
    assert result.rejection_reason == "required_tool_missing"


def test_forbidden_tools():
    """Test forbidden tools constraint."""
    skills = [
        {
            "id": "data-processor",
            "name": "Data Processor",
            "allowed_tools": ["web_browser", "file_system"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)
    result = calculator.calculate(
        task_summary="process data", forbidden_tools=["web_browser"]
    )

    assert result.accepted is False
    assert result.rejection_reason == "forbidden_tool_present"


def test_latency_constraint():
    """Test latency performance constraint."""
    skills = [
        {
            "id": "slow-processor",
            "name": "Slow Processor",
            "tags": ["processing", "data"],
            "performance": {"avg_processing_time_ms": 10000},
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # Should reject when latency exceeds constraint by 2x
    result = calculator.calculate(task_summary="process data", max_latency_ms=2000)
    assert result.accepted is False
    assert result.rejection_reason == "latency_exceeds_constraint"
    # Should use skill's actual latency
    assert result.latency_estimate_ms == 10000


def test_cost_constraint():
    """Test cost constraint with x402 extension."""
    skills = [
        {
            "id": "expensive-service",
            "name": "Expensive Service",
            "tags": ["processing"],
        }
    ]
    x402_ext = {"amount": "100.00", "currency": "USD"}
    calculator = CapabilityCalculator(skills=skills, x402_extension=x402_ext)

    # Should reject when cost exceeds budget
    result = calculator.calculate(task_summary="process data", max_cost_amount="50.00")
    assert result.accepted is False
    assert result.rejection_reason == "cost_exceeds_budget"


def test_queue_depth_scoring():
    """Test queue depth affects load score."""
    skills = [
        {
            "id": "processor",
            "name": "Processor",
            "tags": ["processing"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # Low queue depth should give better score
    result_low = calculator.calculate(task_summary="process data", queue_depth=0)
    result_high = calculator.calculate(task_summary="process data", queue_depth=10)

    assert result_low.subscores["load"] > result_high.subscores["load"]


def test_custom_weights():
    """Test custom scoring weights."""
    skills = [
        {
            "id": "processor",
            "name": "Processor",
            "tags": ["processing"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # Heavy skill match weight
    weights = ScoringWeights(
        skill_match=0.9,
        io_compatibility=0.025,
        performance=0.025,
        load=0.025,
        cost=0.025,
    )
    result = calculator.calculate(task_summary="processor task", weights=weights)

    # Skill match subscore should dominate
    assert result.subscores["skill_match"] > 0
    # Final score should be heavily influenced by skill match
    assert result.accepted is True


def test_min_score_threshold():
    """Test minimum score threshold."""
    skills = [
        {
            "id": "weak-match",
            "name": "Weak Match",
            "tags": ["unrelated"],
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # With high threshold, should reject weak matches
    result = calculator.calculate(
        task_summary="highly specific unusual task", min_score=0.8
    )

    if result.score < 0.8:
        assert result.accepted is False
        assert result.rejection_reason == "score_below_threshold"


def test_confidence_calculation():
    """Test confidence calculation based on data quality."""
    skills = [
        {
            "id": "processor",
            "name": "Processor",
            "tags": ["processing"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
            "performance": {"avg_processing_time_ms": 1000},
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)

    # More constraints = higher confidence
    result = calculator.calculate(
        task_summary="process text",
        input_mime_types=["text/plain"],
        output_mime_types=["text/plain"],
        max_latency_ms=5000,
        queue_depth=2,
    )

    # Should have high confidence with many constraints
    assert result.confidence > 0.7


def test_matched_tags_and_capabilities():
    """Test that matched tags and capabilities are tracked."""
    skills = [
        {
            "id": "ml-model",
            "name": "ML Model",
            "tags": ["machine-learning", "classification"],
            "capabilities_detail": {
                "image_classification": {"enabled": True},
                "text_analysis": {"enabled": True},
            },
        }
    ]
    calculator = CapabilityCalculator(skills=skills, x402_extension=None)
    result = calculator.calculate(task_summary="classify images using machine learning")

    # Check that skill match occurred and reasons were populated
    assert len(result.skill_matches) > 0
    assert result.skill_matches[0].score > 0
    # Reasons should show what matched
    if result.skill_matches[0].reasons:
        # If there are reasons, at least one should mention tags or capabilities
        assert any(
            "tags" in r or "capabilities" in r for r in result.skill_matches[0].reasons
        )
