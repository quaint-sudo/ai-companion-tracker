"""
Configuration for the AI Companion Narrative Shift Tracker.
Scoped to Character.AI and Replika only.

Session 16 — Relationships, Human Development, and Culture
AI Triad Option B Final
"""

import os

# =============================================================================
# Target Apps (2 only — intentionally narrow scope)
# =============================================================================
# Character.AI: Chosen for its prominent role in public safety incidents
#   involving minors and its rapid growth as a conversational AI platform.
# Replika: Chosen as a longstanding "AI companion" app with documented
#   attachment/dependency patterns and prior policy controversies.

APP_STORE_IDS = {
    "character_ai": "1671705818",
    "replika": "1158555867",
}

APP_STORE_RSS_TEMPLATE = (
    "https://itunes.apple.com/us/rss/customerreviews/id={app_id}"
    "/sortBy=mostRecent/page={page}/json"
)

APP_STORE_MAX_PAGES = 10  # maximum allowed by Apple API (500 reviews)

# =============================================================================
# Reddit Configuration (RSS — NO API key, no approval needed)
# =============================================================================
# Limitation: Reddit RSS returns only ~25 most recent posts per feed.
# This is a known sampling constraint, documented in the README.
# Reddit is treated as a supporting narrative signal, not exhaustive data.

TARGET_SUBREDDITS = {
    "character_ai": "CharacterAI",
    "replika": "replika",
}

REDDIT_RSS_TEMPLATE = "https://www.reddit.com/r/{subreddit}/new/.rss"

# =============================================================================
# Classification Dictionaries
# =============================================================================
# Seeded term lists informed by:
#   - Common App Store review language for companion AI apps
#   - Public reporting on AI companion harms (NYT, WaPo, The Verge)
#   - Academic literature on parasocial relationships and technology dependence
#
# These are not exhaustive. They are designed to be transparent, auditable,
# and extendable. Each match is logged for human spot-checking.

BENEFIT_TERMS = frozenset([
    # Emotional support
    "support", "helpful", "comforting", "reassuring", "calming",
    "supportive", "helped", "helps", "comforted",
    # Mental health
    "anxiety", "loneliness", "grief", "therapy", "therapeutic",
    "coping", "mental health", "well-being", "wellbeing",
    "safe space", "emotional support",
    # Positive relationship language
    "companion", "friend", "caring", "understanding", "empathy",
    "listened", "listening",
])

HARM_TERMS = frozenset([
    # Addiction / dependency
    "addicted", "addiction", "dependent", "dependency", "obsessed", "obsession",
    "can't stop", "cant stop", "hooked",
    # Manipulation / safety
    "manipulative", "manipulated", "grooming", "predatory", "exploitation",
    "unsafe", "dangerous", "toxic",
    # Self-harm / crisis
    "self-harm", "self harm", "selfharm", "suicidal", "suicide",
    "harmful", "hurt myself",
    # Concern language
    "worried", "concerning", "inappropriate", "creepy",
])

# =============================================================================
# Data File Paths
# =============================================================================
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "docs", "data")

APPSTORE_CSV = os.path.join(DATA_DIR, "appstore_weekly.csv")
REDDIT_CSV = os.path.join(DATA_DIR, "reddit_weekly.csv")
TIMELINE_JSON = os.path.join(DATA_DIR, "timeline.json")

# CSV schemas
APPSTORE_COLUMNS = [
    "week", "app", "review_count",
    "benefit_count", "harm_count",
    "benefit_rate", "harm_rate",
    "net_sentiment",
]

REDDIT_COLUMNS = [
    "week", "app", "subreddit", "post_count",
    "benefit_count", "harm_count",
    "benefit_rate", "harm_rate",
    "net_sentiment",
]
