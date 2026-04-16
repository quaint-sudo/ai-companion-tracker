"""
Keyword-based classifier for benefit/harm language detection.
Uses dictionary matching from config.py — no ML dependencies needed.
"""

import re
from ingestion.config import BENEFIT_TERMS, HARM_TERMS


def classify(text: str) -> dict:
    """
    Classify a text string for benefit and harm language.

    Args:
        text: Raw review or post/comment text.

    Returns:
        dict with keys:
            - has_benefit (bool): True if any benefit term found
            - has_harm (bool): True if any harm term found
            - benefit_matches (list[str]): Matched benefit terms
            - harm_matches (list[str]): Matched harm terms
    """
    if not text:
        return {
            "has_benefit": False,
            "has_harm": False,
            "benefit_matches": [],
            "harm_matches": [],
        }

    normalized = text.lower()
    # Remove punctuation for better matching, keep spaces
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    benefit_matches = [term for term in BENEFIT_TERMS if term in normalized]
    harm_matches = [term for term in HARM_TERMS if term in normalized]

    return {
        "has_benefit": len(benefit_matches) > 0,
        "has_harm": len(harm_matches) > 0,
        "benefit_matches": benefit_matches,
        "harm_matches": harm_matches,
    }


def classify_batch(texts: list[str]) -> dict:
    """
    Classify a batch of texts and return aggregate counts.

    Args:
        texts: List of text strings to classify.

    Returns:
        dict with keys:
            - total (int): Total texts processed
            - benefit_count (int): Texts with ≥1 benefit term
            - harm_count (int): Texts with ≥1 harm term
            - benefit_rate (float): benefit_count / total
            - harm_rate (float): harm_count / total
            - net_sentiment (float): benefit_rate - harm_rate
    """
    total = len(texts)
    if total == 0:
        return {
            "total": 0,
            "benefit_count": 0,
            "harm_count": 0,
            "benefit_rate": 0.0,
            "harm_rate": 0.0,
            "net_sentiment": 0.0,
        }

    results = [classify(t) for t in texts]
    benefit_count = sum(1 for r in results if r["has_benefit"])
    harm_count = sum(1 for r in results if r["has_harm"])

    benefit_rate = round(benefit_count / total, 4)
    harm_rate = round(harm_count / total, 4)
    net_sentiment = round(benefit_rate - harm_rate, 4)

    return {
        "total": total,
        "benefit_count": benefit_count,
        "harm_count": harm_count,
        "benefit_rate": benefit_rate,
        "harm_rate": harm_rate,
        "net_sentiment": net_sentiment,
    }
