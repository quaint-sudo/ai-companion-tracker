"""Unit tests for the benefit/harm classifier."""

import pytest
from ingestion.classifier import classify, classify_batch


class TestClassifySingle:
    def test_benefit_detected(self):
        result = classify("This app really helped with my anxiety and loneliness")
        assert result["has_benefit"] is True
        assert "anxiety" in result["benefit_matches"]
        assert "loneliness" in result["benefit_matches"]

    def test_harm_detected(self):
        result = classify("I feel addicted and obsessed with this AI, it's manipulative")
        assert result["has_harm"] is True
        assert "addicted" in result["harm_matches"]
        assert "obsessed" in result["harm_matches"]
        assert "manipulative" in result["harm_matches"]

    def test_both_detected(self):
        result = classify("It was helpful at first but now I feel dependent on it")
        assert result["has_benefit"] is True
        assert result["has_harm"] is True

    def test_neutral_text(self):
        result = classify("The app has a nice interface and loads quickly")
        assert result["has_benefit"] is False
        assert result["has_harm"] is False

    def test_empty_text(self):
        result = classify("")
        assert result["has_benefit"] is False
        assert result["has_harm"] is False

    def test_none_text(self):
        result = classify(None)
        assert result["has_benefit"] is False
        assert result["has_harm"] is False

    def test_case_insensitive(self):
        result = classify("VERY HELPFUL and COMFORTING during GRIEF")
        assert result["has_benefit"] is True
        assert "helpful" in result["benefit_matches"]
        assert "grief" in result["benefit_matches"]

    def test_punctuation_handling(self):
        result = classify("I'm addicted! It's so manipulative...")
        assert result["has_harm"] is True
        assert "addicted" in result["harm_matches"]


class TestClassifyBatch:
    def test_batch_counts(self):
        texts = [
            "This is helpful for my anxiety",
            "I feel addicted to this app",
            "Great interface, love the colors",
            "Very comforting and supportive",
        ]
        stats = classify_batch(texts)
        assert stats["total"] == 4
        assert stats["benefit_count"] == 2   # "helpful anxiety" + "comforting supportive"
        assert stats["harm_count"] == 1      # "addicted"

    def test_batch_rates(self):
        texts = [
            "helpful",
            "addicted",
            "neutral text here",
            "also neutral",
        ]
        stats = classify_batch(texts)
        assert stats["benefit_rate"] == 0.25
        assert stats["harm_rate"] == 0.25
        assert stats["net_sentiment"] == 0.0

    def test_empty_batch(self):
        stats = classify_batch([])
        assert stats["total"] == 0
        assert stats["benefit_rate"] == 0.0
        assert stats["harm_rate"] == 0.0
        assert stats["net_sentiment"] == 0.0

    def test_all_benefit(self):
        texts = ["helpful", "supportive", "comforting"]
        stats = classify_batch(texts)
        assert stats["benefit_rate"] == 1.0
        assert stats["harm_rate"] == 0.0
        assert stats["net_sentiment"] == 1.0

    def test_all_harm(self):
        texts = ["addicted", "manipulative", "unsafe"]
        stats = classify_batch(texts)
        assert stats["benefit_rate"] == 0.0
        assert stats["harm_rate"] == 1.0
        assert stats["net_sentiment"] == -1.0
