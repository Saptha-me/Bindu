"""Unit tests for DSPy interaction extractor and strategies."""

from uuid import uuid4

import pytest

from bindu.dspy.extractor import InteractionExtractor, clean_messages
from bindu.dspy.strategies import (
    BaseExtractionStrategy,
    LastTurnStrategy,
    FullHistoryStrategy,
    LastNTurnsStrategy,
    FirstNTurnsStrategy,
    ContextWindowStrategy,
    SlidingWindowStrategy,
    SummaryContextStrategy,
    KeyTurnsStrategy,
    STRATEGIES,
    get_strategy,
    parse_turns,
    jaccard_similarity,
    overlap_similarity,
    weighted_similarity,
    compute_similarity,
)


class TestStrategyRegistry:
    """Test strategy registry and factory function."""

    def test_all_strategies_registered(self):
        """Test that all expected strategies are registered."""
        assert "last_turn" in STRATEGIES
        assert "full_history" in STRATEGIES
        assert "last_n_turns" in STRATEGIES
        assert "first_n_turns" in STRATEGIES
        assert "context_window" in STRATEGIES
        assert "sliding_window" in STRATEGIES
        assert "summary_context" in STRATEGIES
        assert "key_turns" in STRATEGIES

    def test_get_strategy_last_turn(self):
        """Test factory creates LastTurnStrategy."""
        strategy = get_strategy("last_turn")
        assert isinstance(strategy, LastTurnStrategy)
        assert strategy.name == "last_turn"

    def test_get_strategy_context_window_with_params(self):
        """Test factory passes params to ContextWindowStrategy."""
        strategy = get_strategy("context_window", n_turns=5, system_prompt="Be helpful")
        assert isinstance(strategy, ContextWindowStrategy)
        assert strategy.n_turns == 5
        assert strategy.system_prompt == "Be helpful"

    def test_get_strategy_unknown_raises(self):
        """Test factory raises for unknown strategy."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent")


class TestInteractionExtractorInit:
    """Test InteractionExtractor initialization."""

    def test_default_strategy(self):
        """Test default strategy is LastTurnStrategy."""
        extractor = InteractionExtractor()
        assert isinstance(extractor.strategy, LastTurnStrategy)
        assert extractor.strategy.name == "last_turn"

    def test_custom_strategy(self):
        """Test custom strategy initialization."""
        strategy = LastNTurnsStrategy(n_turns=5)
        extractor = InteractionExtractor(strategy)
        assert extractor.strategy is strategy
        assert extractor.strategy.name == "last_n_turns"

    def test_context_window_strategy_with_config(self):
        """Test ContextWindowStrategy with full config."""
        strategy = ContextWindowStrategy(n_turns=3, system_prompt="You are helpful.")
        extractor = InteractionExtractor(strategy)
        assert extractor.strategy.n_turns == 3
        assert extractor.strategy.system_prompt == "You are helpful."


class TestLastTurnStrategy:
    """Test LastTurnStrategy extraction."""

    def test_simple_conversation(self):
        """Test extraction from simple user-assistant conversation."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"

    def test_multi_turn_extracts_last(self):
        """Test that only last turn is extracted."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Second question"
        assert result.agent_output == "Second answer"

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()

        result = extractor.extract(task_id, [])

        assert result is None

    def test_no_assistant_returns_none(self):
        """Test history without assistant message returns None."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [{"role": "user", "content": "Hello"}]

        result = extractor.extract(task_id, history)

        assert result is None


