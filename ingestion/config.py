"""
Configuration for the AI Companion Narrative Shift Tracker.
All app IDs, subreddit targets, and classification dictionaries live here.
"""

# =============================================================================
# App Store Configuration
# =============================================================================
# Apple App Store numeric IDs for each target app
APP_STORE_IDS = {
    "character_ai": "1795227870",
    "replika": "1158555867",
    "pi": "6444743428",
    "woebot": "1305375832",
}

# App Store RSS feed template (JSON format, most recent reviews, US store)
APP_STORE_RSS_TEMPLATE = (
    "https://itunes.apple.com/us/rss/customerreviews/id={app_id}"
    "/sortBy=mostRecent/page={page}/json"
)

# Number of RSS pages to fetch per app (each page = ~50 reviews)
APP_STORE_MAX_PAGES = 5

# =============================================================================
# Trustpilot Configuration
# =============================================================================
# Trustpilot business page slugs for each target app
TRUSTPILOT_SLUGS = {
    "character_ai": "character.ai",
    "replika": "replika.ai",
    "pi": "pi.ai",
    "woebot": "woebothealth.com",
}

TRUSTPILOT_BASE_URL = "https://www.trustpilot.com/review/{slug}"
TRUSTPILOT_MAX_PAGES = 3  # Pages of reviews to fetch per app

# =============================================================================
# Reddit Configuration (Public JSON — NO API key needed)
# =============================================================================
TARGET_SUBREDDITS = ["replika", "CharacterAI", "artificial"]

# Public JSON endpoint (no auth required)
REDDIT_JSON_TEMPLATE = "https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
REDDIT_USER_AGENT = "AI-Companion-Tracker/1.0 (Academic Research)"

# Maximum posts to fetch per subreddit per run
REDDIT_POST_LIMIT = 100

# =============================================================================
# Classification Dictionaries
# =============================================================================
BENEFIT_TERMS = frozenset([
    "support", "helpful", "anxiety", "loneliness", "comfort", "grief",
    "supportive", "helped", "helps", "comforting", "comforted",
    "therapeutic", "therapy", "coping", "safe space", "mental health",
    "emotional support", "calming", "reassuring", "well-being",
])

HARM_TERMS = frozenset([
    "addicted", "manipulative", "dependent", "obsessed", "unsafe", "self-harm",
    "addiction", "manipulated", "dependency", "obsession", "dangerous",
    "toxic", "predatory", "exploitation", "grooming", "suicidal",
    "self harm", "selfharm", "harmful",
])

# =============================================================================
# Data File Paths (relative to repo root)
# =============================================================================
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "docs", "data")
APPSTORE_CSV = os.path.join(DATA_DIR, "appstore_weekly.csv")
TRUSTPILOT_CSV = os.path.join(DATA_DIR, "trustpilot_weekly.csv")
REDDIT_CSV = os.path.join(DATA_DIR, "reddit_weekly.csv")

# CSV column definitions (auto-created on first run)
APPSTORE_COLUMNS = [
    "week", "app", "review_count",
    "benefit_count", "harm_count",
    "benefit_rate", "harm_rate",
    "net_sentiment",
]

TRUSTPILOT_COLUMNS = [
    "week", "app", "review_count",
    "benefit_count", "harm_count",
    "benefit_rate", "harm_rate",
    "net_sentiment",
]

REDDIT_COLUMNS = [
    "week", "subreddit", "post_count", "comment_count",
    "benefit_count", "harm_count",
    "benefit_rate", "harm_rate",
    "net_sentiment", "sentiment_velocity",
]
