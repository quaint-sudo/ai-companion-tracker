"""
Keyword-based classifier for benefit/harm language detection.

Uses seeded dictionary matching from config.py. Returns both aggregate
statistics and per-text match details so results can be spot-checked.

This is not a black-box model — every classification decision is traceable
to specific matched terms, making it suitable for academic review.
"""

import re
from scripts.config import BENEFIT_TERMS, HARM_TERMS


def classify(text: str) -> dict:
    """
    Classify a single text for benefit and harm language.

    Returns:
        dict with:
            - has_benefit (bool)
            - has_harm (bool)
            - benefit_matches (list[str]): Which terms matched
            - harm_matches (list[str]): Which terms matched
    """
    if not text:
        return {
            "has_benefit": False,
            "has_harm": False,
            "benefit_matches": [],
            "harm_matches": [],
        }

    normalized = text.lower()
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

    Returns:
        dict with:
            - total, benefit_count, harm_count
            - benefit_rate, harm_rate, net_sentiment
            - examples: list of notable matches (for spot-checking)
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
            "examples": [],
        }

    results = [classify(t) for t in texts]
    benefit_count = sum(1 for r in results if r["has_benefit"])
    harm_count = sum(1 for r in results if r["has_harm"])

    benefit_rate = round(benefit_count / total, 4)
    harm_rate = round(harm_count / total, 4)
    net_sentiment = round(benefit_rate - harm_rate, 4)

    # Collect notable examples for human review (up to 5 each)
    examples = []
    benefit_examples = 0
    harm_examples = 0
    for text, result in zip(texts, results):
        snippet = text[:120].replace("\n", " ").strip()
        if result["has_harm"] and harm_examples < 5:
            examples.append({
                "type": "harm",
                "snippet": snippet,
                "matches": result["harm_matches"],
            })
            harm_examples += 1
        elif result["has_benefit"] and benefit_examples < 5:
            examples.append({
                "type": "benefit",
                "snippet": snippet,
                "matches": result["benefit_matches"],
            })
            benefit_examples += 1
        if benefit_examples >= 5 and harm_examples >= 5:
            break

    return {
        "total": total,
        "benefit_count": benefit_count,
        "harm_count": harm_count,
        "benefit_rate": benefit_rate,
        "harm_rate": harm_rate,
        "net_sentiment": net_sentiment,
        "examples": examples,
    }
