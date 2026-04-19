"""
Unit tests for the benefit/harm classifier.
Scoped to Character.AI and Replika use cases.
"""

import pytest
from scripts.classifier import classify, classify_batch


class TestClassifySingle:
    """Test individual text classification."""

    def test_clear_benefit(self):
        result = classify("This app has been so helpful for my anxiety and loneliness")
        assert result["has_benefit"] is True
        assert "helpful" in result["benefit_matches"]
        assert "anxiety" in result["benefit_matches"]

    def test_clear_harm(self):
        result = classify("I'm addicted to this app, it feels manipulative")
        assert result["has_harm"] is True
        assert "addicted" in result["harm_matches"]
        assert "manipulative" in result["harm_matches"]

    def test_mixed_signals(self):
        result = classify("It's therapeutic but I'm worried I'm becoming dependent")
        assert result["has_benefit"] is True
        assert result["has_harm"] is True
        assert "therapeutic" in result["benefit_matches"]
        assert "dependent" in result["harm_matches"]

    def test_neutral_text(self):
        result = classify("The interface is clean and loads quickly")
        assert result["has_benefit"] is False
        assert result["has_harm"] is False

    def test_empty_text(self):
        result = classify("")
        assert result["has_benefit"] is False
        assert result["has_harm"] is False

    def test_case_insensitive(self):
        result = classify("VERY SUPPORTIVE and COMFORTING app")
        assert result["has_benefit"] is True
        assert "supportive" in result["benefit_matches"]

    def test_self_harm_detection(self):
        """Ensure multi-word harm terms like 'self-harm' are detected."""
        result = classify("the bot encouraged self-harm behavior")
        assert result["has_harm"] is True

    def test_concern_language(self):
        """Test newer concern terms like 'creepy' and 'inappropriate'."""
        result = classify("The responses were creepy and inappropriate for a child")
        assert result["has_harm"] is True
        assert "creepy" in result["harm_matches"]
        assert "inappropriate" in result["harm_matches"]


class TestClassifyBatch:
    """Test batch classification with aggregate stats."""

    def test_batch_aggregation(self):
        texts = [
            "Very helpful and supportive",        # benefit
            "I feel addicted and obsessed",        # harm
            "Great interface, fast loading",        # neutral
            "Therapeutic for my grief",             # benefit
        ]
        stats = classify_batch(texts)
        assert stats["total"] == 4
        assert stats["benefit_count"] == 2
        assert stats["harm_count"] == 1
        assert stats["benefit_rate"] == 0.5
        assert stats["harm_rate"] == 0.25
        assert stats["net_sentiment"] == 0.25

    def test_empty_batch(self):
        stats = classify_batch([])
        assert stats["total"] == 0
        assert stats["net_sentiment"] == 0.0

    def test_examples_included(self):
        """Verify that example matches are returned for spot-checking."""
        texts = [
            "Very addicted to this dangerous app",
            "So helpful for coping with anxiety",
        ]
        stats = classify_batch(texts)
        assert len(stats["examples"]) > 0
        assert stats["examples"][0]["type"] in ("benefit", "harm")
        assert len(stats["examples"][0]["matches"]) > 0

    def test_all_benefit(self):
        texts = ["helpful", "supportive", "comforting"]
        stats = classify_batch(texts)
        assert stats["benefit_rate"] == 1.0
        assert stats["harm_rate"] == 0.0
        assert stats["net_sentiment"] == 1.0

    def test_all_harm(self):
        texts = ["addicted", "toxic", "dangerous"]
        stats = classify_batch(texts)
        assert stats["harm_rate"] == 1.0
        assert stats["benefit_rate"] == 0.0
        assert stats["net_sentiment"] == -1.0
