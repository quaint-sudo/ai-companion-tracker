"""
Reddit RSS scraper (NO API key, no approval needed).
Fetches recent posts from r/CharacterAI and r/replika via Reddit's public
RSS feeds, classifies them, and appends to reddit_weekly.csv.

KNOWN LIMITATION: Reddit RSS returns only ~25 most recent posts per feed.
This is a sampling constraint, not an exhaustive dataset. Reddit data is
treated as a supporting narrative signal alongside App Store reviews.

This limitation is documented in the README and dashboard.
"""

import os
import time
import feedparser
import pandas as pd
from datetime import datetime, timezone

from scripts.config import (
    TARGET_SUBREDDITS,
    REDDIT_RSS_TEMPLATE,
    REDDIT_CSV,
    REDDIT_COLUMNS,
    DATA_DIR,
)
from scripts.classifier import classify_batch


def get_current_week() -> str:
    """Return current ISO week as 'YYYY-WNN' string."""
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def fetch_subreddit_posts(subreddit_name: str) -> list[str]:
    """
    Fetch recent posts from a subreddit via RSS.

    Reddit RSS feeds return ~25 most recent posts. Each entry includes
    the post title and a summary/content snippet.

    Returns:
        List of post text strings (title + content combined).
    """
    import re
    import requests

    url = REDDIT_RSS_TEMPLATE.format(subreddit=subreddit_name)
    headers = {
        "User-Agent": "AI-Companion-Tracker/1.0 (Academic Research Project)",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except requests.RequestException as e:
        print(f"  [WARN] HTTP error fetching r/{subreddit_name} RSS: {e}")
        return []
    except Exception as e:
        print(f"  [WARN] RSS parse error for r/{subreddit_name}: {e}")
        return []

    if not feed.entries:
        if feed.bozo:
            print(f"  [WARN] RSS feed issue for r/{subreddit_name}: {feed.bozo_exception}")
        return []

    texts = []
    for entry in feed.entries:
        title = entry.get("title", "")
        # RSS content is HTML — extract plain text roughly
        content = entry.get("summary", "")
        content_text = re.sub(r"<[^>]+>", " ", content)
        content_text = re.sub(r"\s+", " ", content_text).strip()

        combined = f"{title} {content_text}".strip()
        if combined:
            texts.append(combined)

    return texts


def ensure_csv_exists():
    """Create the CSV file with headers if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(REDDIT_CSV):
        df = pd.DataFrame(columns=REDDIT_COLUMNS)
        df.to_csv(REDDIT_CSV, index=False)
        print(f"[INIT] Created {REDDIT_CSV}")


def week_app_exists(week: str, app: str) -> bool:
    """Check if data for this week+app already exists (idempotency)."""
    if not os.path.exists(REDDIT_CSV):
        return False
    df = pd.read_csv(REDDIT_CSV)
    return ((df["week"] == week) & (df["app"] == app)).any()


def run():
    """Fetch, classify, and append Reddit RSS data."""
    ensure_csv_exists()
    week = get_current_week()
    print(f"\n{'='*60}")
    print(f"  Reddit RSS — Week {week}")
    print(f"  (Note: RSS returns ~25 posts per subreddit)")
    print(f"{'='*60}")

    new_rows = []

    for app_name, sub_name in TARGET_SUBREDDITS.items():
        display_name = app_name.replace("_", " ").title()
        print(f"\n  [r/{sub_name}] Fetching RSS for {display_name}...")

        if week_app_exists(week, app_name):
            print(f"  [SKIP] Data for {display_name} week {week} already exists.")
            continue

        posts = fetch_subreddit_posts(sub_name)
        print(f"  Collected {len(posts)} posts from RSS feed.")

        if len(posts) == 0:
            print(f"  [WARN] No posts found, recording zero row.")
            new_rows.append({
                "week": week, "app": app_name, "subreddit": f"r/{sub_name}",
                "post_count": 0, "benefit_count": 0, "harm_count": 0,
                "benefit_rate": 0.0, "harm_rate": 0.0, "net_sentiment": 0.0,
            })
            continue

        stats = classify_batch(posts)
        row = {
            "week": week, "app": app_name, "subreddit": f"r/{sub_name}",
            "post_count": stats["total"],
            "benefit_count": stats["benefit_count"],
            "harm_count": stats["harm_count"],
            "benefit_rate": stats["benefit_rate"],
            "harm_rate": stats["harm_rate"],
            "net_sentiment": stats["net_sentiment"],
        }
        new_rows.append(row)

        print(f"  Results: benefit={stats['benefit_rate']:.1%}, "
              f"harm={stats['harm_rate']:.1%}, net={stats['net_sentiment']:+.4f}")
        if stats["examples"]:
            print(f"  Sample matches:")
            for ex in stats["examples"][:3]:
                print(f"    [{ex['type'].upper()}] \"{ex['snippet'][:80]}...\"")
                print(f"           matched: {', '.join(ex['matches'])}")

        # Be polite to Reddit's servers
        time.sleep(2)

    if new_rows:
        df_existing = pd.read_csv(REDDIT_CSV)
        df_new = pd.DataFrame(new_rows, columns=REDDIT_COLUMNS)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(REDDIT_CSV, index=False)
        print(f"\n  ✓ Appended {len(new_rows)} rows to reddit_weekly.csv")
    else:
        print("\n  — No new Reddit data to append.")


if __name__ == "__main__":
    run()