class TestLastNTurnsStrategy:
    """Test LastNTurnsStrategy extraction."""

    def test_single_turn_with_n_equals_1(self):
        """Test extracting single turn when n=1."""
        strategy = LastNTurnsStrategy(n_turns=1)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"

    def test_two_turns_with_n_equals_2(self):
        """Test extracting 2 turns with context formatting."""
        strategy = LastNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Context should include first turn, user_input includes context + final user message
        assert "User: First question" in result.user_input
        assert "Assistant: First answer" in result.user_input
        assert "User: Second question" in result.user_input
        assert result.agent_output == "Second answer"

    def test_three_turns_with_n_equals_3(self):
        """Test extracting 3 turns."""
        strategy = LastNTurnsStrategy(n_turns=3)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert "User: Q1" in result.user_input
        assert "Assistant: A1" in result.user_input
        assert "User: Q2" in result.user_input
        assert "Assistant: A2" in result.user_input
        assert "User: Q3" in result.user_input
        assert result.agent_output == "A3"

    def test_n_greater_than_available_turns(self):
        """Test when n is greater than available turns."""
        strategy = LastNTurnsStrategy(n_turns=5)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Only question"},
            {"role": "assistant", "content": "Only answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Only question"
        assert result.agent_output == "Only answer"

    def test_extracts_last_n_not_first_n(self):
        """Test that last N turns are extracted, not first N."""
        strategy = LastNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Answer1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Answer2"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Answer3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Should have Second and Third, not First
        assert "First" not in result.user_input
        assert "User: Second" in result.user_input
        assert "User: Third" in result.user_input
        assert result.agent_output == "Answer3"

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = LastNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()

        result = extractor.extract(task_id, [])

        assert result is None

    def test_no_complete_turns_returns_none(self):
        """Test history without complete turns returns None."""
        strategy = LastNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [{"role": "user", "content": "Unanswered question"}]

        result = extractor.extract(task_id, history)

        assert result is None

    def test_n_turns_minimum_enforced(self):
        """Test n_turns is at least 1."""
        strategy = LastNTurnsStrategy(n_turns=0)
        assert strategy.n_turns == 1

        strategy = LastNTurnsStrategy(n_turns=-5)
        assert strategy.n_turns == 1


class TestFirstNTurnsStrategy:
    """Test FirstNTurnsStrategy extraction."""

    def test_single_turn_with_n_equals_1(self):
        """Test extracting single turn when n=1."""
        strategy = FirstNTurnsStrategy(n_turns=1)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"

    def test_two_turns_with_n_equals_2(self):
        """Test extracting first 2 turns."""
        strategy = FirstNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # First user message is the input
        assert result.user_input == "First question"
        # Output includes both assistant responses with user context
        assert "Assistant: First answer" in result.agent_output
        assert "User: Second question" in result.agent_output
        assert "Assistant: Second answer" in result.agent_output

    def test_three_turns_with_n_equals_3(self):
        """Test extracting first 3 turns."""
        strategy = FirstNTurnsStrategy(n_turns=3)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Q1"
        assert "Assistant: A1" in result.agent_output
        assert "User: Q2" in result.agent_output
        assert "Assistant: A2" in result.agent_output
        assert "User: Q3" in result.agent_output
        assert "Assistant: A3" in result.agent_output

    def test_n_greater_than_available_turns(self):
        """Test when n is greater than available turns."""
        strategy = FirstNTurnsStrategy(n_turns=5)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Only question"},
            {"role": "assistant", "content": "Only answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Only question"
        assert result.agent_output == "Only answer"

    def test_extracts_first_n_not_last_n(self):
        """Test that first N turns are extracted, not last N."""
        strategy = FirstNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Answer1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Second answer"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Answer3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Should have First and Second, not Third
        assert result.user_input == "First"
        assert "Answer1" in result.agent_output
        assert "Second" in result.agent_output
        assert "Second answer" in result.agent_output
        assert "Third" not in result.agent_output
        assert "Answer3" not in result.agent_output

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = FirstNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()

        result = extractor.extract(task_id, [])

        assert result is None


class TestContextWindowStrategy:
    """Test ContextWindowStrategy extraction."""

    def test_single_turn_with_n_equals_1(self):
        """Test extracting single turn when n=1."""
        strategy = ContextWindowStrategy(n_turns=1)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"

    def test_two_turns_concatenates_user_messages(self):
        """Test that 2 turns concatenates user messages."""
        strategy = ContextWindowStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow up question"},
            {"role": "assistant", "content": "Final answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Both user messages should be in input
        assert "First question" in result.user_input
        assert "Follow up question" in result.user_input
        # Only the last agent response is output
        assert result.agent_output == "Final answer"
        assert "First answer" not in result.agent_output

    def test_three_turns_with_simple_separator(self):
        """Test 3 turns uses simple separator (no turn numbers)."""
        strategy = ContextWindowStrategy(n_turns=3)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # All 3 user messages concatenated
        assert "Q1" in result.user_input
        assert "Q2" in result.user_input
        assert "Q3" in result.user_input
        # Simple separator for <= 3 turns (no [Turn X] prefix)
        assert "[Turn" not in result.user_input
        # Only last agent response
        assert result.agent_output == "A3"

    def test_four_turns_with_turn_numbers(self):
        """Test 4+ turns adds turn numbers for clarity."""
        strategy = ContextWindowStrategy(n_turns=4)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Turn numbers for > 3 turns
        assert "[Turn 1]" in result.user_input
        assert "[Turn 2]" in result.user_input
        assert "[Turn 3]" in result.user_input
        assert "[Turn 4]" in result.user_input
        assert result.agent_output == "A4"

    def test_n_greater_than_available_turns(self):
        """Test when n is greater than available turns."""
        strategy = ContextWindowStrategy(n_turns=5)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Only question"},
            {"role": "assistant", "content": "Only answer"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Only question"
        assert result.agent_output == "Only answer"

    def test_extracts_last_n_turns(self):
        """Test that last N turns are used, not first N."""
        strategy = ContextWindowStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "A3"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        # Should have Second and Third, not First
        assert "First" not in result.user_input
        assert "Second" in result.user_input
        assert "Third" in result.user_input
        assert result.agent_output == "A3"

    def test_system_prompt_included(self):
        """Test that system_prompt is included in result."""
        system_prompt = "You are a helpful coding assistant."
        strategy = ContextWindowStrategy(n_turns=2, system_prompt=system_prompt)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.system_prompt == system_prompt

    def test_system_prompt_none_when_not_provided(self):
        """Test system_prompt is None when not provided."""
        strategy = ContextWindowStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = extractor.extract(task_id, history)

        assert result is not None
        assert result.system_prompt is None

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = ContextWindowStrategy(n_turns=3)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()

        result = extractor.extract(task_id, [])

        assert result is None

    def test_no_complete_turns_returns_none(self):
        """Test history without complete turns returns None."""
        strategy = ContextWindowStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [{"role": "user", "content": "Unanswered question"}]

        result = extractor.extract(task_id, history)

        assert result is None

    def test_typical_use_case_3_to_5_turns(self):
        """Test typical use case with 3-5 turns for context."""
        strategy = ContextWindowStrategy(n_turns=3, system_prompt="You are an AI assistant.")
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "How do I install it?"},
            {"role": "assistant", "content": "You can download it from python.org."},
            {"role": "user", "content": "What about pip?"},
            {"role": "assistant", "content": "Pip comes with Python 3.4+."},
        ]

        result = extractor.extract(task_id, history, feedback_score=0.95)

        assert result is not None
        # All 3 user questions in context
        assert "What is Python?" in result.user_input
        assert "How do I install it?" in result.user_input
        assert "What about pip?" in result.user_input
        # Only final response as output
        assert result.agent_output == "Pip comes with Python 3.4+."
        # System prompt preserved
        assert result.system_prompt == "You are an AI assistant."
        # Feedback preserved
        assert result.feedback_score == 0.95


class TestParseTurns:
    """Test the parse_turns helper function."""

    def test_simple_alternating_conversation(self):
        """Test parsing simple alternating user-assistant messages."""
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 2
        assert turns[0] == ("Q1", "A1")
        assert turns[1] == ("Q2", "A2")

    def test_handles_agent_role(self):
        """Test that 'agent' role is treated same as 'assistant'."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "agent", "content": "Hi there!"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Hello", "Hi there!")

    def test_skips_user_without_response(self):
        """Test that user messages without responses are skipped."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Response to second"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Second", "Response to second")

    def test_skips_orphan_assistant_messages(self):
        """Test that assistant messages without preceding user are handled."""
        messages = [
            {"role": "assistant", "content": "Orphan message"},
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        turns = parse_turns(messages)

        assert len(turns) == 1
        assert turns[0] == ("Question", "Answer")

    def test_empty_messages(self):
        """Test parsing empty message list."""
        turns = parse_turns([])

        assert turns == []


class TestCleanMessages:
    """Test message cleaning functionality."""

    def test_removes_empty_content(self):
        """Test that messages with empty content are removed."""
        history = [
            {"role": "user", "content": "Valid"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "   "},
            {"role": "assistant", "content": "Also valid"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 2
        assert cleaned[0]["content"] == "Valid"
        assert cleaned[1]["content"] == "Also valid"

    def test_removes_messages_without_role(self):
        """Test that messages without role are removed."""
        history = [
            {"content": "No role"},
            {"role": "user", "content": "Has role"},
        ]

        cleaned = clean_messages(history)

        assert len(cleaned) == 1
        assert cleaned[0]["content"] == "Has role"

    def test_strips_whitespace(self):
        """Test that content whitespace is stripped."""
        history = [{"role": "user", "content": "  trimmed  "}]

        cleaned = clean_messages(history)

        assert cleaned[0]["content"] == "trimmed"


class TestFeedbackPassthrough:
    """Test that feedback data is correctly passed through extraction."""

    def test_feedback_score_passed_through(self):
        """Test feedback_score is included in result."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        result = extractor.extract(task_id, history, feedback_score=0.9)

        assert result is not None
        assert result.feedback_score == 0.9

    def test_feedback_type_passed_through(self):
        """Test feedback_type is included in result."""
        strategy = LastTurnStrategy()
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        result = extractor.extract(task_id, history, feedback_type="rating")

        assert result is not None
        assert result.feedback_type == "rating"

    def test_feedback_in_last_n_turns(self):
        """Test feedback is passed through in LastNTurnsStrategy."""
        strategy = LastNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = extractor.extract(
            task_id, history, feedback_score=0.8, feedback_type="thumbs_up"
        )

        assert result is not None
        assert result.feedback_score == 0.8
        assert result.feedback_type == "thumbs_up"

    def test_feedback_in_first_n_turns(self):
        """Test feedback is passed through in FirstNTurnsStrategy."""
        strategy = FirstNTurnsStrategy(n_turns=2)
        extractor = InteractionExtractor(strategy)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = extractor.extract(
            task_id, history, feedback_score=1.0, feedback_type="rating"
        )

        assert result is not None
        assert result.feedback_score == 1.0
        assert result.feedback_type == "rating"


class TestSlidingWindowStrategy:
    """Test SlidingWindowStrategy extraction."""

    def test_single_window_with_2_turns(self):
        """Test extraction with exactly window_size turns."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        results = strategy.extract_all(task_id, history)

        assert len(results) == 1
        assert "Q1" in results[0].user_input
        assert "Q2" in results[0].user_input
        assert results[0].agent_output == "A2"

    def test_sliding_window_overlapping(self):
        """Test sliding window with stride=1 produces overlapping examples."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        results = strategy.extract_all(task_id, history)

        # 4 turns, window_size=2, stride=1 -> 3 windows
        assert len(results) == 3

        # Window 1: Q1, Q2 -> A2
        assert "Q1" in results[0].user_input
        assert "Q2" in results[0].user_input
        assert results[0].agent_output == "A2"

        # Window 2: Q2, Q3 -> A3
        assert "Q2" in results[1].user_input
        assert "Q3" in results[1].user_input
        assert results[1].agent_output == "A3"

        # Window 3: Q3, Q4 -> A4
        assert "Q3" in results[2].user_input
        assert "Q4" in results[2].user_input
        assert results[2].agent_output == "A4"

    def test_sliding_window_non_overlapping(self):
        """Test sliding window with stride=window_size produces non-overlapping examples."""
        strategy = SlidingWindowStrategy(window_size=2, stride=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        results = strategy.extract_all(task_id, history)

        # 4 turns, window_size=2, stride=2 -> 2 windows
        assert len(results) == 2

        # Window 1: Q1, Q2 -> A2
        assert "Q1" in results[0].user_input
        assert "Q2" in results[0].user_input
        assert results[0].agent_output == "A2"

        # Window 2: Q3, Q4 -> A4
        assert "Q3" in results[1].user_input
        assert "Q4" in results[1].user_input
        assert results[1].agent_output == "A4"

    def test_not_enough_turns_returns_empty(self):
        """Test that insufficient turns returns empty list."""
        strategy = SlidingWindowStrategy(window_size=3, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        results = strategy.extract_all(task_id, history)

        assert results == []

    def test_extract_returns_last_window(self):
        """Test that extract() returns only the last window."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Last window: Q2, Q3 -> A3
        assert "Q2" in result.user_input
        assert "Q3" in result.user_input
        assert result.agent_output == "A3"

    def test_window_size_3_with_stride_1(self):
        """Test larger window size."""
        strategy = SlidingWindowStrategy(window_size=3, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        results = strategy.extract_all(task_id, history)

        # 4 turns, window_size=3, stride=1 -> 2 windows
        assert len(results) == 2

        # Window 1: Q1, Q2, Q3 -> A3
        assert "Q1" in results[0].user_input
        assert "Q2" in results[0].user_input
        assert "Q3" in results[0].user_input
        assert results[0].agent_output == "A3"

        # Window 2: Q2, Q3, Q4 -> A4
        assert "Q2" in results[1].user_input
        assert "Q3" in results[1].user_input
        assert "Q4" in results[1].user_input
        assert results[1].agent_output == "A4"

    def test_feedback_passed_through_extract_all(self):
        """Test feedback is passed to all extracted interactions."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        results = strategy.extract_all(
            task_id, history, feedback_score=0.9, feedback_type="rating"
        )

        assert len(results) == 2
        for result in results:
            assert result.feedback_score == 0.9
            assert result.feedback_type == "rating"

    def test_minimum_window_size_enforced(self):
        """Test window_size minimum is 1."""
        strategy = SlidingWindowStrategy(window_size=0, stride=1)
        assert strategy.window_size == 1

    def test_minimum_stride_enforced(self):
        """Test stride minimum is 1."""
        strategy = SlidingWindowStrategy(window_size=2, stride=0)
        assert strategy.stride == 1

    def test_empty_history_returns_empty(self):
        """Test empty history returns empty list."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        task_id = uuid4()

        results = strategy.extract_all(task_id, [])

        assert results == []

    def test_factory_creates_sliding_window(self):
        """Test factory function creates SlidingWindowStrategy."""
        strategy = get_strategy("sliding_window", window_size=3, stride=2)

        assert isinstance(strategy, SlidingWindowStrategy)
        assert strategy.window_size == 3
        assert strategy.stride == 2
        assert strategy.name == "sliding_window"

    def test_start_offset_skips_initial_turns(self):
        """Test start_offset skips the first N turns."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1, start_offset=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
            {"role": "user", "content": "Q4"},
            {"role": "assistant", "content": "A4"},
        ]

        results = strategy.extract_all(task_id, history)

        # 4 turns, window_size=2, stride=1, start_offset=1 -> 2 windows
        # Starts from turn index 1 (Q2), not 0 (Q1)
        assert len(results) == 2

        # Window 1: Q2, Q3 -> A3 (starts at index 1)
        assert "Q1" not in results[0].user_input
        assert "Q2" in results[0].user_input
        assert "Q3" in results[0].user_input
        assert results[0].agent_output == "A3"

        # Window 2: Q3, Q4 -> A4
        assert "Q3" in results[1].user_input
        assert "Q4" in results[1].user_input
        assert results[1].agent_output == "A4"

    def test_start_offset_larger_than_turns_returns_empty(self):
        """Test start_offset larger than available turns returns empty."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1, start_offset=10)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        results = strategy.extract_all(task_id, history)

        assert results == []

    def test_start_offset_with_insufficient_remaining_turns(self):
        """Test start_offset that leaves fewer turns than window_size."""
        strategy = SlidingWindowStrategy(window_size=3, stride=1, start_offset=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        # 3 turns total, start_offset=2 leaves only 1 turn, need 3 for window
        results = strategy.extract_all(task_id, history)

        assert results == []

    def test_start_offset_minimum_enforced(self):
        """Test start_offset minimum is 0."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1, start_offset=-5)
        assert strategy.start_offset == 0

    def test_start_offset_zero_is_default(self):
        """Test start_offset defaults to 0."""
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        assert strategy.start_offset == 0

    def test_factory_creates_sliding_window_with_offset(self):
        """Test factory function creates SlidingWindowStrategy with start_offset."""
        strategy = get_strategy("sliding_window", window_size=3, stride=2, start_offset=1)

        assert isinstance(strategy, SlidingWindowStrategy)
        assert strategy.window_size == 3
        assert strategy.stride == 2
        assert strategy.start_offset == 1


class TestSummaryContextStrategy:
    """Test SummaryContextStrategy extraction."""

    def test_single_turn_no_summary(self):
        """Test single turn doesn't produce summary."""
        strategy = SummaryContextStrategy(summary_turns=3, recent_turns=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"
        # No summary markers for single turn
        assert "[Previous conversation summary]" not in result.user_input

    def test_two_turns_within_recent_turns(self):
        """Test 2 turns with recent_turns=2 doesn't produce summary."""
        strategy = SummaryContextStrategy(summary_turns=3, recent_turns=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Should be formatted as recent context without summary
        assert "[Previous conversation summary]" not in result.user_input
        assert "Q1" in result.user_input
        assert "Q2" in result.user_input
        assert result.agent_output == "A2"

    def test_creates_summary_for_long_conversation(self):
        """Test summary is created for conversations longer than recent_turns."""
        strategy = SummaryContextStrategy(summary_turns=2, recent_turns=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "How do I install pip?"},
            {"role": "assistant", "content": "Pip comes bundled with Python."},
            {"role": "user", "content": "What packages should I install?"},
            {"role": "assistant", "content": "It depends on your project needs."},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Should have summary section
        assert "[Previous conversation summary]" in result.user_input
        # Should have recent conversation section
        assert "[Recent conversation]" in result.user_input
        # Summary should mention earlier turns
        assert "Turn 1" in result.user_input or "Asked" in result.user_input
        # Final output
        assert result.agent_output == "It depends on your project needs."

    def test_bullet_format_summary(self):
        """Test bullet format summary creates bullet points."""
        strategy = SummaryContextStrategy(summary_turns=2, recent_turns=1, summary_format="bullets")
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question."},
            {"role": "assistant", "content": "First answer."},
            {"role": "user", "content": "Second question."},
            {"role": "assistant", "content": "Second answer."},
            {"role": "user", "content": "Third question."},
            {"role": "assistant", "content": "Third answer."},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Bullet format should have "- Turn" markers
        assert "- Turn" in result.user_input

    def test_paragraph_format_summary(self):
        """Test paragraph format summary creates flowing text."""
        strategy = SummaryContextStrategy(summary_turns=2, recent_turns=1, summary_format="paragraph")
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First question."},
            {"role": "assistant", "content": "First answer."},
            {"role": "user", "content": "Second question."},
            {"role": "assistant", "content": "Second answer."},
            {"role": "user", "content": "Third question."},
            {"role": "assistant", "content": "Third answer."},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Paragraph format should have "User asked about" markers
        assert "User asked about" in result.user_input
        # Should not have bullet points
        assert "- Turn" not in result.user_input

    def test_max_summary_length_truncates(self):
        """Test that summary is truncated to max_summary_length."""
        strategy = SummaryContextStrategy(
            summary_turns=3, recent_turns=1, max_summary_length=100
        )
        task_id = uuid4()
        # Create a conversation with long messages
        history = [
            {"role": "user", "content": "This is a very long question " * 10},
            {"role": "assistant", "content": "This is a very long answer " * 10},
            {"role": "user", "content": "Another long question " * 10},
            {"role": "assistant", "content": "Another long answer " * 10},
            {"role": "user", "content": "Final question"},
            {"role": "assistant", "content": "Final answer"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # The summary portion should be truncated (ends with ...)
        # Note: The full user_input includes more than just the summary
        summary_section = result.user_input.split("[Recent conversation]")[0]
        # Summary should be reasonably sized
        assert len(summary_section) < 500  # Some buffer for formatting

    def test_feedback_passed_through(self):
        """Test feedback is passed to extracted interaction."""
        strategy = SummaryContextStrategy(summary_turns=2, recent_turns=1)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Q3"},
            {"role": "assistant", "content": "A3"},
        ]

        result = strategy.extract(task_id, history, feedback_score=0.95, feedback_type="rating")

        assert result is not None
        assert result.feedback_score == 0.95
        assert result.feedback_type == "rating"

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = SummaryContextStrategy()
        task_id = uuid4()

        result = strategy.extract(task_id, [])

        assert result is None

    def test_no_complete_turns_returns_none(self):
        """Test history without complete turns returns None."""
        strategy = SummaryContextStrategy()
        task_id = uuid4()
        history = [{"role": "user", "content": "Unanswered question"}]

        result = strategy.extract(task_id, history)

        assert result is None

    def test_minimum_values_enforced(self):
        """Test minimum values for parameters are enforced."""
        strategy = SummaryContextStrategy(
            summary_turns=0,
            recent_turns=0,
            max_summary_length=0,
        )
        assert strategy.summary_turns == 1
        assert strategy.recent_turns == 1
        assert strategy.max_summary_length == 100

    def test_invalid_summary_format_defaults_to_bullets(self):
        """Test invalid summary_format defaults to bullets."""
        strategy = SummaryContextStrategy(summary_format="invalid")
        assert strategy.summary_format == "bullets"

    def test_factory_creates_summary_context(self):
        """Test factory function creates SummaryContextStrategy."""
        strategy = get_strategy("summary_context", summary_turns=4, recent_turns=2)

        assert isinstance(strategy, SummaryContextStrategy)
        assert strategy.summary_turns == 4
        assert strategy.recent_turns == 2
        assert strategy.name == "summary_context"

    def test_extract_key_point_first_sentence(self):
        """Test _extract_key_point extracts first sentence."""
        strategy = SummaryContextStrategy()

        result = strategy._extract_key_point("This is first. This is second.", prefix="Test")

        assert result == "Test: This is first."

    def test_extract_key_point_truncates_long_text(self):
        """Test _extract_key_point truncates long text without sentence end."""
        strategy = SummaryContextStrategy()
        long_text = "This is a very long text without any sentence ending markers " * 5

        result = strategy._extract_key_point(long_text)

        assert len(result) <= 83  # 80 + "..."
        assert result.endswith("...")

    def test_recent_turns_formatting(self):
        """Test recent turns are formatted with role labels."""
        strategy = SummaryContextStrategy(summary_turns=1, recent_turns=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Second response"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Third response"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Recent section should have User/Assistant labels
        assert "User: Second" in result.user_input
        assert "Assistant: Second response" in result.user_input
        assert "User: Third" in result.user_input


class TestSimilarityFunctions:
    """Test text similarity functions."""

    def test_jaccard_similarity_identical_texts(self):
        """Test Jaccard similarity of identical texts is 1.0."""
        result = jaccard_similarity("hello world", "hello world")
        assert result == 1.0

    def test_jaccard_similarity_no_overlap(self):
        """Test Jaccard similarity with no common words is 0.0."""
        result = jaccard_similarity("hello world", "foo bar")
        assert result == 0.0

    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity with partial overlap."""
        result = jaccard_similarity("hello world foo", "hello bar baz")
        # Words: {hello, world, foo} vs {hello, bar, baz}
        # Intersection: {hello} = 1
        # Union: {hello, world, foo, bar, baz} = 5
        # Jaccard = 1/5 = 0.2
        assert result == 0.2

    def test_jaccard_similarity_empty_text(self):
        """Test Jaccard similarity with empty text is 0.0."""
        assert jaccard_similarity("", "hello") == 0.0
        assert jaccard_similarity("hello", "") == 0.0
        assert jaccard_similarity("", "") == 0.0

    def test_overlap_similarity_identical_texts(self):
        """Test overlap similarity of identical texts is 1.0."""
        result = overlap_similarity("hello world", "hello world")
        assert result == 1.0

    def test_overlap_similarity_subset(self):
        """Test overlap similarity when one is subset of other."""
        # "hello" is subset of "hello world"
        result = overlap_similarity("hello", "hello world")
        assert result == 1.0  # intersection/min = 1/1 = 1.0

    def test_overlap_similarity_no_overlap(self):
        """Test overlap similarity with no common words is 0.0."""
        result = overlap_similarity("hello world", "foo bar")
        assert result == 0.0

    def test_overlap_similarity_empty_text(self):
        """Test overlap similarity with empty text is 0.0."""
        assert overlap_similarity("", "hello") == 0.0
        assert overlap_similarity("hello", "") == 0.0

    def test_weighted_similarity_identical_texts(self):
        """Test weighted similarity of identical texts is 1.0."""
        result = weighted_similarity("hello world", "hello world")
        assert abs(result - 1.0) < 1e-10  # Allow for floating point precision

    def test_weighted_similarity_no_overlap(self):
        """Test weighted similarity with no common words is 0.0."""
        result = weighted_similarity("hello world", "foo bar")
        assert result == 0.0

    def test_weighted_similarity_with_corpus(self):
        """Test weighted similarity uses corpus for IDF calculation."""
        corpus = [
            "hello world",
            "hello there",
            "hello everyone",
            "goodbye world",
        ]
        # "hello" appears in 3 docs, "world" appears in 2 docs
        # "world" should have higher weight than "hello"
        result = weighted_similarity("hello world", "goodbye world", corpus=corpus)
        assert result > 0  # Should have some similarity from "world"

    def test_weighted_similarity_empty_text(self):
        """Test weighted similarity with empty text is 0.0."""
        assert weighted_similarity("", "hello") == 0.0
        assert weighted_similarity("hello", "") == 0.0

    def test_compute_similarity_jaccard(self):
        """Test compute_similarity with jaccard method."""
        result = compute_similarity("hello world", "hello foo", method="jaccard")
        assert result == jaccard_similarity("hello world", "hello foo")

    def test_compute_similarity_overlap(self):
        """Test compute_similarity with overlap method."""
        result = compute_similarity("hello", "hello world", method="overlap")
        assert result == overlap_similarity("hello", "hello world")

    def test_compute_similarity_weighted(self):
        """Test compute_similarity with weighted method."""
        result = compute_similarity("hello world", "hello world", method="weighted")
        assert abs(result - 1.0) < 1e-10  # Allow for floating point precision

    def test_compute_similarity_invalid_method(self):
        """Test compute_similarity raises for invalid method."""
        with pytest.raises(ValueError, match="Unknown similarity method"):
            compute_similarity("hello", "world", method="invalid")


class TestKeyTurnsStrategy:
    """Test KeyTurnsStrategy extraction."""

    def test_single_turn_returns_that_turn(self):
        """Test single turn returns that turn."""
        strategy = KeyTurnsStrategy(n_turns=3)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        assert result.user_input == "Hello"
        assert result.agent_output == "Hi there!"

    def test_fewer_turns_than_n_uses_all(self):
        """Test when fewer turns than n_turns, all are used."""
        strategy = KeyTurnsStrategy(n_turns=5)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        assert "Q1" in result.user_input
        assert "Q2" in result.user_input
        assert result.agent_output == "A2"

    def test_selects_most_similar_turns(self):
        """Test strategy selects turns most similar to final turn."""
        strategy = KeyTurnsStrategy(n_turns=3, similarity_method="jaccard")
        task_id = uuid4()
        history = [
            {"role": "user", "content": "What is weather"},
            {"role": "assistant", "content": "Weather info"},
            {"role": "user", "content": "Python programming language"},
            {"role": "assistant", "content": "Python is great"},
            {"role": "user", "content": "Python web frameworks"},
            {"role": "assistant", "content": "Django and Flask"},
            {"role": "user", "content": "Random unrelated topic"},
            {"role": "assistant", "content": "Some response"},
            {"role": "user", "content": "Python data science"},
            {"role": "assistant", "content": "NumPy and Pandas"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Final turn is about Python data science
        # Should select Python-related turns (higher similarity)
        # and exclude weather/random topics
        assert result.agent_output == "NumPy and Pandas"
        # The final query should be in output
        assert "Python data science" in result.user_input

    def test_preserves_chronological_order(self):
        """Test selected turns are in chronological order."""
        strategy = KeyTurnsStrategy(n_turns=3, similarity_method="jaccard")
        task_id = uuid4()
        history = [
            {"role": "user", "content": "A topic about cats"},
            {"role": "assistant", "content": "Cats are pets"},
            {"role": "user", "content": "Dogs are also pets"},
            {"role": "assistant", "content": "Yes they are"},
            {"role": "user", "content": "Weather today"},
            {"role": "assistant", "content": "It is sunny"},
            {"role": "user", "content": "Cats and dogs playing"},
            {"role": "assistant", "content": "Cute animals"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Even if turn 2 (dogs) is more similar than turn 1 (cats),
        # they should appear in order if both selected

    def test_include_final_always_includes_last_turn(self):
        """Test include_final=True always includes last turn."""
        strategy = KeyTurnsStrategy(n_turns=2, include_final=True)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Very similar query A"},
            {"role": "assistant", "content": "Answer A"},
            {"role": "user", "content": "Very similar query A again"},
            {"role": "assistant", "content": "Answer again"},
            {"role": "user", "content": "Completely different topic"},
            {"role": "assistant", "content": "Different answer"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Final turn should always be included
        assert "Completely different topic" in result.user_input
        assert result.agent_output == "Different answer"

    def test_jaccard_method(self):
        """Test KeyTurnsStrategy with jaccard similarity."""
        strategy = KeyTurnsStrategy(n_turns=2, similarity_method="jaccard")
        assert strategy.similarity_method == "jaccard"
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Python programming"},
            {"role": "assistant", "content": "Great language"},
            {"role": "user", "content": "Python code"},
            {"role": "assistant", "content": "Here is code"},
        ]

        result = strategy.extract(task_id, history)
        assert result is not None

    def test_weighted_method(self):
        """Test KeyTurnsStrategy with weighted similarity."""
        strategy = KeyTurnsStrategy(n_turns=2, similarity_method="weighted")
        assert strategy.similarity_method == "weighted"
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Python programming"},
            {"role": "assistant", "content": "Great language"},
            {"role": "user", "content": "Python code"},
            {"role": "assistant", "content": "Here is code"},
        ]

        result = strategy.extract(task_id, history)
        assert result is not None

    def test_overlap_method(self):
        """Test KeyTurnsStrategy with overlap similarity."""
        strategy = KeyTurnsStrategy(n_turns=2, similarity_method="overlap")
        assert strategy.similarity_method == "overlap"
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Python programming"},
            {"role": "assistant", "content": "Great language"},
            {"role": "user", "content": "Python code"},
            {"role": "assistant", "content": "Here is code"},
        ]

        result = strategy.extract(task_id, history)
        assert result is not None

    def test_use_both_messages_true(self):
        """Test similarity calculation includes both user and assistant messages."""
        strategy = KeyTurnsStrategy(n_turns=2, use_both_messages=True)
        assert strategy.use_both_messages is True

    def test_use_both_messages_false(self):
        """Test similarity calculation uses only user messages."""
        strategy = KeyTurnsStrategy(n_turns=2, use_both_messages=False)
        assert strategy.use_both_messages is False

    def test_feedback_passed_through(self):
        """Test feedback is passed to extracted interaction."""
        strategy = KeyTurnsStrategy(n_turns=2)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        result = strategy.extract(task_id, history, feedback_score=0.9, feedback_type="rating")

        assert result is not None
        assert result.feedback_score == 0.9
        assert result.feedback_type == "rating"

    def test_empty_history_returns_none(self):
        """Test empty history returns None."""
        strategy = KeyTurnsStrategy()
        task_id = uuid4()

        result = strategy.extract(task_id, [])

        assert result is None

    def test_no_complete_turns_returns_none(self):
        """Test history without complete turns returns None."""
        strategy = KeyTurnsStrategy()
        task_id = uuid4()
        history = [{"role": "user", "content": "Unanswered question"}]

        result = strategy.extract(task_id, history)

        assert result is None

    def test_minimum_n_turns_enforced(self):
        """Test n_turns minimum is 1."""
        strategy = KeyTurnsStrategy(n_turns=0)
        assert strategy.n_turns == 1

        strategy = KeyTurnsStrategy(n_turns=-5)
        assert strategy.n_turns == 1

    def test_factory_creates_key_turns(self):
        """Test factory function creates KeyTurnsStrategy."""
        strategy = get_strategy("key_turns", n_turns=4, similarity_method="weighted")

        assert isinstance(strategy, KeyTurnsStrategy)
        assert strategy.n_turns == 4
        assert strategy.similarity_method == "weighted"
        assert strategy.name == "key_turns"

    def test_formatting_with_key_context_labels(self):
        """Test output formatting includes key context labels."""
        strategy = KeyTurnsStrategy(n_turns=3)
        task_id = uuid4()
        history = [
            {"role": "user", "content": "Python question"},
            {"role": "assistant", "content": "Python answer"},
            {"role": "user", "content": "More Python"},
            {"role": "assistant", "content": "More answer"},
            {"role": "user", "content": "Final Python question"},
            {"role": "assistant", "content": "Final answer"},
        ]

        result = strategy.extract(task_id, history)

        assert result is not None
        # Should have context labels
        assert "[Key context" in result.user_input
        assert "[Current query]" in result.user_input
